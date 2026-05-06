"""
APScheduler setup — runs each ingester on its configured cron schedule.

The scheduler is started on FastAPI startup and shut down on app shutdown.
Each job runs in its own async DB session so it doesn't interfere with the API.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import Settings

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def _run_sheets(settings: Settings) -> None:
    from src.database import async_session_factory
    from src.ingestion.sheets import SheetsIngester
    async with async_session_factory() as db:
        try:
            ingester = SheetsIngester(settings, db)
            result = await ingester.ingest()
            await db.commit()
            logger.info("Sheets ingestion: %s", result)
        except Exception as exc:
            await db.rollback()
            logger.error("Sheets ingestion failed: %s", exc)


async def _run_gmail(settings: Settings) -> None:
    from src.database import async_session_factory
    from src.ingestion.gmail import GmailIngester
    async with async_session_factory() as db:
        try:
            ingester = GmailIngester(settings, db)
            result = await ingester.ingest()
            await db.commit()
            logger.info("Gmail ingestion: %s", result)
        except Exception as exc:
            await db.rollback()
            logger.error("Gmail ingestion failed: %s", exc)


async def _run_hubspot(settings: Settings) -> None:
    from src.database import async_session_factory
    from src.ingestion.hubspot import HubSpotIngester
    async with async_session_factory() as db:
        try:
            ingester = HubSpotIngester(settings, db)
            result = await ingester.ingest()
            await db.commit()
            logger.info("HubSpot ingestion: %s", result)
        except Exception as exc:
            await db.rollback()
            logger.error("HubSpot ingestion failed: %s", exc)


async def _run_documents(settings: Settings) -> None:
    from src.database import async_session_factory
    from src.ingestion.documents import DocumentIngester
    async with async_session_factory() as db:
        try:
            ingester = DocumentIngester(settings, db)
            result = await ingester.ingest()
            await db.commit()
            logger.info("Document ingestion: %s", result)
        except Exception as exc:
            await db.rollback()
            logger.error("Document ingestion failed: %s", exc)


async def _run_evaluator(settings: Settings) -> None:
    from src.database import async_session_factory
    from src.reasoning.evaluator import SelfImprovementEvaluator
    async with async_session_factory() as db:
        try:
            evaluator = SelfImprovementEvaluator(settings, db)
            result = await evaluator.run()
            await db.commit()
            logger.info("Evaluator run: %s", result)
        except Exception as exc:
            await db.rollback()
            logger.error("Evaluator failed: %s", exc)


def _parse_cron(cron_str: str) -> CronTrigger:
    """Parse a 5-field cron string into an APScheduler CronTrigger."""
    parts = cron_str.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron string: {cron_str!r}")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
    )


async def start_scheduler(settings: Settings) -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler()

    jobs = [
        ("sheets", _run_sheets, settings.schedule_sheets),
        ("gmail", _run_gmail, settings.schedule_gmail),
        ("hubspot", _run_hubspot, settings.schedule_hubspot),
        ("documents", _run_documents, settings.schedule_documents),
        ("evaluator", _run_evaluator, settings.schedule_evaluator),
    ]

    for job_id, func, cron_str in jobs:
        try:
            trigger = _parse_cron(cron_str)
            _scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                args=[settings],
                replace_existing=True,
                max_instances=1,  # Prevent overlapping runs
                coalesce=True,
            )
            logger.info("Scheduled %s: %s", job_id, cron_str)
        except Exception as exc:
            logger.error("Failed to schedule %s: %s", job_id, exc)

    _scheduler.start()
    logger.info("Ingestion scheduler started with %d jobs", len(_scheduler.get_jobs()))


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Ingestion scheduler stopped")
