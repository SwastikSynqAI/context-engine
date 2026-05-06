"""
Document ingester — parses PDFs (contracts, proposals) and extracts entities.

Uses pypdf for text extraction and Claude for entity/clause extraction.
Each document becomes an entity of type DEAL (contracts) or CLIENT (proposals)
with the raw text chunks stored as embeddings.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

import anthropic
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.ingestion.base import BaseIngester, IngestionResult
from src.models.enums import ContentType, DataSource, EntityType

logger = logging.getLogger(__name__)

DOCUMENT_EXTRACTION_PROMPT = """You are a contract and document analyst for YourCompany, a managed office company.

Extract key information from the following document text:
1. Client/company name
2. Property/building name and location
3. Number of seats / sq ft
4. Monthly/annual value or rent
5. Contract duration (start date, end date)
6. Key contacts (names, emails)
7. Special terms or exceptions
8. Broker involved (if any)

Document text:
{text}

Return as JSON:
{{
  "document_type": "contract|proposal|mou|other",
  "client_name": "",
  "building_name": "",
  "seats": null,
  "monthly_value": null,
  "start_date": "",
  "end_date": "",
  "contacts": [],
  "broker_name": "",
  "special_terms": []
}}
"""


class DocumentIngester(BaseIngester):
    source_name = DataSource.DOCUMENT

    # Directory to scan for documents (can be configured)
    DOCUMENTS_DIR = "documents"

    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        super().__init__(settings, db)
        self._anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def _fetch_raw(self) -> list[dict[str, Any]]:
        docs_path = Path(self.DOCUMENTS_DIR)
        if not docs_path.exists():
            self.logger.info("Documents directory '%s' does not exist — skipping", self.DOCUMENTS_DIR)
            return []

        records = []
        for pdf_path in docs_path.rglob("*.pdf"):
            try:
                text = self._extract_pdf_text(pdf_path)
                if len(text.strip()) < 100:
                    continue
                file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]
                records.append({
                    "file_path": str(pdf_path),
                    "file_name": pdf_path.name,
                    "file_hash": file_hash,
                    "text": text,
                })
            except Exception as exc:
                self.logger.warning("Failed to read %s: %s", pdf_path, exc)

        return records

    async def _process_record(self, record: dict[str, Any], result: IngestionResult) -> None:
        import json

        file_path = record["file_path"]
        file_hash = record["file_hash"]
        text = record["text"]
        file_name = record["file_name"]

        # Extract structured data with Claude
        prompt = DOCUMENT_EXTRACTION_PROMPT.format(text=text[:6000])
        try:
            message = self._anthropic.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            extracted = json.loads(raw.strip())
        except Exception as exc:
            self.logger.warning("Extraction failed for %s: %s", file_name, exc)
            extracted = {}

        doc_type = extracted.get("document_type", "other")
        client_name = extracted.get("client_name", "")
        entity_name = client_name or f"Document: {file_name}"

        # Create/update a DEAL entity for contracts, CLIENT for proposals
        entity_type = EntityType.DEAL if doc_type == "contract" else EntityType.CLIENT

        attrs = {
            "document_type": doc_type,
            "file_name": file_name,
            "file_path": file_path,
            "client_name": client_name,
            "building_name": extracted.get("building_name", ""),
            "seats": extracted.get("seats"),
            "monthly_value": extracted.get("monthly_value"),
            "start_date": extracted.get("start_date", ""),
            "end_date": extracted.get("end_date", ""),
            "special_terms": extracted.get("special_terms", []),
        }

        entity, created = await self.entity_store.upsert_entity(
            type=entity_type,
            name=entity_name,
            source=DataSource.DOCUMENT,
            source_id=f"doc:{file_hash}",
            attributes=attrs,
            confidence=0.85,
        )

        if created:
            result.entities_created += 1
        else:
            result.entities_updated += 1

        # Link to building if mentioned
        building_name = extracted.get("building_name")
        if building_name and entity:
            await self.relationship_mapper.link_space_to_building(
                space_id=entity.id,
                building_name=building_name,
                source=DataSource.DOCUMENT,
                metadata={"document": file_name},
            )
            result.relationships_created += 1

        # Store document chunks as embeddings
        from src.graph.embedder import Embedder
        embedder = Embedder(self.settings, self.db)
        await embedder.embed_entity(entity)

    def _extract_pdf_text(self, path: Path) -> str:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
