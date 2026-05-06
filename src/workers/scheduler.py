"""
APScheduler setup for AI Hire background workers.

Jobs:
- resume_worker: every 5 minutes
- reply_checker: every 10 minutes
- stage_advancement: every 15 minutes
- reminder_worker: every 6 hours

Returns an AsyncIOScheduler — started/stopped by FastAPI lifespan.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance (not started yet)."""
    from src.workers.reminder_worker import send_reminders
    from src.workers.reply_checker import check_candidate_replies
    from src.workers.resume_worker import score_pending_resumes
    from src.workers.stage_advancement import advance_stages

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        score_pending_resumes,
        trigger="interval",
        minutes=5,
        id="resume_worker",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        check_candidate_replies,
        trigger="interval",
        minutes=10,
        id="reply_checker",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        advance_stages,
        trigger="interval",
        minutes=15,
        id="stage_advancement",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        send_reminders,
        trigger="interval",
        hours=6,
        id="reminder_worker",
        replace_existing=True,
        max_instances=1,
    )

    return scheduler
