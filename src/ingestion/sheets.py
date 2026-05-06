"""
Google Sheets ingester — reads the four YourCompany sheets:
  1. Tenant / client list
  2. Building inventory
  3. Vendor list
  4. Broker list

Uses a Google Service Account for read-only access.
Each sheet is identified by its spreadsheet ID (from settings).

Column conventions (adapt to match the actual sheet headers):
  Tenant list   : Company Name, Contact Name, Email, Phone, Building, Seats, Status
  Building list : Building Name, Address, City, Total Seats, Available Seats, Type
  Vendor list   : Vendor Name, Service Type, Contact Name, Email, Phone, Building
  Broker list   : Broker Name, Firm, Email, Phone, Specialisation
"""

from __future__ import annotations

import logging
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.ingestion.base import BaseIngester, IngestionResult
from src.models.enums import DataSource, EntityType

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ── Column header mappings ────────────────────────────────────────────────────
# Map from normalised key → possible column headers in the actual sheets
# (case-insensitive; first match wins)
TENANT_FIELD_MAP = {
    "company_name": ["company name", "client name", "tenant name", "organisation"],
    "contact_name": ["contact name", "primary contact", "name"],
    "email": ["email", "email address"],
    "phone": ["phone", "mobile", "contact number"],
    "building": ["building", "building name", "location"],
    "seats": ["seats", "no. of seats", "seat count", "allocated seats"],
    "status": ["status", "client status"],
    "industry": ["industry", "sector"],
    "company_size": ["company size", "headcount", "employees"],
    "deal_value": ["deal value", "monthly rent", "monthly value"],
}

BUILDING_FIELD_MAP = {
    "building_name": ["building name", "name", "property name"],
    "address": ["address", "full address"],
    "city": ["city", "location"],
    "total_seats": ["total seats", "capacity", "total capacity"],
    "available_seats": ["available seats", "vacant seats"],
    "type": ["type", "property type", "building type"],
    "pin_code": ["pin code", "pincode", "zip"],
}

VENDOR_FIELD_MAP = {
    "vendor_name": ["vendor name", "company name", "name"],
    "service_type": ["service type", "service", "category"],
    "contact_name": ["contact name", "contact person"],
    "email": ["email", "email address"],
    "phone": ["phone", "contact number"],
    "building": ["building", "building name", "location served"],
}

BROKER_FIELD_MAP = {
    "broker_name": ["broker name", "name", "full name"],
    "firm": ["firm", "company", "brokerage firm"],
    "email": ["email", "email address"],
    "phone": ["phone", "mobile"],
    "specialisation": ["specialisation", "specialization", "focus area", "area"],
}


