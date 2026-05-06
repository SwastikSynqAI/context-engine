"""Integration tests for the FastAPI endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_returns_200(self, test_client):
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "db_connected" in data

    async def test_health_has_counts(self, test_client):
        response = await test_client.get("/health")
        data = response.json()
        assert "entity_count" in data
        assert "relationship_count" in data


@pytest.mark.asyncio
class TestContextEndpoints:
    async def test_query_context_returns_200(self, test_client):
        response = await test_client.post(
            "/context/query",
            json={"question": "Who are our current tenants?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "confidence" in data

    async def test_query_context_validates_min_length(self, test_client):
        response = await test_client.post(
            "/context/query",
            json={"question": "hi"},
        )
        assert response.status_code == 422

    async def test_get_entity_not_found(self, test_client):
        response = await test_client.get("/context/entity/nonexistent-entity-xyz")
        assert response.status_code == 404

    async def test_get_icp_returns_200(self, test_client):
        response = await test_client.get("/context/icp")
        assert response.status_code == 200
        data = response.json()
        assert "based_on_decisions" in data
        assert "confidence" in data

    async def test_get_pricing_returns_200(self, test_client):
        response = await test_client.post(
            "/context/pricing",
            json={"seats": 50, "location": "Gurugram"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommended_range" in data
        assert "confidence" in data

    async def test_relationship_map_not_found(self, test_client):
        response = await test_client.get("/context/relationships/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_relationship_map_depth_too_large(self, test_client):
        response = await test_client.get("/context/relationships/some-id?depth=5")
        assert response.status_code == 400

    async def test_quality_check_returns_200(self, test_client):
        response = await test_client.get("/context/quality")
        assert response.status_code == 200
        data = response.json()
        assert "overall_health_score" in data
        assert "issues" in data


@pytest.mark.asyncio
class TestDecisionEndpoints:
    async def test_capture_decision_returns_201(self, test_client):
        response = await test_client.post(
            "/context/decisions",
            json={
                "decision_type": "lead_approval",
                "actor": "admin",
                "context_snapshot": {
                    "company": "Acme Corp",
                    "industry": "fintech",
                    "seats": 100,
                    "location": "Gurugram",
                },
                "human_action": "Approved — strong ICP fit",
                "human_reasoning": "Recently funded BFSI company expanding NCR team",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["decision_type"] == "lead_approval"

    async def test_record_outcome_updates_decision(self, test_client):
        # First create a decision
        create_response = await test_client.post(
            "/context/decisions",
            json={
                "decision_type": "deal_closure",
                "actor": "admin",
                "context_snapshot": {"client": "TestCo", "value": 500000},
                "human_action": "Deal closed at $12,000/unit/month",
            },
        )
        assert create_response.status_code == 201
        decision_id = create_response.json()["id"]

        # Record the outcome
        outcome_response = await test_client.patch(
            f"/context/decisions/{decision_id}/outcome",
            json={
                "outcome": "deal_closed",
                "outcome_notes": "Client onboarded successfully",
                "feedback_signal": "positive",
            },
        )
        assert outcome_response.status_code == 200
        data = outcome_response.json()
        assert data["outcome"] == "deal_closed"
        assert data["feedback_signal"] == "positive"
