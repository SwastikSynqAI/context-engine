"""
ApplicationService — orchestrates the full intake pipeline for a new application.

Called by the POST /hr/apply endpoint. Also usable directly from Playwright
inbound pullers and the email parser (they pass a CandidateCreate + optional bytes).

Pipeline:
1. Dedup check (against existing candidate entities)
2. Save resume file to uploads/resumes/
3. Extract resume text
4. Upsert candidate entity (type='candidate') in entities table
5. Create hr_application row
6. Log to hr_activity_log
7. Return result (entity_id, application_id, is_duplicate, stage)

Scoring and acknowledgement are triggered as FastAPI BackgroundTasks by the
route handler — not here — so the HTTP response returns immediately.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.engines.hr.inbound.deduplication import DeduplicationChecker
from src.engines.hr.inbound.resume_extractor import extract_text_from_bytes
from src.engines.hr.models import CandidateCreate, CandidateStage
from src.models.enums import DataSource, EntityType

logger = logging.getLogger(__name__)


class ApplicationService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def process(
        self,
        *,
        candidate: CandidateCreate,
        resume_bytes: bytes | None = None,
        resume_filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Full intake pipeline. Returns a result dict with:
        - entity_id: str
        - application_id: str
        - is_duplicate: bool
        - existing_entity_id: str | None
        - stage: str
        - resume_path: str | None
        - resume_text: str
        """
        # 1. Fetch existing candidates for dedup (email + phone lookup)
        existing = await self._fetch_existing_candidates(
            email=candidate.email,
            phone=candidate.phone,
        )

        checker = DeduplicationChecker()
        dedup = checker.check(
            incoming_name=candidate.name,
            incoming_email=candidate.email,
            incoming_phone=candidate.phone,
            existing_candidates=existing,
        )

        if dedup.is_duplicate:
            logger.info(
                "Duplicate candidate detected: %s (match: %s, existing: %s)",
                candidate.email, dedup.match_reason, dedup.existing_entity_id,
            )
            application_id = await self._create_application(
                candidate_entity_id=dedup.existing_entity_id,
                candidate=candidate,
                resume_path=None,
                resume_text="",
            )
            return {
                "entity_id": dedup.existing_entity_id,
                "application_id": application_id,
                "is_duplicate": True,
                "existing_entity_id": dedup.existing_entity_id,
                "stage": CandidateStage.APPLIED.value,
                "resume_path": None,
                "resume_text": "",
            }

        # 2. Save resume file
        resume_path, resume_text = None, ""
        if resume_bytes and resume_filename:
            resume_path = await self._save_resume(resume_bytes, resume_filename)
            try:
                resume_text = extract_text_from_bytes(resume_bytes, filename=resume_filename)
            except Exception as exc:
                logger.warning("Resume text extraction failed: %s", exc)

        # 3. Upsert candidate entity
        source_map = {
            "careers_form": DataSource.CAREERS_FORM,
            "linkedin_inbound": DataSource.LINKEDIN_INBOUND,
            "linkedin_sourced": DataSource.LINKEDIN_SOURCED,
            "naukri": DataSource.NAUKRI,
            "email": DataSource.GMAIL,
            "manual": DataSource.MANUAL,
        }
        source = source_map.get(candidate.source, DataSource.MANUAL)

        attrs = candidate.to_entity_attributes()
        attrs["email"] = candidate.email
        attrs["phone"] = candidate.phone
        if resume_path:
            attrs["resume_path"] = resume_path

        entity_id = await self._upsert_candidate_entity(
            name=candidate.name,
            source=source,
            source_id=candidate.email,
            attributes=attrs,
            pii_fields=candidate.pii_fields,
        )

        # 4. Create application row
        application_id = await self._create_application(
            candidate_entity_id=entity_id,
            candidate=candidate,
            resume_path=resume_path,
            resume_text=resume_text,
        )

        # 5. Log activity
        await self._log_activity(
            candidate_entity_id=entity_id,
            application_id=application_id,
            action="application_received",
            details={
                "source": candidate.source,
                "role": candidate.role,
                "resume_filename": resume_filename,
            },
        )

        await self.db.flush()

        return {
            "entity_id": entity_id,
            "application_id": application_id,
            "is_duplicate": False,
            "existing_entity_id": None,
            "stage": CandidateStage.APPLIED.value,
            "resume_path": resume_path,
            "resume_text": resume_text[:500] if resume_text else "",
        }

    async def _fetch_existing_candidates(
        self, *, email: str, phone: str | None
    ) -> list[dict[str, Any]]:
        """Fetch candidates by email or phone for dedup check."""
        result = await self.db.execute(
            text(
                "SELECT id, name, attributes->>'email' AS email, "
                "attributes->>'phone' AS phone "
                "FROM entities WHERE type = 'candidate' "
                "AND (attributes->>'email' = :email OR attributes->>'phone' = :phone)"
            ),
            {"email": email, "phone": phone or ""},
        )
        rows = result.fetchall()
        return [
            {
                "entity_id": str(row.id),
                "name": row.name,
                "email": row.email or "",
                "phone": row.phone,
            }
            for row in rows
        ]

    async def _upsert_candidate_entity(
        self,
        *,
        name: str,
        source: DataSource,
        source_id: str,
        attributes: dict[str, Any],
        pii_fields: list[str],
    ) -> str:
        """Upsert a candidate entity. Returns the entity id (str)."""
        import json
        entity_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        await self.db.execute(
            text(
                "INSERT INTO entities (id, type, name, source, source_id, attributes, pii_fields, confidence, created_at, updated_at) "
                "VALUES (:id, 'candidate', :name, :source, :source_id, CAST(:attributes AS jsonb), CAST(:pii_fields AS jsonb), 1.0, :now, :now) "
                "ON CONFLICT (source, source_id) DO UPDATE SET "
                "attributes = EXCLUDED.attributes, updated_at = EXCLUDED.updated_at "
                "RETURNING id"
            ),
            {
                "id": entity_id,
                "name": name,
                "source": source.value,
                "source_id": source_id,
                "attributes": json.dumps(attributes),
                "pii_fields": json.dumps(pii_fields),
                "now": now,
            },
        )
        # Fetch the actual id (could be existing entity on conflict)
        result = await self.db.execute(
            text("SELECT id FROM entities WHERE source = :source AND source_id = :source_id"),
            {"source": source.value, "source_id": source_id},
        )
        row = result.fetchone()
        return str(row.id) if row else entity_id

    async def _save_resume(self, resume_bytes: bytes, filename: str) -> str:
        """Save resume bytes to uploads/resumes/ and return the path."""
        upload_dir = Path(self.settings.uploads_resumes_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        ext = filename.rsplit(".", 1)[-1].lower()
        safe_id = str(uuid.uuid4())
        dest = upload_dir / f"{safe_id}.{ext}"
        dest.write_bytes(resume_bytes)
        return str(dest)

    async def _create_application(
        self,
        *,
        candidate_entity_id: str,
        candidate: CandidateCreate,
        resume_path: str | None,
        resume_text: str,
    ) -> str:
        import json
        app_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        await self.db.execute(
            text(
                "INSERT INTO hr_applications "
                "(id, candidate_entity_id, role_type, source, stage, "
                "resume_path, resume_text, stage_history, created_at, updated_at) "
                "VALUES (:id, :candidate_entity_id, :role_type, :source, :stage, "
                ":resume_path, :resume_text, CAST(:stage_history AS jsonb), :created_at, :updated_at) "
                "ON CONFLICT (candidate_entity_id, role_type) DO NOTHING"
            ),
            {
                "id": app_id,
                "candidate_entity_id": candidate_entity_id,
                "role_type": candidate.role,
                "source": candidate.source,
                "stage": CandidateStage.APPLIED.value,
                "resume_path": resume_path,
                "resume_text": resume_text,
                "stage_history": json.dumps([{"stage": "applied", "timestamp": now.isoformat()}]),
                "created_at": now,
                "updated_at": now,
            },
        )
        return app_id

    async def _log_activity(
        self,
        *,
        candidate_entity_id: str,
        application_id: str,
        action: str,
        details: dict[str, Any],
    ) -> None:
        import json
        await self.db.execute(
            text(
                "INSERT INTO hr_activity_log "
                "(id, candidate_entity_id, application_id, action, details, performed_by, created_at) "
                "VALUES (:id, :candidate_entity_id, :application_id, :action, "
                "CAST(:details AS jsonb), 'system', :created_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "candidate_entity_id": candidate_entity_id,
                "application_id": application_id,
                "action": action,
                "details": json.dumps(details),
                "created_at": datetime.now(UTC),
            },
        )
