"""Tests for ContextEngine."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestContextEngine:
    async def test_query_returns_no_context_when_empty(self, db_session, test_settings):
        from src.reasoning.context_engine import ContextEngine

        with patch.object(ContextEngine, "_call_claude", new_callable=AsyncMock) as mock_claude:
            mock_claude.return_value = ("Test answer", None)

            engine = ContextEngine(test_settings, db_session)

            # Patch embedder to return empty results
            engine.embedder.similarity_search = AsyncMock(return_value=[])

            result = await engine.query("Who are our clients?")
            # With no embeddings, should return the no-context response
            assert "don't have enough context" in result.answer.lower() or result.context_entities_used == 0

    async def test_get_entity_context_returns_none_for_unknown(self, db_session, test_settings):
        from src.reasoning.context_engine import ContextEngine

        engine = ContextEngine(test_settings, db_session)
        result = await engine.get_entity_context("nonexistent-entity-xyz")
        assert result is None

    async def test_get_icp_with_no_decisions(self, db_session, test_settings):
        from src.reasoning.context_engine import ContextEngine

        engine = ContextEngine(test_settings, db_session)
        icp = await engine.get_icp()
        assert icp.based_on_decisions == 0
        assert icp.confidence == 0.0

    async def test_get_pricing_context_with_no_deals(self, db_session, test_settings):
        from src.reasoning.context_engine import ContextEngine
        from src.models.schemas import PricingQuery

        engine = ContextEngine(test_settings, db_session)
        result = await engine.get_pricing_context(
            PricingQuery(seats=50, location="Gurugram")
        )
        assert result.confidence < 0.5


@pytest.mark.asyncio
class TestDecisionCapture:
    async def test_capture_creates_decision(self, db_session):
        from src.reasoning.decision_capture import DecisionCaptureService
        from src.models.schemas import ExpertDecisionCreate
        from src.models.enums import DecisionType, DecisionActor

        service = DecisionCaptureService(db_session)
        data = ExpertDecisionCreate(
            decision_type=DecisionType.LEAD_APPROVAL,
            actor=DecisionActor.ADMIN,
            context_snapshot={"company": "Acme", "industry": "fintech", "seats": 100},
            human_action="Approved — strong ICP fit, recently funded BFSI company",
            primary_entity_id=None,
        )
        result = await service.capture(data)
        assert result.id is not None
        assert result.decision_type == DecisionType.LEAD_APPROVAL
        assert result.actor == DecisionActor.ADMIN

    async def test_record_outcome_updates_feedback(self, db_session):
        from src.reasoning.decision_capture import DecisionCaptureService
        from src.models.schemas import ExpertDecisionCreate
        from src.models.enums import DecisionType, DecisionActor

        service = DecisionCaptureService(db_session)
        decision = await service.capture(
            ExpertDecisionCreate(
                decision_type=DecisionType.LEAD_APPROVAL,
                actor=DecisionActor.ADMIN,
                context_snapshot={"company": "TestCo"},
                human_action="Approved",
            )
        )

        updated = await service.record_outcome(
            decision_id=decision.id,
            outcome="deal_closed",
            feedback_signal="positive",
        )
        assert updated.outcome == "deal_closed"
        assert updated.feedback_signal == "positive"
