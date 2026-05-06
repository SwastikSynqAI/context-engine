"""
Resume worker — scores unscored resumes for new applications.

Runs every 5 minutes. Finds applications where:
- resume_text is not null and non-empty
- resume_score is null
- stage in ('applied', 'parsed')

Calls ResumeScorer → writes score back → advances stage to 'parsed'.
If resume_score >= threshold → calls start_prescreen inline.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from src.database import async_session_factory

logger = logging.getLogger(__name__)


async def score_pending_resumes() -> None:
    """Score all unscored resumes. Called by APScheduler."""
    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "SELECT a.id, a.candidate_entity_id, a.role_type, a.resume_text, "
                "e.attributes->>'name' AS name, e.attributes->>'email' AS email, "
                "e.attributes->>'application_answer' AS application_answer "
                "FROM hr_applications a "
                "JOIN entities e ON e.id = a.candidate_entity_id "
                "WHERE a.resume_text IS NOT NULL "
                "AND a.resume_text != '' "
                "AND a.resume_score IS NULL "
                "AND a.stage NOT IN ('rejected') "
                "LIMIT 10"
            )
        )
        rows = result.fetchall()

    if not rows:
        return

    logger.info("Resume worker: %d applications to score", len(rows))

    from src.config import get_settings
    from src.engines.hr.scoring.resume_scorer import make_resume_scorer

    settings = get_settings()
    scorer = make_resume_scorer()

    for row in rows:
        try:
            score = await scorer.score(
                resume_text=row.resume_text,
                application_answer=row.application_answer or "",
                role=row.role_type,
                role_salary_max=1500000,
            )

            async with async_session_factory() as db:
                import json
                from datetime import UTC, datetime
                now = datetime.now(UTC)
                await db.execute(
                    text(
                        "UPDATE hr_applications SET "
                        "resume_score = :score, "
                        "resume_score_data = CAST(:data AS jsonb), "
                        "stage = CASE WHEN stage = 'applied' THEN 'parsed' ELSE stage END, "
                        "updated_at = :now "
                        "WHERE id = :app_id"
                    ),
                    {
                        "score": score.overall,
                        "data": json.dumps(score.model_dump()),
                        "now": now,
                        "app_id": str(row.id),
                    },
                )
                await db.commit()

            logger.info(
                "Scored resume for %s (%s): %.1f",
                row.email, row.role_type, score.overall,
            )

            if score.overall >= settings.hr_resume_score_threshold and not score.auto_reject:
                await _trigger_prescreen(application_id=str(row.id), settings=settings)

        except Exception as exc:
            logger.error("Resume scoring failed for app %s: %s", row.id, exc)


async def _trigger_prescreen(*, application_id: str, settings) -> None:
    """Inline pre-screen trigger — creates screen session and sends Q1."""
    try:
        import json
        import uuid
        from datetime import UTC, datetime

        async with async_session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT a.id, a.candidate_entity_id, a.role_type, "
                    "e.attributes->>'name' AS name, e.attributes->>'email' AS email "
                    "FROM hr_applications a "
                    "JOIN entities e ON e.id = a.candidate_entity_id "
                    "WHERE a.id = :app_id AND a.stage = 'parsed'"
                ),
                {"app_id": application_id},
            )
            row = result.fetchone()
            if not row:
                return

            session_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            initial_state = json.dumps({
                "current_question_index": 0,
                "probe_used": False,
                "last_reply_at": None,
                "reminder_sent": False,
                "completed": False,
                "timed_out": False,
            })
            await db.execute(
                text(
                    "INSERT INTO hr_screen_sessions "
                    "(id, application_id, candidate_entity_id, channel, conversation_state, started_at, created_at) "
                    "VALUES (:id, :app_id, :candidate_id, 'email', CAST(:state AS jsonb), :now, :now) "
                    "ON CONFLICT (application_id) DO NOTHING"
                ),
                {"id": session_id, "app_id": application_id,
                 "candidate_id": str(row.candidate_entity_id), "state": initial_state, "now": now},
            )
            await db.execute(
                text("UPDATE hr_applications SET stage = 'pre_screening', updated_at = :now WHERE id = :app_id"),
                {"now": now, "app_id": application_id},
            )
            await db.commit()

        from src.engines.hr.screening.dispatcher import make_dispatcher
        dispatcher = make_dispatcher()
        await dispatcher.send_question(
            candidate_email=row.email,
            candidate_name=row.name,
            role=row.role_type,
            question_index=0,
            is_probe=False,
        )
        logger.info("Auto pre-screen started for %s", row.email)
    except Exception as exc:
        logger.error("Auto pre-screen trigger failed for app %s: %s", application_id, exc)