def _normalise_row(headers: list[str], row: list[str], field_map: dict[str, list[str]]) -> dict[str, str]:
    """Map raw sheet row to normalised dict using field_map."""
    raw = {h.strip().lower(): (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
    out: dict[str, str] = {}
    for canonical_key, possible_headers in field_map.items():
        for h in possible_headers:
            if h.lower() in raw and raw[h.lower()].strip():
                out[canonical_key] = raw[h.lower()].strip()
                break
    return out


class SheetsIngester(BaseIngester):
    source_name = DataSource.GOOGLE_SHEETS

    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        super().__init__(settings, db)
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service
        creds = service_account.Credentials.from_service_account_file(
            self.settings.google_service_account_json,
            scopes=SCOPES,
        )
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._service

    def _read_sheet(self, spreadsheet_id: str, range_name: str = "A:Z") -> list[list[str]]:
        service = self._get_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])

    # ── BaseIngester interface ────────────────────────────────────────────────

    async def _fetch_raw(self) -> list[dict[str, Any]]:
        """
        Returns a list of tagged raw dicts, one per sheet row.
        Each dict has a '__sheet_type__' key so _process_record knows what it is.
        """
        records: list[dict[str, Any]] = []

        sheet_configs = [
            (self.settings.sheets_tenant_list_id, "tenant", TENANT_FIELD_MAP),
            (self.settings.sheets_building_inventory_id, "building", BUILDING_FIELD_MAP),
            (self.settings.sheets_vendor_list_id, "vendor", VENDOR_FIELD_MAP),
            (self.settings.sheets_broker_list_id, "broker", BROKER_FIELD_MAP),
        ]

        for sheet_id, sheet_type, field_map in sheet_configs:
            if not sheet_id:
                self.logger.warning("No sheet ID configured for %s — skipping", sheet_type)
                continue
            try:
                rows = self._read_sheet(sheet_id)
                if not rows:
                    continue
                headers = [h.strip() for h in rows[0]]
                for i, row in enumerate(rows[1:], start=2):
                    normalised = _normalise_row(headers, row, field_map)
                    if not normalised:
                        continue
                    normalised["__sheet_type__"] = sheet_type
                    normalised["__row_number__"] = str(i)
                    normalised["__sheet_id__"] = sheet_id
                    records.append(normalised)
            except Exception as exc:
                self.logger.error("Failed to read %s sheet (%s): %s", sheet_type, sheet_id, exc)

        return records

    async def _process_record(self, record: dict[str, Any], result: IngestionResult) -> None:
        sheet_type = record.pop("__sheet_type__")
        row_num = record.pop("__row_number__")
        sheet_id = record.pop("__sheet_id__")
        source_id = f"{sheet_id}:row:{row_num}"

        if sheet_type == "tenant":
            await self._process_tenant(record, source_id, result)
        elif sheet_type == "building":
            await self._process_building(record, source_id, result)
        elif sheet_type == "vendor":
            await self._process_vendor(record, source_id, result)
        elif sheet_type == "broker":
            await self._process_broker(record, source_id, result)

    async def _process_tenant(
        self, data: dict[str, Any], source_id: str, result: IngestionResult
    ) -> None:
        name = data.get("company_name")
        if not name:
            result.add_error(f"Tenant row {source_id}: missing company_name — skipped")
            return

        pii_fields = ["email", "phone", "contact_name"]
        entity, created = await self.entity_store.upsert_entity(
            type=EntityType.CLIENT,
            name=name,
            source=DataSource.GOOGLE_SHEETS,
            source_id=source_id,
            attributes=data,
            confidence=0.9,
            pii_fields=pii_fields,
        )

        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1

        # If building is mentioned, create the relationship
        building_name = data.get("building")
        if building_name and entity:
            created_rel = await self.relationship_mapper.link_client_to_building(
                client_id=entity.id,
                building_id=await self._get_or_create_building_id(building_name),
                source=DataSource.GOOGLE_SHEETS,
                metadata={"seats": data.get("seats"), "status": data.get("status")},
            )
            if created_rel:
                result.relationships_created += 1

        # If contact is mentioned, create contact entity + link
        contact_name = data.get("contact_name")
        if contact_name:
            contact, c_created = await self.entity_store.upsert_entity(
                type=EntityType.CONTACT,
                name=contact_name,
                source=DataSource.GOOGLE_SHEETS,
                source_id=f"{source_id}:contact",
                attributes={
                    "email": data.get("email", ""),
                    "phone": data.get("phone", ""),
                    "company": name,
                },
                confidence=0.85,
                pii_fields=["email", "phone"],
            )
            if c_created:
                result.entities_created += 1

            linked = await self.relationship_mapper.link_contact_to_company(
                contact_id=contact.id,
                company_name=name,
                source=DataSource.GOOGLE_SHEETS,
            )
            if linked:
                result.relationships_created += 1

    async def _process_building(
        self, data: dict[str, Any], source_id: str, result: IngestionResult
    ) -> None:
        name = data.get("building_name")
        if not name:
            result.add_error(f"Building row {source_id}: missing building_name — skipped")
            return

        _, created = await self.entity_store.upsert_entity(
            type=EntityType.BUILDING,
            name=name,
            source=DataSource.GOOGLE_SHEETS,
            source_id=source_id,
            attributes=data,
            confidence=0.95,
        )
        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1

    async def _process_vendor(
        self, data: dict[str, Any], source_id: str, result: IngestionResult
    ) -> None:
        name = data.get("vendor_name")
        if not name:
            return

        vendor, created = await self.entity_store.upsert_entity(
            type=EntityType.VENDOR,
            name=name,
            source=DataSource.GOOGLE_SHEETS,
            source_id=source_id,
            attributes=data,
            confidence=0.9,
            pii_fields=["email", "phone", "contact_name"],
        )
        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1

    async def _process_broker(
        self, data: dict[str, Any], source_id: str, result: IngestionResult
    ) -> None:
        name = data.get("broker_name")
        if not name:
            return

        _, created = await self.entity_store.upsert_entity(
            type=EntityType.BROKER,
            name=name,
            source=DataSource.GOOGLE_SHEETS,
            source_id=source_id,
            attributes=data,
            confidence=0.9,
            pii_fields=["email", "phone"],
        )
        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1

    async def _get_or_create_building_id(self, building_name: str) -> str:
        """Find building by name or create a placeholder."""
        candidates = await self.entity_store.search_entities_by_name(
            building_name, type=EntityType.BUILDING
        )
        if candidates:
            return candidates[0].id
        building, _ = await self.entity_store.upsert_entity(
            type=EntityType.BUILDING,
            name=building_name,
            source=DataSource.GOOGLE_SHEETS,
            confidence=0.6,  # placeholder — will be updated when building sheet runs
        )
        return building.id
