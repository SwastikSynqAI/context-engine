"""
HubSpot ingester — pulls deals, contacts, and companies from HubSpot CRM.

Maps HubSpot objects → Context Engine entity types:
  HubSpot Deal    → EntityType.DEAL
  HubSpot Contact → EntityType.CONTACT
  HubSpot Company → EntityType.CLIENT
"""

from __future__ import annotations

import logging
from typing import Any

import hubspot
from hubspot.crm.companies import ApiException as CompanyApiException
from hubspot.crm.contacts import ApiException as ContactApiException
from hubspot.crm.deals import ApiException as DealApiException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.ingestion.base import BaseIngester, IngestionResult
from src.models.enums import DataSource, EntityType, RelationshipType

logger = logging.getLogger(__name__)

DEAL_PROPERTIES = [
    "dealname", "amount", "dealstage", "closedate", "pipeline",
    "hubspot_owner_id", "hs_deal_stage_probability",
]
CONTACT_PROPERTIES = [
    "firstname", "lastname", "email", "phone", "jobtitle", "company",
]
COMPANY_PROPERTIES = [
    "name", "domain", "industry", "numberofemployees", "city", "country",
    "annualrevenue",
]


class HubSpotIngester(BaseIngester):
    source_name = DataSource.HUBSPOT

    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        super().__init__(settings, db)
        self._client = hubspot.Client.create(access_token=settings.hubspot_api_key)

    # ── BaseIngester interface ────────────────────────────────────────────────

    async def _fetch_raw(self) -> list[dict[str, Any]]:
        """Fetch all deals, contacts, and companies. Tag each record with __hs_type__."""
        records = []
        records += await self._fetch_deals()
        records += await self._fetch_contacts()
        records += await self._fetch_companies()
        return records

    async def _process_record(self, record: dict[str, Any], result: IngestionResult) -> None:
        hs_type = record.pop("__hs_type__")
        if hs_type == "deal":
            await self._process_deal(record, result)
        elif hs_type == "contact":
            await self._process_contact(record, result)
        elif hs_type == "company":
            await self._process_company(record, result)

    # ── Fetch methods ─────────────────────────────────────────────────────────

    async def _fetch_deals(self) -> list[dict[str, Any]]:
        records = []
        after = None
        while True:
            try:
                kwargs = {
                    "limit": 100,
                    "properties": DEAL_PROPERTIES,
                    "associations": ["contacts", "companies"],
                }
                if after:
                    kwargs["after"] = after

                page = self._client.crm.deals.basic_api.get_page(**kwargs)
                for deal in page.results:
                    r = {"__hs_type__": "deal", "__hs_id__": deal.id}
                    r.update(deal.properties or {})
                    # Flatten associations
                    if deal.associations:
                        if deal.associations.contacts:
                            r["__contact_ids__"] = [
                                a.id for a in deal.associations.contacts.results
                            ]
                        if deal.associations.companies:
                            r["__company_ids__"] = [
                                a.id for a in deal.associations.companies.results
                            ]
                    records.append(r)

                if not page.paging or not page.paging.next:
                    break
                after = page.paging.next.after
            except DealApiException as exc:
                self.logger.error("HubSpot deals API error: %s", exc)
                break
        return records

    async def _fetch_contacts(self) -> list[dict[str, Any]]:
        records = []
        after = None
        while True:
            try:
                kwargs = {"limit": 100, "properties": CONTACT_PROPERTIES}
                if after:
                    kwargs["after"] = after
                page = self._client.crm.contacts.basic_api.get_page(**kwargs)
                for contact in page.results:
                    r = {"__hs_type__": "contact", "__hs_id__": contact.id}
                    r.update(contact.properties or {})
                    records.append(r)
                if not page.paging or not page.paging.next:
                    break
                after = page.paging.next.after
            except ContactApiException as exc:
                self.logger.error("HubSpot contacts API error: %s", exc)
                break
        return records

    async def _fetch_companies(self) -> list[dict[str, Any]]:
        records = []
        after = None
        while True:
            try:
                kwargs = {"limit": 100, "properties": COMPANY_PROPERTIES}
                if after:
                    kwargs["after"] = after
                page = self._client.crm.companies.basic_api.get_page(**kwargs)
                for company in page.results:
                    r = {"__hs_type__": "company", "__hs_id__": company.id}
                    r.update(company.properties or {})
                    records.append(r)
                if not page.paging or not page.paging.next:
                    break
                after = page.paging.next.after
            except CompanyApiException as exc:
                self.logger.error("HubSpot companies API error: %s", exc)
                break
        return records

    # ── Process methods ───────────────────────────────────────────────────────

    async def _process_deal(self, data: dict[str, Any], result: IngestionResult) -> None:
        hs_id = data.pop("__hs_id__")
        contact_ids = data.pop("__contact_ids__", [])
        company_ids = data.pop("__company_ids__", [])

        name = data.get("dealname") or f"Deal {hs_id}"
        attrs = {
            "deal_name": name,
            "amount": data.get("amount"),
            "deal_stage": data.get("dealstage"),
            "close_date": data.get("closedate"),
            "pipeline": data.get("pipeline"),
        }

        deal, created = await self.entity_store.upsert_entity(
            type=EntityType.DEAL,
            name=name,
            source=DataSource.HUBSPOT,
            source_id=f"hs_deal:{hs_id}",
            attributes=attrs,
            confidence=0.95,
        )
        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1

        # Link deal to contacts
        for contact_id in contact_ids:
            contact = await self.entity_store.get_entity_by_source(
                DataSource.HUBSPOT, f"hs_contact:{contact_id}"
            )
            if contact:
                _, rel_created = await self.entity_store.upsert_relationship(
                    from_entity_id=contact.id,
                    to_entity_id=deal.id,
                    relationship_type=RelationshipType.PART_OF_DEAL,
                    source=DataSource.HUBSPOT,
                )
                if rel_created:
                    result.relationships_created += 1

        # Link deal to companies
        for company_id in company_ids:
            company = await self.entity_store.get_entity_by_source(
                DataSource.HUBSPOT, f"hs_company:{company_id}"
            )
            if company:
                _, rel_created = await self.entity_store.upsert_relationship(
                    from_entity_id=company.id,
                    to_entity_id=deal.id,
                    relationship_type=RelationshipType.PART_OF_DEAL,
                    source=DataSource.HUBSPOT,
                )
                if rel_created:
                    result.relationships_created += 1

    async def _process_contact(self, data: dict[str, Any], result: IngestionResult) -> None:
        hs_id = data.pop("__hs_id__")
        first = data.get("firstname", "")
        last = data.get("lastname", "")
        name = f"{first} {last}".strip() or f"Contact {hs_id}"

        attrs = {
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "job_title": data.get("jobtitle", ""),
            "company": data.get("company", ""),
        }

        contact, created = await self.entity_store.upsert_entity(
            type=EntityType.CONTACT,
            name=name,
            source=DataSource.HUBSPOT,
            source_id=f"hs_contact:{hs_id}",
            attributes=attrs,
            confidence=0.95,
            pii_fields=["email", "phone"],
        )
        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1

        # Link contact to company if mentioned
        company_name = data.get("company")
        if company_name and contact:
            linked = await self.relationship_mapper.link_contact_to_company(
                contact_id=contact.id,
                company_name=company_name,
                source=DataSource.HUBSPOT,
            )
            if linked:
                result.relationships_created += 1

    async def _process_company(self, data: dict[str, Any], result: IngestionResult) -> None:
        hs_id = data.pop("__hs_id__")
        name = data.get("name") or f"Company {hs_id}"

        attrs = {
            "company_name": name,
            "domain": data.get("domain", ""),
            "industry": data.get("industry", ""),
            "company_size": data.get("numberofemployees", ""),
            "city": data.get("city", ""),
            "country": data.get("country", ""),
        }

        _, created = await self.entity_store.upsert_entity(
            type=EntityType.CLIENT,
            name=name,
            source=DataSource.HUBSPOT,
            source_id=f"hs_company:{hs_id}",
            attributes=attrs,
            confidence=0.95,
        )
        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1
