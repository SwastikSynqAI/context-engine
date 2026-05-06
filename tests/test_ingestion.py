"""
Tests for the ingestion pipeline.
Uses an in-memory SQLite-compatible approach via mocking — no live DB required.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ingestion.base import IngestionResult
from src.models.enums import DataSource, EntityType


class TestIngestionResult:
    def test_success_when_no_errors(self):
        result = IngestionResult(source="test")
        assert result.success is True

    def test_failure_when_errors(self):
        result = IngestionResult(source="test")
        result.add_error("something broke")
        assert result.success is False
        assert len(result.errors) == 1

    def test_finish_sets_timestamp(self):
        result = IngestionResult(source="test")
        assert result.finished_at is None
        result.finish()
        assert result.finished_at is not None

    def test_str_representation(self):
        result = IngestionResult(source="sheets")
        result.entities_created = 5
        result.entities_updated = 2
        result.relationships_created = 3
        result.finish()
        s = str(result)
        assert "sheets" in s
        assert "+5" in s


class TestSheetsFieldNormalisation:
    def test_normalise_row_maps_canonical_fields(self):
        from src.ingestion.sheets import TENANT_FIELD_MAP, _normalise_row

        headers = ["Company Name", "Email", "Seats", "Building"]
        row = ["Acme Corp", "acme@example.com", "50", "Metro Business District"]
        result = _normalise_row(headers, row, TENANT_FIELD_MAP)

        assert result["company_name"] == "Acme Corp"
        assert result["email"] == "acme@example.com"
        assert result["seats"] == "50"
        assert result["building"] == "Metro Business District"

    def test_normalise_row_case_insensitive(self):
        from src.ingestion.sheets import TENANT_FIELD_MAP, _normalise_row

        headers = ["COMPANY NAME", "EMAIL"]
        row = ["Test Co", "test@test.com"]
        result = _normalise_row(headers, row, TENANT_FIELD_MAP)
        assert result["company_name"] == "Test Co"

    def test_normalise_row_empty_values_not_included(self):
        from src.ingestion.sheets import TENANT_FIELD_MAP, _normalise_row

        headers = ["Company Name", "Email"]
        row = ["Acme", ""]
        result = _normalise_row(headers, row, TENANT_FIELD_MAP)
        assert "company_name" in result
        assert "email" not in result  # empty string skipped


@pytest.mark.asyncio
class TestEntityStore:
    async def test_upsert_creates_new_entity(self, db_session):
        from src.graph.entity_store import EntityStore

        store = EntityStore(db_session)
        entity, created = await store.upsert_entity(
            type=EntityType.CLIENT,
            name="Test Corp",
            source=DataSource.GOOGLE_SHEETS,
            source_id="sheet:test:1",
            attributes={"industry": "tech"},
        )
        assert created is True
        assert entity.name == "Test Corp"
        assert entity.type == EntityType.CLIENT

    async def test_upsert_updates_existing_entity(self, db_session):
        from src.graph.entity_store import EntityStore

        store = EntityStore(db_session)
        # Create
        await store.upsert_entity(
            type=EntityType.CLIENT,
            name="Test Corp",
            source=DataSource.GOOGLE_SHEETS,
            source_id="sheet:test:2",
            attributes={"industry": "tech"},
        )
        # Update
        entity, created = await store.upsert_entity(
            type=EntityType.CLIENT,
            name="Test Corp Updated",
            source=DataSource.GOOGLE_SHEETS,
            source_id="sheet:test:2",
            attributes={"industry": "fintech"},
        )
        assert created is False
        assert entity.name == "Test Corp Updated"
        # Attributes should merge — original key preserved
        assert "industry" in entity.attributes

    async def test_upsert_relationship_idempotent(self, db_session):
        from src.graph.entity_store import EntityStore
        from src.models.enums import RelationshipType

        store = EntityStore(db_session)
        e1, _ = await store.upsert_entity(
            type=EntityType.CLIENT, name="Client A",
            source=DataSource.GOOGLE_SHEETS, source_id="c:1"
        )
        e2, _ = await store.upsert_entity(
            type=EntityType.BUILDING, name="Building X",
            source=DataSource.GOOGLE_SHEETS, source_id="b:1"
        )

        _, c1 = await store.upsert_relationship(
            from_entity_id=e1.id, to_entity_id=e2.id,
            relationship_type=RelationshipType.TENANT_OF,
            source=DataSource.GOOGLE_SHEETS,
        )
        _, c2 = await store.upsert_relationship(
            from_entity_id=e1.id, to_entity_id=e2.id,
            relationship_type=RelationshipType.TENANT_OF,
            source=DataSource.GOOGLE_SHEETS,
        )
        assert c1 is True
        assert c2 is False  # Second call = update, not create
