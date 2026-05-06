"""
EntityStore — all CRUD for entities and relationships.

Design: upsert_entity uses (source, source_id) as the natural key so re-running
ingesters is idempotent. Confidence is preserved unless explicitly overridden.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Entity, Relationship
from src.models.enums import DataSource, EntityType, RelationshipType


class EntityStore:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Entities ──────────────────────────────────────────────────────────────

    async def upsert_entity(
        self,
        *,
        type: EntityType,
        name: str,
        source: DataSource,
        source_id: str | None = None,
        attributes: dict[str, Any] | None = None,
        confidence: float = 1.0,
        pii_fields: list[str] | None = None,
    ) -> tuple[Entity, bool]:
        """
        Insert or update an entity. Returns (entity, created: bool).
        When source_id is None a new UUID is generated and the record is always inserted.
        """
        if source_id is None:
            # No natural key — always insert
            entity = Entity(
                id=str(uuid.uuid4()),
                type=type,
                name=name,
                attributes=attributes or {},
                source=source,
                source_id=None,
                confidence=confidence,
                pii_fields=pii_fields or [],
            )
            self.db.add(entity)
            await self.db.flush()
            return entity, True

        # Try to find existing record
        result = await self.db.execute(
            select(Entity).where(
                Entity.source == source,
                Entity.source_id == source_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            entity = Entity(
                id=str(uuid.uuid4()),
                type=type,
                name=name,
                attributes=attributes or {},
                source=source,
                source_id=source_id,
                confidence=confidence,
                pii_fields=pii_fields or [],
            )
            self.db.add(entity)
            await self.db.flush()
            return entity, True
        else:
            # Update mutable fields; preserve id and confidence unless explicitly changed
            existing.name = name
            existing.type = type
            if attributes is not None:
                # Merge attributes — new values win, existing keys not in new dict are preserved
                merged = {**existing.attributes, **attributes}
                existing.attributes = merged
            if pii_fields is not None:
                existing.pii_fields = list(set(existing.pii_fields + pii_fields))
            existing.confidence = confidence
            existing.updated_at = datetime.now(UTC)
            await self.db.flush()
            return existing, False

    async def get_entity_by_id(self, entity_id: str) -> Entity | None:
        result = await self.db.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_entity_by_source(self, source: str, source_id: str) -> Entity | None:
        result = await self.db.execute(
            select(Entity).where(
                Entity.source == source,
                Entity.source_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    async def search_entities_by_name(self, name: str, type: EntityType | None = None) -> list[Entity]:
        """Trigram-based fuzzy name search."""
        query = select(Entity).where(Entity.is_active == True)
        if type:
            query = query.where(Entity.type == type)
        # Postgres trigram similarity — results ordered by match quality
        query = query.where(
            Entity.name.op("%%")(name)  # %% is the escaped trigram operator
        ).order_by(
            Entity.name.op("<->")(name)  # distance ascending = most similar first
        ).limit(20)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_entities_by_type(self, type: EntityType) -> list[Entity]:
        result = await self.db.execute(
            select(Entity).where(Entity.type == type, Entity.is_active == True)
        )
        return list(result.scalars().all())

    async def count_entities(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(Entity).where(Entity.is_active == True)
        )
        return result.scalar_one()

    # ── Relationships ─────────────────────────────────────────────────────────

    async def upsert_relationship(
        self,
        *,
        from_entity_id: str,
        to_entity_id: str,
        relationship_type: RelationshipType,
        source: DataSource,
        metadata: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> tuple[Relationship, bool]:
        """Insert or update a relationship. Returns (relationship, created: bool)."""
        result = await self.db.execute(
            select(Relationship).where(
                Relationship.from_entity_id == from_entity_id,
                Relationship.to_entity_id == to_entity_id,
                Relationship.relationship_type == relationship_type,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            rel = Relationship(
                id=str(uuid.uuid4()),
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                relationship_type=relationship_type,
                rel_metadata=metadata or {},
                confidence=confidence,
                source=source,
            )
            self.db.add(rel)
            await self.db.flush()
            return rel, True
        else:
            if metadata:
                existing.rel_metadata = {**existing.rel_metadata, **metadata}
            existing.confidence = confidence
            existing.updated_at = datetime.now(UTC)
            await self.db.flush()
            return existing, False

    async def get_relationships(
        self,
        entity_id: str,
        direction: str = "both",  # "outgoing" | "incoming" | "both"
        rel_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        conditions = []
        if direction in ("outgoing", "both"):
            conditions.append(Relationship.from_entity_id == entity_id)
        if direction in ("incoming", "both"):
            conditions.append(Relationship.to_entity_id == entity_id)

        from sqlalchemy import or_
        query = select(Relationship).where(
            or_(*conditions),
            Relationship.is_active == True,
        )
        if rel_type:
            query = query.where(Relationship.relationship_type == rel_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_relationships(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(Relationship).where(Relationship.is_active == True)
        )
        return result.scalar_one()
