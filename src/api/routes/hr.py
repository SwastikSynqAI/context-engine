"""
AI Hire — public HR endpoints.

POST /hr/apply  — receives applications from yourcompany.com/careers
GET  /hr/health — engine health check
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.database import get_db
from src.engines.hr.inbound.form_receiver import ApplicationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr", tags=["hr"])


@router.post("/apply", status_code=201)
async def apply(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(None),
    role: str = Form(...),
    location: str | None = Form(None),
    current_ctc: int | None = Form(None),
    expected_ctc: int | None = Form(None),
    notice_period_days: int | None = Form(None),
    years_experience: float | None = Form(None),
    application_answer: str | None = Form(None),
    linkedin_url: str | None = Form(None),
    source: str = Form(default="careers_form"),
    resume: UploadFile | None = File(None),
) -> JSONResponse:
    """
    Receive a job application from the yourcompany.com/careers form.
    Public endpoint — no auth required. CORS is set at the app level for yourcompany.com.
    Resume processing and acknowledgement happen as background tasks.
    """
    from src.engines.hr.models import CandidateCreate

    candidate = CandidateCreate(
        name=name,
        email=email,
        phone=phone,
        role=role,
        source=source,
        location=location,
        current_ctc=current_ctc,
        expected_ctc=expected_ctc,
        notice_period_days=notice_period_days,
        years_experience=years_experience,
        application_answer=application_answer,
        linkedin_url=linkedin_url,
    )

    resume_bytes: bytes | None = None
    resume_filename: str | None = None
    if resume and resume.filename:
        resume_bytes = await resume.read()
        resume_filename = resume.filename

    service = ApplicationService(db=db, settings=settings)
    try:
        result = await service.process(
            candidate=candidate,
            resume_bytes=resume_bytes,
            resume_filename=resume_filename,
        )
    except Exception as exc:
        logger.error("Application processing failed for %s: %s", email, exc)
        raise HTTPException(status_code=500, detail="Application processing failed")

    background_tasks.add_task(
        _run_ack_and_score,
        entity_id=result["entity_id"],
        application_id=result["application_id"],
        name=name,
        email=email,
        phone=phone,
        role=role,
        resume_text=result.get("resume_text", ""),
        application_answer=application_answer or "",
        expected_ctc=expected_ctc,
        settings=settings,
    )

    return JSONResponse(
        status_code=201,
        content={
            "message": "Application received",
            "entity_id": result["entity_id"],
            "application_id": result["application_id"],
            "is_duplicate": result["is_duplicate"],
        },
    )


@router.get("/health")
async def hr_health() -> dict:
    return {"status": "ok", "engine": "synq-hire"}


async def _run_ack_and_score(
    *,
    entity_id: str,
    application_id: str,
    name: str,
    email: str,
    phone: str | None,
    role: str,
    resume_text: str,
    application_answer: str,
    expected_ctc: int | None,
    settings: Settings,
) -> None:
    """Background task: send acknowledgement + trigger resume scoring."""
    try:
        from src.engines.hr.inbound.acknowledger import make_acknowledger
        ack = make_acknowledger()
        await ack.send(name=name, email=email, phone=phone, role=role)
    except Exception as exc:
        logger.error("Acknowledgement failed for %s: %s", email, exc)

    try:
        from src.engines.hr.scoring.answer_scorer import score_answer
        answer_result = score_answer(application_answer)
        if answer_result.auto_reject:
            logger.info("Auto-reject for %s: %s", email, answer_result.rejection_reason)
            return

        if resume_text and len(resume_text) > 50:
            from src.engines.hr.scoring.resume_scorer import make_resume_scorer
            scorer = make_resume_scorer()
            await scorer.score(
                resume_text=resume_text,
                application_answer=application_answer,
                role=role,
                role_salary_max=1500000,
            )
    except Exception as exc:
        logger.error("Background scoring failed for %s: %s", email, exc)


# ── Pre-screen trigger ────────────────────────────────────────────────────────

@router.post("/applications/{application_id}/start-prescreen", status_code=200)
async def start_prescreen(
    application_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Trigger pre-screen for an application. Creates screen session and sends Q1 via email.
    Called automatically when resume_score >= threshold, or manually from dashboard.
    """
    import json
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import text

    result = await db.execute(
        text(
            "SELECT a.id, a.candidate_entity_id, a.role_type, a.stage, "
            "e.name, e.attributes->>'email' AS email "
            "FROM hr_applications a "
            "JOIN entities e ON e.id = a.candidate_entity_id "
            "WHERE a.id = :app_id"
        ),
        {"app_id": application_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    if row.stage not in ("applied", "parsed"):
        return {"message": f"Application already in stage {row.stage}", "skipped": True}

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
        {"id": session_id, "app_id": application_id, "candidate_id": str(row.candidate_entity_id),
         "state": initial_state, "now": now},
    )
    await db.execute(
        text("UPDATE hr_applications SET stage = 'pre_screening', updated_at = :now WHERE id = :app_id"),
        {"now": now, "app_id": application_id},
    )
    await db.commit()

    background_tasks.add_task(
        _send_prescreen_question,
        candidate_email=row.email,
        candidate_name=row.name,
        role=row.role_type,
        question_index=0,
        is_probe=False,
        settings=settings,
    )

    return {"message": "Pre-screen started", "session_id": session_id}


async def _send_prescreen_question(
    *,
    candidate_email: str,
    candidate_name: str,
    role: str,
    question_index: int,
    is_probe: bool = False,
    settings,
) -> None:
    """Background: send a pre-screen question email."""
    try:
        from src.engines.hr.screening.dispatcher import make_dispatcher
        dispatcher = make_dispatcher()
        await dispatcher.send_question(
            candidate_email=candidate_email,
            candidate_name=candidate_name,
            role=role,
            question_index=question_index,
            is_probe=is_probe,
        )
    except Exception as exc:
        logger.error("Pre-screen Q%d send failed for %s: %s", question_index + 1, candidate_email, exc)


# ── Test routes ───────────────────────────────────────────────────────────────

@router.post("/applications/{application_id}/invite-test", status_code=201)
async def invite_to_test(
    application_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Generate test questions and send invite email. Called after pre_screened stage."""
    import json
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import text

    result = await db.execute(
        text(
            "SELECT a.id, a.candidate_entity_id, a.role_type, a.stage, "
            "e.name, e.attributes->>'email' AS email "
            "FROM hr_applications a "
            "JOIN entities e ON e.id = a.candidate_entity_id "
            "WHERE a.id = :app_id"
        ),
        {"app_id": application_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    from src.services.test_engine import generate_test_token

    token = generate_test_token()
    session_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    await db.execute(
        text(
            "INSERT INTO hr_test_sessions "
            "(id, application_id, candidate_entity_id, token, status, questions, created_at) "
            "VALUES (:id, :app_id, :candidate_id, :token, 'pending', '{}'::jsonb, :now) "
            "ON CONFLICT (application_id) DO NOTHING"
        ),
        {"id": session_id, "app_id": application_id,
         "candidate_id": str(row.candidate_entity_id), "token": token, "now": now},
    )
    await db.execute(
        text("UPDATE hr_applications SET stage = 'test_invited', updated_at = :now WHERE id = :app_id"),
        {"now": now, "app_id": application_id},
    )
    await db.commit()

    background_tasks.add_task(
        _generate_and_send_test_invite,
        token=token,
        session_id=session_id,
        candidate_email=row.email,
        candidate_name=row.name,
        role=row.role_type,
        settings=settings,
    )

    test_url = f"{settings.frontend_url}/test/{token}"
    return {"message": "Test invitation sent", "token": token, "test_url": test_url}


async def _generate_and_send_test_invite(
    *, token: str, session_id: str, candidate_email: str, candidate_name: str, role: str, settings
) -> None:
    """Background: generate test questions and email the test link."""
    try:
        from src.services.test_engine import make_test_engine
        engine = make_test_engine()
        questions = await engine.generate_questions(role=role, ai_required=False)

        import json
        from datetime import UTC, datetime

        from sqlalchemy import text

        from src.database import async_session_factory
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
            f"Congratulations! You've been shortlisted for the online assessment.\n\n"
            f"Please complete the test within 48 hours at the link below:\n"
            f"{test_url}\n\n"
            f"The test has 3 sections (Aptitude, English, and General Knowledge) "
            f"and takes approximately 35 minutes.\n\n"
            f"Note: You'll need to allow screen sharing and camera access when prompted.\n\n"
            f"Best,\n"
            f"Hiring Team\n"
            f"hiring@example.com"
        )
        await send_email_smtp(
            to_email=candidate_email,
            subject="YourCompany — Online Assessment Invitation",
            body=body,
            smtp_config=smtp_config,
        )
    except Exception as exc:
        logger.error("Test invite failed for %s: %s", candidate_email, exc)


@router.get("/test/{token}")
async def get_test(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Fetch test questions for a candidate (correct_index stripped before sending)."""
    from sqlalchemy import text

    result = await db.execute(
        text("SELECT id, status, questions, started_at FROM hr_test_sessions WHERE token = :token"),
        {"token": token},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")
    if row.status in ("completed", "timed_out"):
        raise HTTPException(status_code=410, detail="Test already completed")

    # Record started_at on first candidate access
    if row.started_at is None:
        from datetime import UTC, datetime
        await db.execute(
            text("UPDATE hr_test_sessions SET started_at = :now WHERE token = :token AND started_at IS NULL"),
            {"now": datetime.now(UTC), "token": token},
        )
        await db.commit()

    questions = row.questions if isinstance(row.questions, dict) else {}
    sanitized = {}
    for module, qs in questions.items():
        sanitized[module] = [
            {"question": q["question"], "options": q["options"], "index": i}
            for i, q in enumerate(qs)
        ]
    return {"session_id": str(row.id), "questions": sanitized, "status": row.status}


@router.post("/test/{token}/submit", status_code=200)
async def submit_test(
    token: str,
    answers: dict,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Submit test answers. Scores and advances stage."""
    from datetime import UTC, datetime

    from sqlalchemy import text

    from src.services.test_engine import score_test

    result = await db.execute(
        text("SELECT id, application_id, candidate_entity_id, questions, status FROM hr_test_sessions WHERE token = :token"),
        {"token": token},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")
    if row.status == "completed":
        raise HTTPException(status_code=410, detail="Test already submitted")

    questions = row.questions if isinstance(row.questions, dict) else {}
    score_result = score_test(
        questions=questions,
        answers=answers,
        ai_required="ai" in questions,
    )

    now = datetime.now(UTC)
    await db.execute(
        text(
            "UPDATE hr_test_sessions SET status = 'completed', "
            "aptitude_score = :apt, english_score = :eng, overall_score = :overall, "
            "completed_at = :now WHERE token = :token"
        ),
        {"apt": score_result["aptitude_score"], "eng": score_result["english_score"],
         "overall": score_result["overall_score"], "now": now, "token": token},
    )

    new_stage = "screened" if score_result["passed"] else "rejected"
    await db.execute(
        text("UPDATE hr_applications SET stage = :stage, updated_at = :now WHERE id = :app_id"),
        {"stage": new_stage, "app_id": str(row.application_id), "now": now},
    )
    await db.commit()

    return {"passed": score_result["passed"], "overall_score": score_result["overall_score"], "stage": new_stage}
