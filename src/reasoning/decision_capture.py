"""
DecisionCapture — handles the recording of expert decisions as training signal.

Every time Admin approves a lead, rejects a vendor, closes a deal, or makes any
significant commercial decision, that event should be captured here with the full
context snapshot at decision time.

The context snapshot is COPIED, not referenced — it must be immutable.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.entity_store import EntityStore
from src.models.entities import ExpertDecision
from src.models.enums import DecisionActor, DecisionType
from src.models.schemas import ExpertDecisionCreate, ExpertDecisionRead


class DecisionCaptureService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.store = EntityStore(db)

    async def capture(self, decision_data: ExpertDecisionCreate) -> ExpertDecisionRead:
        """
        Record an expert decision.

        The context_snapshot in decision_data should contain everything relevant
        at decision time — do not pass references, pass the actual data.
        """
        # Enrich context snapshot with current entity state if primary_entity_id is given
        snapshot = dict(decision_data.context_snapshot)
        if decision_data.primary_entity_id:
            entity = await self.store.get_entity_by_id(decision_data.primary_entity_id)
            if entity:
                snapshot["_entity_state_at_decision"] = {
                    "id": entity.id,
                    "type": entity.type,
                    "name": entity.name,
                    "attributes": entity.attributes,
                    "confidence": entity.confidence,
                    "captured_at": datetime.now(UTC).isoformat(),
                }

        decision = ExpertDecision(
            id=str(uuid.uuid4()),
            decision_type=decision_data.decision_type,
            actor=decision_data.actor,
            context_snapshot=snapshot,
            human_action=decision_data.human_action,
            human_reasoning=decision_data.human_reasoning,
            primary_entity_id=decision_data.primary_entity_id,
        )

        self.db.add(decision)
        await self.db.flush()
        return ExpertDecisionRead.model_validate(decision)

    async def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        outcome_notes: str | None = None,
        feedback_signal: str = "neutral",
    ) -> ExpertDecisionRead | None:
        """
        Record the outcome of a decision asynchronously (called when we know what happened).
        feedback_signal: "positive" | "negative" | "neutral"
        """
        from sqlalchemy import select
        result = await self.db.execute(
            select(ExpertDecision).where(ExpertDecision.id == decision_id)
        )
        decision = result.scalar_one_or_none()
        if not decision:
            return None

        decision.outcome = outcome
        decision.outcome_notes = outcome_notes
        decision.feedback_signal = feedback_signal
        decision.outcome_recorded_at = datetime.now(UTC)

        # Update entity confidence based on outcome
        if decision.primary_entity_id and feedback_signal in ("positive", "negative"):
            await self._adjust_entity_confidence(
                decision.primary_entity_id,
                positive=(feedback_signal == "positive"),
            )

        await self.db.flush()
        return ExpertDecisionRead.model_validate(decision)

    async def get_decisions_for_entity(
        self, entity_id: str, limit: int = 20
    ) -> list[ExpertDecisionRead]:
        from sqlalchemy import select
        result = await self.db.execute(
            select(ExpertDecision)
            .where(ExpertDecision.primary_entity_id == entity_id)
            .order_by(ExpertDecision.timestamp.desc())
            .limit(limit)
        )
        return [ExpertDecisionRead.model_validate(d) for d in result.scalars().all()]

    async def get_decisions_by_actor(
        self, actor: DecisionActor, decision_type: DecisionType | None = None, limit: int = 50
    ) -> list[ExpertDecisionRead]:
        from sqlalchemy import select
        query = (
            select(ExpertDecision)
            .where(ExpertDecision.actor == actor)
            .order_by(ExpertDecision.timestamp.desc())
            .limit(limit)
        )
        if decision_type:
            query = query.where(ExpertDecision.decision_type == decision_type)
        result = await self.db.execute(query)
        return [ExpertDecisionRead.model_validate(d) for d in result.scalars().all()]

    # ── Private ───────────────────────────────────────────────────────────────

    async def _adjust_entity_confidence(
        self, entity_id: str, positive: bool
    ) -> None:
        """Nudge entity confidence up/down based on decision outcome feedback."""
        entity = await self.store.get_entity_by_id(entity_id)
        if not entity:
            return
        delta = 0.05 if positive else -0.05
        entity.confidence = max(0.1, min(1.0, entity.confidence + delta))
        await self.db.flush()
