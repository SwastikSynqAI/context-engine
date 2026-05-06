"""
QualityMonitor — continuous data quality checks across all entities.

Runs checks for:
- Duplicate entity detection (same name, different source IDs)
- Missing required fields per entity type
- Orphaned entities (no relationships)
- PII exposure (PII fields not tagged)
- Low-confidence entities that need review
- Data conflicts: when two ingested records for the same entity disagree on a field
  (these surface as open conflicts for human resolution)
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.entities import DataConflict, DataQualityLog, Entity, Relationship
from src.models.enums import EntityType, QualityCheckType
from src.models.schemas import QualityIssue, QualityReport

logger = logging.getLogger(__name__)

# Required attributes per entity type — checked for presence
REQUIRED_FIELDS: dict[str, list[str]] = {
    EntityType.CLIENT: ["company_name"],
    EntityType.BUILDING: ["building_name"],
    EntityType.VENDOR: ["vendor_name", "service_type"],
    EntityType.BROKER: ["broker_name"],
    EntityType.CONTACT: [],  # Just a name is enough
    EntityType.DEAL: [],
    EntityType.SPACE: [],
}

# Fields that could contain PII — if present as attribute keys, entity should tag them
PII_SENTINEL_KEYS = {"email", "phone", "mobile", "personal_email", "address", "contact_name"}


class QualityMonitor:
    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        self.settings = settings
        self.db = db

    async def run(self) -> QualityReport:
        issues: list[QualityIssue] = []
        issues += await self._check_duplicates()
        issues += await self._check_missing_fields()
        issues += await self._check_orphaned_entities()
        issues += await self._check_pii_tagging()
        issues += await self._check_low_confidence()
        issues += await self._surface_open_conflicts()

        entity_count = await self._count(Entity)
        rel_count = await self._count(Relationship)

        # Persist new issues to data_quality_log
        await self._persist_issues(issues)

        critical = sum(1 for i in issues if i.severity == "critical")
        warnings = sum(1 for i in issues if i.severity == "warning")
        health = max(0.0, 1.0 - (critical * 0.1 + warnings * 0.02))

        return QualityReport(
            total_entities=entity_count,
            total_relationships=rel_count,
            issues=issues,
            overall_health_score=round(health, 2),
            generated_at=datetime.now(UTC),
        )

    # ── Checks ────────────────────────────────────────────────────────────────

    async def _check_duplicates(self) -> list[QualityIssue]:
        """Find entities with the same name and type from different sources."""
        result = await self.db.execute(
            select(Entity.type, Entity.name, func.count().label("cnt"))
            .group_by(Entity.type, Entity.name)
            .having(func.count() > 1)
            .limit(50)
        )
        rows = result.all()
        issues = []
        for row in rows:
            issues.append(QualityIssue(
                entity_id=None,
                entity_name=row.name,
                check_type=QualityCheckType.DUPLICATE_DETECTION,
                description=f"Possible duplicate: '{row.name}' ({row.type}) appears {row.cnt} times",
                severity="warning",
            ))
        return issues

    async def _check_missing_fields(self) -> list[QualityIssue]:
        issues = []
        for entity_type, required in REQUIRED_FIELDS.items():
            if not required:
                continue
            result = await self.db.execute(
                select(Entity).where(Entity.type == entity_type, Entity.is_active == True)
            )
            entities = list(result.scalars().all())
            for entity in entities:
                for field in required:
                    if not entity.attributes.get(field):
                        issues.append(QualityIssue(
                            entity_id=entity.id,
                            entity_name=entity.name,
                            check_type=QualityCheckType.MISSING_REQUIRED_FIELD,
                            description=f"'{entity.name}' ({entity_type}) missing required field: {field}",
                            severity="warning",
                        ))
        return issues

    async def _check_orphaned_entities(self) -> list[QualityIssue]:
        """Entities with no relationships are suspicious — flag for review."""
        result = await self.db.execute(
            select(Entity.id, Entity.name, Entity.type).where(
                Entity.is_active == True,
                ~Entity.id.in_(
                    select(Relationship.from_entity_id).union(
                        select(Relationship.to_entity_id)
                    )
                ),
            ).limit(50)
        )
        rows = result.all()
        return [
            QualityIssue(
                entity_id=row.id,
                entity_name=row.name,
                check_type=QualityCheckType.ORPHANED_ENTITY,
                description=f"'{row.name}' ({row.type}) has no relationships",
                severity="info",
            )
            for row in rows
        ]

    async def _check_pii_tagging(self) -> list[QualityIssue]:
        """Flag entities that have PII attribute keys but haven't tagged them in pii_fields."""
        result = await self.db.execute(
            select(Entity).where(Entity.is_active == True).limit(500)
        )
        entities = list(result.scalars().all())
        issues = []
        for entity in entities:
            untagged_pii = []
            for key in entity.attributes:
                if key.lower() in PII_SENTINEL_KEYS and key not in entity.pii_fields:
                    untagged_pii.append(key)
            if untagged_pii:
                issues.append(QualityIssue(
                    entity_id=entity.id,
                    entity_name=entity.name,
                    check_type=QualityCheckType.PII_EXPOSURE,
                    description=(
                        f"'{entity.name}' has PII fields not tagged for DPDP compliance: "
                        f"{', '.join(untagged_pii)}"
                    ),
                    severity="critical",
                ))
        return issues

    async def _check_low_confidence(self) -> list[QualityIssue]:
        result = await self.db.execute(
            select(Entity).where(
                Entity.confidence < 0.5,
                Entity.is_active == True,
            ).limit(50)
        )
        entities = list(result.scalars().all())
        return [
            QualityIssue(
                entity_id=e.id,
                entity_name=e.name,
                check_type=QualityCheckType.CONFIDENCE_DRIFT,
                description=f"'{e.name}' ({e.type}) has low confidence: {e.confidence:.2f}",
                severity="warning",
            )
            for e in entities
        ]

    async def _surface_open_conflicts(self) -> list[QualityIssue]:
        """Include open data conflicts in the quality report so they're visible."""
        result = await self.db.execute(
            select(DataConflict).where(DataConflict.status == "open").limit(50)
        )
        conflicts = list(result.scalars().all())
        return [
            QualityIssue(
                entity_id=c.entity_id,
                entity_name=None,
                check_type="data_conflict",
                description=(
                    f"Conflict on '{c.field_name}': "
                    f"'{c.source_a}' says '{c.value_a}', "
                    f"'{c.source_b}' says '{c.value_b}'. "
                    f"Resolve at PATCH /conflicts/{c.id}/resolve"
                ),
                severity="warning",
            )
            for c in conflicts
        ]

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _persist_issues(self, issues: list[QualityIssue]) -> None:
        for issue in issues:
            if not issue.entity_id:
                continue
            log = DataQualityLog(
                id=str(uuid.uuid4()),
                entity_id=issue.entity_id,
                check_type=issue.check_type,
                status="failed" if issue.severity == "critical" else "warning",
                anomaly_description=issue.description,
            )
            self.db.add(log)
        await self.db.flush()

    async def _count(self, model) -> int:
        result = await self.db.execute(select(func.count()).select_from(model))
        return result.scalar_one()
