"""
Reminder worker — nudges candidates who haven't replied to pre-screen Q in 48h.

Runs every 6 hours. Finds screen sessions that:
- Are not completed or timed out
- Were started > 48h ago
- Reminder has not been sent yet (conversation_state.reminder_sent = false)

Marks reminder_sent = true to avoid spam. Times out sessions after 7 days.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from src.database import async_session_factory

logger = logging.getLogger(__name__)

REMINDER_AFTER_HOURS = 48
TIMEOUT_AFTER_DAYS = 7


async def send_reminders() -> None:
    """Send reminders and time out stale sessions."""
    await _send_pending_reminders()
    await _timeout_stale_sessions()


async def _send_pending_reminders() -> None:
    cutoff = datetime.now(UTC) - timedelta(hours=REMINDER_AFTER_HOURS)

    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "SELECT ss.id, ss.conversation_state, ss.started_at, "
                "e.attributes->>'name' AS name, e.attributes->>'email' AS email "
                "FROM hr_screen_sessions ss "
                "JOIN hr_applications a ON a.id = ss.application_id "
                "JOIN entities e ON e.id = ss.candidate_entity_id "
                "WHERE ss.completed_at IS NULL "
                "AND ss.timed_out_at IS NULL "
                "AND ss.started_at < :cutoff "
                "AND (ss.conversation_state->>'reminder_sent')::boolean IS NOT TRUE "
                "LIMIT 20"
            ),
            {"cutoff": cutoff},
        )
        sessions = result.fetchall()

    for session in sessions:
        try:
            await _send_reminder(session=session)
        except Exception as exc:
            logger.error("Reminder send failed for session %s: %s", session.id, exc)


async def _send_reminder(*, session) -> None:
    from src.config import get_settings
    from src.engines.hr.inbound.acknowledger import send_email_smtp

    settings = get_settings()
    state = session.conversation_state or {}
    current_index = state.get("current_question_index", 0)
    first_name = session.name.split()[0] if session.name else "there"

    body = (
        f"Hi {first_name},\n\n"
        f"Just a gentle reminder — we're waiting for your reply to Question "
        f"{current_index + 1} of 5 in the YourCompany pre-screening.\n\n"
        f"Please reply to the earlier email at your earliest convenience. "
        f"If you're no longer interested, no action needed.\n\n"
        f"Best,\nHiring Team\nhiring@example.com"
    )
    smtp_config = {
        "host": settings.smtp_host, "port": settings.smtp_port,
        "username": settings.smtp_username, "password": settings.smtp_password,
        "from_email": settings.hiring_email,
    }
    await send_email_smtp(
        to_email=session.email,
        subject="YourCompany — A quick reminder on your pre-screening",
        body=body,
        smtp_config=smtp_config,
    )

    updated_state = {**state, "reminder_sent": True}
    async with async_session_factory() as db:
        await db.execute(
            text("UPDATE hr_screen_sessions SET conversation_state = CAST(:s AS jsonb) WHERE id = :id"),
            {"s": json.dumps(updated_state), "id": str(session.id)},
        )
        await db.commit()

    logger.info("Reminder sent to %s (session %s)", session.email, session.id)


async def _timeout_stale_sessions() -> None:
    timeout_cutoff = datetime.now(UTC) - timedelta(days=TIMEOUT_AFTER_DAYS)
    now = datetime.now(UTC)

    async with async_session_factory() as db:
        await db.execute(
            text(
                "UPDATE hr_screen_sessions SET timed_out_at = :now "
                "WHERE completed_at IS NULL AND timed_out_at IS NULL AND started_at < :cutoff"
            ),
            {"now": now, "cutoff": timeout_cutoff},
        )
        await db.execute(
            text(
                "UPDATE hr_applications SET stage = 'rejected', rejection_reason = 'prescreen_timeout', "
                "updated_at = :now "
                "WHERE id IN ("
                "  SELECT application_id FROM hr_screen_sessions "
                "  WHERE timed_out_at = :now"
                ")"
            ),
            {"now": now},
        )
        await db.commit()
    logger.debug("Stale session timeout check complete")
