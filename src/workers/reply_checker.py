"""
Reply checker — polls IMAP inbox for candidate pre-screen replies.

Runs every 10 minutes. For each active screen session:
1. Fetch emails from candidate_email in last 48h via IMAPService
2. Match emails to the session (any email from that address counts)
3. Record response in hr_screen_responses
4. Use ResponseCollector to decide next action
5. Dispatch next question, probe, or completion email

Probe logic: if answer < 15 words and no probe used → send probe, don't advance index.
Completion: after all 5 answers → mark session completed, trigger screen scorer.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from src.database import async_session_factory
from src.engines.hr.screening.response_collector import ResponseCollector

logger = logging.getLogger(__name__)

_collector = ResponseCollector()


async def check_candidate_replies() -> None:
    """Poll IMAP and process any pending pre-screen replies."""
    from src.services.imap_service import make_imap_service
    imap = make_imap_service()
    if imap is None:
        logger.debug("IMAP not configured — skipping reply check")
        return

    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "SELECT ss.id, ss.application_id, ss.candidate_entity_id, "
                "ss.conversation_state, "
                "e.attributes->>'name' AS name, e.attributes->>'email' AS email, "
                "a.role_type "
                "FROM hr_screen_sessions ss "
                "JOIN hr_applications a ON a.id = ss.application_id "
                "JOIN entities e ON e.id = ss.candidate_entity_id "
                "WHERE ss.completed_at IS NULL "
                "AND ss.timed_out_at IS NULL "
                "AND a.stage = 'pre_screening' "
                "LIMIT 50"
            )
        )
        sessions = result.fetchall()

    if not sessions:
        return

    logger.info("Reply checker: processing %d active screen sessions", len(sessions))

    for session in sessions:
        try:
            await _process_session(session=session, imap=imap)
        except Exception as exc:
            logger.error("Reply checker failed for session %s: %s", session.id, exc)


async def _process_session(*, session, imap) -> None:
    state = session.conversation_state or {}
    current_index = state.get("current_question_index", 0)
    completed = state.get("completed", False)

    if completed:
        return

    replies = imap.fetch_candidate_replies(candidate_email=session.email, since_hours=48)
    if not replies:
        return

    latest_reply = replies[-1]
    reply_text = latest_reply["body"].strip()

    if not reply_text or len(reply_text) < 3:
        return

    # Dedup: check if we already recorded this reply text
    async with async_session_factory() as db:
        check = await db.execute(
            text(
                "SELECT id FROM hr_screen_responses "
                "WHERE session_id = :sid AND response_text = :txt "
                "LIMIT 1"
            ),
            {"sid": str(session.id), "txt": reply_text[:500]},
        )
        if check.fetchone():
            return

    # Record the response
    async with async_session_factory() as db:
        await db.execute(
            text(
                "INSERT INTO hr_screen_responses "
                "(id, session_id, question_index, question_text, response_text, received_at) "
                "VALUES (:id, :session_id, :q_idx, :q_text, :resp, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "session_id": str(session.id),
                "q_idx": current_index,
                "q_text": f"Question {current_index + 1}",
                "resp": reply_text[:2000],
                "now": datetime.now(UTC),
            },
        )
        await db.commit()

    action_result = _collector.process_reply(
        reply_text=reply_text,
        session_state=state,
        question_index=current_index,
    )
    action = action_result["action"]
    updated_state = action_result["updated_state"]

    async with async_session_factory() as db:
        await db.execute(
            text(
                "UPDATE hr_screen_sessions SET conversation_state = CAST(:state AS jsonb) "
                "WHERE id = :id"
            ),
            {"state": json.dumps(updated_state), "id": str(session.id)},
        )
        await db.commit()

    from src.engines.hr.screening.dispatcher import make_dispatcher
    dispatcher = make_dispatcher()

    if action == "send_probe":
        await dispatcher.send_question(
            candidate_email=session.email,
            candidate_name=session.name,
            role=session.role_type,
            question_index=current_index,
            is_probe=True,
        )
        logger.info("Probe sent to %s for Q%d", session.email, current_index + 1)

    elif action == "send_next_question":
        next_index = updated_state["current_question_index"]
        await dispatcher.send_question(
            candidate_email=session.email,
            candidate_name=session.name,
            role=session.role_type,
            question_index=next_index,
            is_probe=False,
        )
        logger.info("Q%d sent to %s", next_index + 1, session.email)

    elif action == "complete_screening":
        await _complete_screening(session=session, updated_state=updated_state, dispatcher=dispatcher)


async def _complete_screening(*, session, updated_state: dict, dispatcher) -> None:
    """Mark session complete, send completion email, trigger screen scorer."""
    now = datetime.now(UTC)

    async with async_session_factory() as db:
        await db.execute(
            text(
                "UPDATE hr_screen_sessions SET "
                "completed_at = :now, conversation_state = CAST(:state AS jsonb) "
                "WHERE id = :id"
            ),
            {"now": now, "state": json.dumps(updated_state), "id": str(session.id)},
        )
        await db.execute(
            text("UPDATE hr_applications SET stage = 'pre_screened', updated_at = :now WHERE id = :app_id"),
            {"now": now, "app_id": str(session.application_id)},
        )
        await db.commit()

    await dispatcher.send_completion(
        candidate_email=session.email,
        candidate_name=session.name,
    )

    await _score_screen_session(session_id=str(session.id), role=session.role_type)
    logger.info("Pre-screen complete for %s — session %s", session.email, session.id)


async def _score_screen_session(*, session_id: str, role: str) -> None:
    """Score all Q&A pairs for a completed session, write screen_score to application."""
    try:
        async with async_session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT question_index, question_text, response_text "
                    "FROM hr_screen_responses WHERE session_id = :sid "
                    "AND is_probe_response = false "
                    "ORDER BY question_index"
                ),
                {"sid": session_id},
            )
            responses = result.fetchall()

        if len(responses) < 5:
            logger.warning("Session %s has only %d responses — skipping screen score", session_id, len(responses))
            return

        qa_pairs = [
            {"question": r.question_text, "answer": r.response_text}
            for r in responses[:5]
        ]

        from src.engines.hr.screening.screen_scorer import make_screen_scorer
        scorer = make_screen_scorer()
        screen_score = await scorer.score(role=role, qa_pairs=qa_pairs)

        async with async_session_factory() as db:
            import json
            result = await db.execute(
                text("SELECT application_id FROM hr_screen_sessions WHERE id = :sid"),
                {"sid": session_id},
            )
            row = result.fetchone()
            if not row:
                return
            await db.execute(
                text(
                    "UPDATE hr_applications SET "
                    "screen_score = :score, "
                    "screen_score_data = CAST(:data AS jsonb), "
                    "updated_at = :now "
                    "WHERE id = :app_id"
                ),
                {
                    "score": screen_score.overall,
                    "data": json.dumps(screen_score.model_dump()),
                    "now": datetime.now(UTC),
                    "app_id": str(row.application_id),
                },
            )
            await db.commit()

        logger.info("Screen score written for session %s: %.1f", session_id, screen_score.overall)
    except Exception as exc:
        logger.error("Screen scoring failed for session %s: %s", session_id, exc)
