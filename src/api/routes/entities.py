"""
Entity and Relationship CRUD — the primary data entry path.

Since all data enters through human action, these endpoints are the main way
to build the knowledge graph. Every create/update goes through here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.graph.embedder import Embedder
from src.graph.entity_store import EntityStore
from src.models.entities import Entity, Relationship
from src.models.enums import DataSource, EntityType, RelationshipType
from src.models.schemas import (
    EntityCreate,
    EntityRead,
    EntityUpdate,
    RelationshipCreate,
    RelationshipRead,
)
from src.config import get_settings, Settings

router = APIRouter(prefix="/entities", tags=["entities"])


# ── Entities ──────────────────────────────────────────────────────────────────

@router.post("", response_model=EntityRead, status_code=201)
async def create_entity(
    body: EntityCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EntityRead:
    """
    Add an entity to the knowledge graph.
    If an entity with the same source + source_id already exists, it is updated.
    """
    store = EntityStore(db)
    entity, created = await store.upsert_entity(
        type=body.type,
        name=body.name,
        source=body.source,
        source_id=body.source_id,
        attributes=body.attributes,
        confidence=body.confidence,
        pii_fields=body.pii_fields,
    )

    # Generate embedding immediately so the entity is queryable right away
    try:
        embedder = Embedder(settings, db)
        await embedder.embed_entity(entity)
    except Exception:
        pass  # Embedding failure does not block entity creation

    return EntityRead.model_validate(entity)


@router.post("/bulk", response_model=list[EntityRead], status_code=201)
async def bulk_create_entities(
    body: list[EntityCreate],
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[EntityRead]:
    """
    Add or update multiple entities in one call.
    Useful when pasting a list from a spreadsheet or importing a set of records.
    Returns the upserted entities in the same order.
    """
    if len(body) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 entities per bulk call")

    store = EntityStore(db)
    embedder = Embedder(settings, db)
    results = []

    for item in body:
        entity, _ = await store.upsert_entity(
            type=item.type,
            name=item.name,
            source=item.source,
            source_id=item.source_id,
            attributes=item.attributes,
            confidence=item.confidence,
            pii_fields=item.pii_fields,
        )
        results.append(entity)

    # Embed all at once
    try:
        await embedder.embed_entities_bulk(results)
    except Exception:
        pass

    return [EntityRead.model_validate(e) for e in results]


@router.get("", response_model=list[EntityRead])
async def list_entities(
    type: EntityType | None = Query(default=None, description="Filter by entity type"),
    search: str | None = Query(default=None, description="Fuzzy name search"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[EntityRead]:
    """List entities, optionally filtered by type or searched by name."""
    store = EntityStore(db)

    if search:
        entities = await store.search_entities_by_name(search, type=type)
        return [EntityRead.model_validate(e) for e in entities[offset:offset + limit]]

    if type:
        entities = await store.get_entities_by_type(type)
        return [EntityRead.model_validate(e) for e in entities[offset:offset + limit]]

    # No filter — return paginated list ordered by updated_at desc
    from sqlalchemy import desc
    result = await db.execute(
        select(Entity)
        .where(Entity.is_active == True)
        .order_by(desc(Entity.updated_at))
        .offset(offset)
        .limit(limit)
    )
    return [EntityRead.model_validate(e) for e in result.scalars().all()]


@router.get("/{entity_id}", response_model=EntityRead)
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db)) -> EntityRead:
    store = EntityStore(db)
    entity = await store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
    return EntityRead.model_validate(entity)


@router.patch("/{entity_id}", response_model=EntityRead)
async def update_entity(
    entity_id: str,
    body: EntityUpdate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EntityRead:
    """Update an entity's name, attributes, confidence, or active status."""
    store = EntityStore(db)
    entity = await store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    if body.name is not None:
        entity.name = body.name
    if body.attributes is not None:
        entity.attributes = {**entity.attributes, **body.attributes}
    if body.confidence is not None:
        entity.confidence = body.confidence
    if body.is_active is not None:
        entity.is_active = body.is_active

    await db.flush()

    # Re-embed after update
    try:
        embedder = Embedder(settings, db)
        await embedder.embed_entity(entity)
    except Exception:
        pass

    return EntityRead.model_validate(entity)


@router.delete("/{entity_id}")
async def deactivate_entity(entity_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Soft-delete an entity (sets is_active=False). Does not remove from the DB."""
    store = EntityStore(db)
    entity = await store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
    entity.is_active = False
    await db.flush()
    return Response(status_code=204)


# ── Relationships ─────────────────────────────────────────────────────────────

@router.post("/{entity_id}/relationships", response_model=RelationshipRead, status_code=201)
async def create_relationship(
    entity_id: str,
    body: RelationshipCreate,
    db: AsyncSession = Depends(get_db),
) -> RelationshipRead:
    """
    Create a relationship FROM this entity to another.
    body.from_entity_id must match entity_id (or be omitted — it will be set automatically).
    """
    store = EntityStore(db)

    # Verify both entities exist
    from_entity = await store.get_entity_by_id(entity_id)
    if not from_entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    to_entity = await store.get_entity_by_id(body.to_entity_id)
    if not to_entity:
        raise HTTPException(status_code=404, detail=f"Target entity '{body.to_entity_id}' not found")

    rel, _ = await store.upsert_relationship(
        from_entity_id=entity_id,
        to_entity_id=body.to_entity_id,
        relationship_type=body.relationship_type,
        source=body.source,
        metadata=body.metadata,
        confidence=body.confidence,
    )
    return RelationshipRead.model_validate(rel)


@router.get("/{entity_id}/relationships", response_model=list[RelationshipRead])
async def list_relationships(
    entity_id: str,
    direction: str = Query(default="both", description="outgoing | incoming | both"),
    db: AsyncSession = Depends(get_db),
) -> list[RelationshipRead]:
    store = EntityStore(db)
    entity = await store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    if direction not in ("outgoing", "incoming", "both"):
        raise HTTPException(status_code=400, detail="direction must be outgoing | incoming | both")

    rels = await store.get_relationships(entity_id, direction=direction)
    return [RelationshipRead.model_validate(r) for r in rels]


@router.delete("/relationships/{relationship_id}")
async def deactivate_relationship(
    relationship_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Soft-delete a relationship."""
    result = await db.execute(
        select(Relationship).where(Relationship.id == relationship_id)
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail=f"Relationship '{relationship_id}' not found")
    rel.is_active = False
    await db.flush()
    return Response(status_code=204)
