"""
RelationshipMapper — infers and creates relationships from entity data.

This module knows YourCompany's specific relationship logic:
- A contact with a company name → look up/create the company entity and link them
- A deal with a client name → link deal to client entity
- A space in a building → link space to building
etc.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.entity_store import EntityStore
from src.models.enums import DataSource, EntityType, RelationshipType

logger = logging.getLogger(__name__)


class RelationshipMapper:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.store = EntityStore(db)

    async def link_contact_to_company(
        self,
        contact_id: str,
        company_name: str,
        source: DataSource,
    ) -> bool:
        """Find (or create) a client entity for company_name and create a contact_at relationship."""
        candidates = await self.store.search_entities_by_name(company_name, type=EntityType.CLIENT)
        if not candidates:
            # Create a placeholder client entity so the relationship can be established
            client, _ = await self.store.upsert_entity(
                type=EntityType.CLIENT,
                name=company_name,
                source=source,
                confidence=0.6,  # lower confidence — inferred, not directly ingested
            )
            company_id = client.id
        else:
            company_id = candidates[0].id

        _, created = await self.store.upsert_relationship(
            from_entity_id=contact_id,
            to_entity_id=company_id,
            relationship_type=RelationshipType.CONTACT_AT,
            source=source,
        )
        return created

    async def link_deal_to_client(
        self,
        deal_id: str,
        client_name: str,
        source: DataSource,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        candidates = await self.store.search_entities_by_name(client_name, type=EntityType.CLIENT)
        if not candidates:
            client, _ = await self.store.upsert_entity(
                type=EntityType.CLIENT,
                name=client_name,
                source=source,
                confidence=0.6,
            )
            client_id = client.id
        else:
            client_id = candidates[0].id

        _, created = await self.store.upsert_relationship(
            from_entity_id=client_id,
            to_entity_id=deal_id,
            relationship_type=RelationshipType.PART_OF_DEAL,
            source=source,
            metadata=metadata or {},
        )
        return created

    async def link_space_to_building(
        self,
        space_id: str,
        building_name: str,
        source: DataSource,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        candidates = await self.store.search_entities_by_name(building_name, type=EntityType.BUILDING)
        if not candidates:
            building, _ = await self.store.upsert_entity(
                type=EntityType.BUILDING,
                name=building_name,
                source=source,
                confidence=0.6,
            )
            building_id = building.id
        else:
            building_id = candidates[0].id

        _, created = await self.store.upsert_relationship(
            from_entity_id=space_id,
            to_entity_id=building_id,
            relationship_type=RelationshipType.LOCATED_IN,
            source=source,
            metadata=metadata or {},
        )
        return created

    async def link_client_to_building(
        self,
        client_id: str,
        building_id: str,
        source: DataSource,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        _, created = await self.store.upsert_relationship(
            from_entity_id=client_id,
            to_entity_id=building_id,
            relationship_type=RelationshipType.TENANT_OF,
            source=source,
            metadata=metadata or {},
        )
        return created

    async def link_broker_to_deal(
        self,
        broker_id: str,
        deal_id: str,
        source: DataSource,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        _, created = await self.store.upsert_relationship(
            from_entity_id=broker_id,
            to_entity_id=deal_id,
            relationship_type=RelationshipType.BROKER_FOR,
            source=source,
            metadata=metadata or {},
        )
        return created
