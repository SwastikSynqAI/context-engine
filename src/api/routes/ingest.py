"""
Manual ingestion triggers — connectors only run when a human calls them.
No background scheduling. No auto-pull. You decide when to sync.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.database import get_db
from src.ingestion.base import IngestionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

VALID_SOURCES = {"sheets", "gmail", "hubspot", "documents"}


@router.post("/{source}", status_code=202)
async def trigger_ingestion(
    source: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Manually trigger an ingestion pull from a connected source.
    Runs in the background — returns immediately with a job acknowledgement.

    Sources: sheets | gmail | hubspot | documents
    """
    if source not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{source}'. Valid sources: {', '.join(sorted(VALID_SOURCES))}",
        )

    background_tasks.add_task(_run_ingestion, source, settings)
    return {
        "status": "accepted",
        "source": source,
        "message": f"Ingestion from '{source}' started. Check /health for entity count changes.",
    }


@router.post("/{source}/sync", status_code=200)
async def trigger_ingestion_sync(
    source: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Synchronous version — waits for ingestion to complete before responding.
    Use for small sources or when you need the result immediately.
    """
    if source not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{source}'. Valid sources: {', '.join(sorted(VALID_SOURCES))}",
        )

    result = await _run_ingestion_with_session(source, settings)
    return {
        "source": result.source,
        "entities_created": result.entities_created,
        "entities_updated": result.entities_updated,
        "relationships_created": result.relationships_created,
        "errors": result.errors,
        "success": result.success,
    }


async def _run_ingestion(source: str, settings: Settings) -> None:
    """Background task — creates its own session."""
    from src.database import async_session_factory
    async with async_session_factory() as db:
        try:
            result = await _run_ingestion_with_session(source, settings, db=db)
            await db.commit()
            logger.info("Manual ingestion complete: %s", result)
        except Exception as exc:
            await db.rollback()
            logger.error("Manual ingestion failed for %s: %s", source, exc)


async def _run_ingestion_with_session(
    source: str,
    settings: Settings,
    db: AsyncSession | None = None,
) -> IngestionResult:
    from src.database import async_session_factory

    if db is None:
        # Caller manages session externally
        raise ValueError("db session required")

    if source == "sheets":
        from src.ingestion.sheets import SheetsIngester
        ingester = SheetsIngester(settings, db)
    elif source == "gmail":
        from src.ingestion.gmail import GmailIngester
        ingester = GmailIngester(settings, db)
    elif source == "hubspot":
        from src.ingestion.hubspot import HubSpotIngester
        ingester = HubSpotIngester(settings, db)
    elif source == "documents":
        from src.ingestion.documents import DocumentIngester
        ingester = DocumentIngester(settings, db)
    else:
        raise ValueError(f"Unknown source: {source}")

    return await ingester.ingest()
