from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.graph.entity_store import EntityStore
from src.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    store = EntityStore(db)
    try:
        entity_count = await store.count_entities()
        rel_count = await store.count_relationships()
        db_connected = True
    except Exception:
        entity_count = 0
        rel_count = 0
        db_connected = False

    return HealthResponse(
        status="ok" if db_connected else "degraded",
        db_connected=db_connected,
        entity_count=entity_count,
        relationship_count=rel_count,
        last_ingestion=None,  # TODO: track via a metadata table in v2
    )
