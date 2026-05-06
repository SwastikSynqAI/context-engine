"""
Stage advancement worker — automatically moves candidates who meet thresholds.

Runs every 15 minutes. Checks:
- pre_screened + screen_score >= threshold → invite to test
- test_completed + passed → advance to 'screened', notify shortlister

Does NOT auto-send interview invites — Admin must approve via dashboard (Gate 1).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import text

from src.database import async_session_factory

logger = logging.getLogger(__name__)


async def advance_stages() -> None:
    """Auto-advance candidates past automated gates."""
    from src.config import get_settings
    settings = get_settings()

    await _advance_prescreened_to_test_invited(settings=settings)
    await _check_shortlist_gate(settings=settings)


async def _advance_prescreened_to_test_invited(*, settings) -> None:
    """Candidates who passed pre-screen → invite to test."""
    threshold = settings.hr_screen_score_threshold

    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "SELECT a.id, a.role_type, "
                "e.attributes->>'name' AS name, e.attributes->>'email' AS email "
                "FROM hr_applications a "
                "JOIN entities e ON e.id = a.candidate_entity_id "
                "WHERE a.stage = 'pre_screened' "
                "AND a.screen_score >= :threshold "
                "LIMIT 20"
            ),
            {"threshold": threshold},
        )
        rows = result.fetchall()

    for row in rows:
        try:
            await _invite_to_test(application_id=str(row.id), candidate_email=row.email,
                                  candidate_name=row.name, role=row.role_type, settings=settings)
        except Exception as exc:
            logger.error("Test invite failed for app %s: %s", row.id, exc)


async def _invite_to_test(*, application_id: str, candidate_email: str,
                           candidate_name: str, role: str, settings) -> None:
    """Create test session and send invite email."""
    import json
    import uuid

    from src.services.test_engine import generate_test_token, make_test_engine

    token = generate_test_token()
    session_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    async with async_session_factory() as db:
        await db.execute(
            text(
                "INSERT INTO hr_test_sessions "
                "(id, application_id, candidate_entity_id, token, status, questions, created_at) "
                "SELECT :id, :app_id, candidate_entity_id, :token, 'pending', '{}'::jsonb, :now "
                "FROM hr_applications WHERE id = :app_id "
                "ON CONFLICT (application_id) DO NOTHING"
            ),
            {"id": session_id, "app_id": application_id, "token": token, "now": now},
        )
        await db.execute(
            text("UPDATE hr_applications SET stage = 'test_invited', updated_at = :now WHERE id = :app_id"),
            {"now": now, "app_id": application_id},
        )
        await db.commit()

    engine = make_test_engine()
    questions = await engine.generate_questions(role=role, ai_required=False)

    async with async_session_factory() as db:
        await db.execute(
            text("UPDATE hr_test_sessions SET questions = CAST(:q AS jsonb) WHERE id = :id"),
            {"q": json.dumps(questions), "id": session_id},
        )
        await db.commit()

    from src.engines.hr.inbound.acknowledger import send_email_smtp
    test_url = f"{settings.frontend_url}/test/{token}"
    smtp_config = {
        "host": settings.smtp_host, "port": settings.smtp_port,
        "username": settings.smtp_username, "password": settings.smtp_password,
        "from_email": settings.hiring_email,
    }
    first_name = candidate_name.split()[0]
    body = (
        f"Hi {first_name},\n\n"
        f"Great news! You've passed the pre-screening stage. "
        f"Please complete a short online assessment within 48 hours:\n\n"
        f"{test_url}\n\n"
        f"The test covers Aptitude and English (approx. 30 min).\n\n"
        f"Best,\nHiring Team\nhiring@example.com"
    )
    await send_email_smtp(
        to_email=candidate_email,
        subject="YourCompany — You're invited to the online assessment",
        body=body,
        smtp_config=smtp_config,
    )
    logger.info("Test invite sent to %s for app %s", candidate_email, application_id)


async def _check_shortlist_gate(*, settings) -> None:
    """After 3+ candidates reach 'screened' → email shortlist to Admin."""
    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "SELECT a.id AS application_id, a.role_type, a.resume_score, a.screen_score, "
                "e.attributes->>'name' AS name, e.attributes->>'email' AS email "
                "FROM hr_applications a "
                "JOIN entities e ON e.id = a.candidate_entity_id "
                "WHERE a.stage = 'screened' "
                "AND a.rejection_reason IS NULL "
                "ORDER BY a.updated_at DESC "
                "LIMIT 20"
            )
        )
        rows = result.fetchall()

    if len(rows) < 3:
        return

    candidates = [
        {
            "application_id": str(r.application_id),
            "name": r.name,
            "email": r.email,
            "role": r.role_type,
            "resume_score": r.resume_score or 0,
            "screen_score": r.screen_score or 0,
        }
        for r in rows
    ]

    try:
        from src.engines.hr.ranking.shortlister import build_shortlist, make_shortlister
        ranked = build_shortlist(candidates=candidates, top_n=5)
        shortlister = make_shortlister()
        role = candidates[0]["role"]
        await shortlister.send_shortlist(candidates=ranked, role=role)
        logger.info("Shortlist email sent to Admin: %d candidates for %s", len(ranked), role)
    except Exception as exc:
        logger.error("Shortlist gate failed: %s", exc)
