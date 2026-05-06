"""
Self-improvement evaluator — runs weekly to score context response quality.

What it does:
1. Finds decisions that have recorded outcomes
2. Checks whether the context_snapshot at decision time would have led to the correct answer
3. Flags entities where confidence is misaligned with outcomes
4. Detects ICP drift — when the enterprise's customer patterns have shifted
5. Updates entity confidence scores based on outcome feedback history
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.entities import DataQualityLog, Entity, ExpertDecision
from src.models.enums import QualityCheckType

logger = logging.getLogger(__name__)


class SelfImprovementEvaluator:
    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        self.settings = settings
        self.db = db

    async def run(self) -> dict:
        """
        Full weekly evaluation pass. Returns a summary dict.
        """
        logger.info("Starting weekly self-improvement evaluation")
        results = {
            "started_at": datetime.now(UTC).isoformat(),
            "confidence_adjustments": 0,
            "drift_signals": [],
            "quality_issues_flagged": 0,
        }

        results["confidence_adjustments"] = await self._recalibrate_confidence()
        results["drift_signals"] = await self._detect_icp_drift()
        results["quality_issues_flagged"] = await self._flag_stale_entities()

        results["finished_at"] = datetime.now(UTC).isoformat()
        logger.info("Evaluation complete: %s", results)
        return results

    async def _recalibrate_confidence(self) -> int:
        """
        For each entity that has decisions with outcomes, recalculate confidence
        based on the ratio of positive to total outcomes.
        """
        result = await self.db.execute(
            select(
                ExpertDecision.primary_entity_id,
                func.count().label("total"),
                func.sum(
                    func.cast(ExpertDecision.feedback_signal == "positive", type_=func.Integer)
                ).label("positive_count"),
            )
            .where(
                ExpertDecision.primary_entity_id.isnot(None),
                ExpertDecision.feedback_signal.isnot(None),
            )
            .group_by(ExpertDecision.primary_entity_id)
        )
        rows = result.all()
        adjusted = 0

        for row in rows:
            entity_id = row.primary_entity_id
            total = row.total or 0
            positive = row.positive_count or 0
            if total == 0:
                continue

            outcome_ratio = positive / total
            # Map outcome ratio [0, 1] to confidence [0.3, 0.95]
            new_confidence = 0.3 + outcome_ratio * 0.65

            entity_result = await self.db.execute(
                select(Entity).where(Entity.id == entity_id)
            )
            entity = entity_result.scalar_one_or_none()
            if entity:
                old_conf = entity.confidence
                entity.confidence = round(new_confidence, 2)
                if abs(old_conf - entity.confidence) > 0.05:
                    logger.debug(
                        "Confidence recalibrated for %s: %.2f → %.2f",
                        entity.name, old_conf, entity.confidence
                    )
                    adjusted += 1

        await self.db.flush()
        return adjusted

    async def _detect_icp_drift(self) -> list[str]:
        """
        Compare recent decisions (last 30 days) to historical decisions.
        Flag if the distribution of approved lead industries/sizes has shifted.
        """
        drift_signals = []
        cutoff = datetime.now(UTC) - timedelta(days=30)

        recent_result = await self.db.execute(
            select(ExpertDecision).where(
                ExpertDecision.decision_type == "lead_approval",
                ExpertDecision.timestamp >= cutoff,
            )
        )
        recent = list(recent_result.scalars().all())

        historical_result = await self.db.execute(
            select(ExpertDecision).where(
                ExpertDecision.decision_type == "lead_approval",
                ExpertDecision.timestamp < cutoff,
            ).limit(200)
        )
        historical = list(historical_result.scalars().all())

        if len(recent) < 3 or len(historical) < 5:
            return []  # Insufficient data

        # Extract industries from context snapshots
        def extract_industries(decisions: list[ExpertDecision]) -> dict[str, int]:
            counts: dict[str, int] = {}
            for d in decisions:
                ind = d.context_snapshot.get("industry", "").lower().strip()
                if ind:
                    counts[ind] = counts.get(ind, 0) + 1
            return counts

        recent_industries = extract_industries(recent)
        hist_industries = extract_industries(historical)

        # Find industries present in recent but not historical (new verticals)
        new_verticals = set(recent_industries) - set(hist_industries)
        if new_verticals:
            drift_signals.append(f"New industries in recent approvals: {', '.join(new_verticals)}")

        # Find industries that were common historically but absent recently (drift away)
        hist_top = {k for k, v in hist_industries.items() if v >= 3}
        disappeared = hist_top - set(recent_industries)
        if disappeared:
            drift_signals.append(f"Industries declining in approvals: {', '.join(disappeared)}")

        return drift_signals

    async def _flag_stale_entities(self) -> int:
        """Flag entities that haven't been updated in 30 days as potentially stale."""
        stale_cutoff = datetime.now(UTC) - timedelta(days=30)
        result = await self.db.execute(
            select(Entity).where(
                Entity.updated_at < stale_cutoff,
                Entity.is_active == True,
            ).limit(100)
        )
        stale_entities = list(result.scalars().all())
        count = 0

        for entity in stale_entities:
            # Only flag once — check if already flagged
            existing = await self.db.execute(
                select(DataQualityLog).where(
                    DataQualityLog.entity_id == entity.id,
                    DataQualityLog.check_type == QualityCheckType.STALE_DATA,
                    DataQualityLog.resolved == False,
                )
            )
            if existing.scalar_one_or_none():
                continue

            import uuid
            log = DataQualityLog(
                id=str(uuid.uuid4()),
                entity_id=entity.id,
                check_type=QualityCheckType.STALE_DATA,
                status="warning",
                anomaly_description=(
                    f"Entity '{entity.name}' ({entity.type}) has not been updated since "
                    f"{entity.updated_at.strftime('%Y-%m-%d')}. Re-run ingestion."
                ),
            )
            self.db.add(log)
            count += 1

        await self.db.flush()
        return count
