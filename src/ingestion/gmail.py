"""
Gmail ingester — reads threaded conversations and extracts entity mentions + relationships.

Strategy:
1. Fetch threads from the configured Gmail account (last N days)
2. For each thread, ask Claude to extract mentioned entities and relationships
3. Upsert extracted entities/relationships with source=gmail and lower confidence
   (email is informal — we trust Sheets/HubSpot more)

Requires OAuth2 (not service account) since Gmail access is user-specific.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime, timedelta
from email import message_from_bytes
from typing import Any

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.ingestion.base import BaseIngester, IngestionResult
from src.models.enums import DataSource, EntityType, RelationshipType

logger = logging.getLogger(__name__)

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

ENTITY_EXTRACTION_PROMPT = """You are a data extraction assistant for YourCompany, a managed office company.

Extract all entity mentions from this email thread. Focus on:
- Company/client names
- Building/property names
- Broker names and their firms
- Vendor names
- Contact names and their roles

For each entity, determine:
- Entity type: client | building | broker | vendor | contact
- Name
- Any attributes mentioned (email, phone, company, seat count, deal value, etc.)
- Relationships implied (e.g. "XYZ Corp is looking at our Gurugram building" → client PART_OF_DEAL with building)

Email thread:
{thread_text}

Respond as JSON array: [{{"type": "...", "name": "...", "attributes": {{}}, "relationships": []}}]
If no relevant entities found, return [].
"""


class GmailIngester(BaseIngester):
    source_name = DataSource.GMAIL

    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        super().__init__(settings, db)
        self._service = None
        self._anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _get_service(self):
        if self._service is not None:
            return self._service

        creds = None
        import os
        token_path = self.settings.google_oauth_token_json

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.settings.google_oauth_credentials_json, GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    # ── BaseIngester interface ────────────────────────────────────────────────

    async def _fetch_raw(self) -> list[dict[str, Any]]:
        service = self._get_service()
        user_id = self.settings.gmail_user_email or "me"

        # Fetch threads from last 7 days
        cutoff = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y/%m/%d")
        results = (
            service.users()
            .threads()
            .list(userId=user_id, q=f"after:{cutoff}", maxResults=100)
            .execute()
        )
        threads = results.get("threads", [])

        raw_records = []
        for thread_meta in threads:
            try:
                thread = (
                    service.users()
                    .threads()
                    .get(userId=user_id, id=thread_meta["id"], format="full")
                    .execute()
                )
                thread_text = self._extract_thread_text(thread)
                if len(thread_text.strip()) < 50:
                    continue
                raw_records.append({
                    "thread_id": thread_meta["id"],
                    "thread_text": thread_text,
                    "message_count": len(thread.get("messages", [])),
                })
            except Exception as exc:
                self.logger.warning("Failed to fetch thread %s: %s", thread_meta["id"], exc)

        return raw_records

    async def _process_record(self, record: dict[str, Any], result: IngestionResult) -> None:
        thread_id = record["thread_id"]
        thread_text = record["thread_text"]

        # Extract entities using Claude
        extracted = await self._extract_entities(thread_text)

        for item in extracted:
            entity_type = item.get("type")
            name = item.get("name", "").strip()
            if not name or not entity_type:
                continue

            try:
                entity_type_enum = EntityType(entity_type)
            except ValueError:
                continue

            entity, created = await self.entity_store.upsert_entity(
                type=entity_type_enum,
                name=name,
                source=DataSource.GMAIL,
                source_id=f"gmail:{thread_id}:{entity_type}:{name[:50]}",
                attributes=item.get("attributes", {}),
                confidence=0.7,  # Email is informal — lower confidence than CRM
                pii_fields=["email", "phone"] if entity_type in ("contact", "broker") else [],
            )

            if created:
                result.entities_created += 1
            else:
                result.entities_updated += 1

            # Process implied relationships
            for rel in item.get("relationships", []):
                await self._process_relationship(entity, rel, thread_id, result)

    async def _extract_entities(self, thread_text: str) -> list[dict]:
        import json
        prompt = ENTITY_EXTRACTION_PROMPT.format(thread_text=thread_text[:4000])
        try:
            message = self._anthropic.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as exc:
            self.logger.warning("Entity extraction failed for thread: %s", exc)
            return []

    async def _process_relationship(
        self, entity, rel: dict, thread_id: str, result: IngestionResult
    ) -> None:
        rel_type_str = rel.get("type", "")
        target_name = rel.get("target", "")
        if not rel_type_str or not target_name:
            return

        try:
            rel_type = RelationshipType(rel_type_str)
        except ValueError:
            return

        # Find target entity
        target_type = rel.get("target_type")
        candidates = await self.entity_store.search_entities_by_name(
            target_name,
            type=EntityType(target_type) if target_type else None,
        )
        if not candidates:
            return

        _, created = await self.entity_store.upsert_relationship(
            from_entity_id=entity.id,
            to_entity_id=candidates[0].id,
            relationship_type=rel_type,
            source=DataSource.GMAIL,
            metadata={"thread_id": thread_id},
            confidence=0.65,
        )
        if created:
            result.relationships_created += 1

    def _extract_thread_text(self, thread: dict) -> str:
        """Extract plain text from a Gmail thread."""
        parts = []
        for message in thread.get("messages", []):
            payload = message.get("payload", {})
            parts.append(self._extract_message_text(payload))
        return "\n---\n".join(p for p in parts if p.strip())

    def _extract_message_text(self, payload: dict) -> str:
        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {})
        data = body.get("data", "")

        if data and "text/plain" in mime_type:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

        text_parts = []
        for part in payload.get("parts", []):
            if "text/plain" in part.get("mimeType", ""):
                part_data = part.get("body", {}).get("data", "")
                if part_data:
                    text_parts.append(
                        base64.urlsafe_b64decode(part_data + "==").decode("utf-8", errors="replace")
                    )
        return "\n".join(text_parts)
