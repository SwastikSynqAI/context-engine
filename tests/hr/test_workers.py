"""Unit tests for background workers — DB is mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Resume worker ────────────────────────────────────────────────────────────

def test_resume_worker_imports():
    from src.workers.resume_worker import score_pending_resumes
    assert callable(score_pending_resumes)


@pytest.mark.asyncio
async def test_score_pending_resumes_skips_empty():
    """If no pending applications, worker completes without error."""
    from src.workers.resume_worker import score_pending_resumes
    with patch("src.workers.resume_worker.async_session_factory") as mock_factory:
        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)
        await score_pending_resumes()


# ── Reply checker ────────────────────────────────────────────────────────────

def test_reply_checker_imports():
    from src.workers.reply_checker import check_candidate_replies
    assert callable(check_candidate_replies)


# ── Stage advancement ────────────────────────────────────────────────────────

def test_stage_advancement_imports():
    from src.workers.stage_advancement import advance_stages
    assert callable(advance_stages)


# ── Reminder worker ──────────────────────────────────────────────────────────

def test_reminder_worker_imports():
    from src.workers.reminder_worker import send_reminders
    assert callable(send_reminders)


# ── Scheduler ────────────────────────────────────────────────────────────────

def test_scheduler_imports():
    from src.workers.scheduler import create_scheduler
    assert callable(create_scheduler)
