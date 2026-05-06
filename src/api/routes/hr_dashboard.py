"""
AI Hire — Admin Dashboard API endpoints.

All endpoints under /hr/dashboard require a valid admin JWT.

Endpoints:
  GET  /hr/dashboard/pipeline                    — stage counts + candidate cards
  GET  /hr/dashboard/applications                — paginated list
  GET  /hr/dashboard/applications/{id}           — full detail
  POST /hr/dashboard/applications/{id}/advance   — advance to next stage
  POST /hr/dashboard/applications/{id}/reject    — reject with reason
  GET  /hr/dashboard/config                      — read editable config
  PUT  /hr/dashboard/config                      — save config key-value pairs
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import require_admin, verify_token
from src.config import Settings, get_settings
from src.database import get_db
from src.services.offer_generator import make_offer_generator, write_offer_docx

_bearer_optional = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr/dashboard", tags=["hr-dashboard"])

# ── Constants ─────────────────────────────────────────────────────────────────

PIPELINE_STAGES: list[str] = [
    "applied",
    "pre_screening",
    "pre_screened",
    "test_invited",
    "screened",
    "hr_approved",
    "shortlisted",
    "offer_sent",
    "hired",
    "rejected",
]

ADVANCE_MAP: dict[str, str] = {
    "applied": "pre_screening",
    "pre_screening": "pre_screened",
    "pre_screened": "test_invited",
    "test_invited": "screened",
    "screened": "hr_approved",
    "hr_approved": "shortlisted",
    "offer_sent": "hired",
}

CONFIG_KEYS: list[str] = [
    "hr_resume_score_threshold",
    "hr_screen_score_threshold",
    "hr_test_pass_threshold",
    "hiring_email",
    "admin_notify_email",
    "frontend_url",
    # Department heads
    "hod_bd_email",
    "hod_ops_email",
    "hod_it_email",
    "hod_ai_email",
    "hod_marketing_email",
    "hod_finance_email",
    "hod_hr_email",
    # Calendly scheduling links
    "calendly_default_link",
    "calendly_bd_link",
    "calendly_ops_link",
]

# Maps role_type → HOD config keys + department label
ROLE_HOD_MAP: dict[str, dict[str, str]] = {
    "bd_manager": {
        "department": "Business Development",
        "hod_email_key": "hod_bd_email",
        "calendly_key": "calendly_bd_link",
    },
    "operations_manager": {
        "department": "Operations & Administration",
        "hod_email_key": "hod_ops_email",
        "calendly_key": "calendly_ops_link",
    },
    "it": {
        "department": "Information Technology",
        "hod_email_key": "hod_it_email",
        "calendly_key": "calendly_default_link",
    },
    "ai": {
        "department": "AI / Data",
        "hod_email_key": "hod_ai_email",
        "calendly_key": "calendly_default_link",
    },
    "marketing": {
        "department": "Marketing",
        "hod_email_key": "hod_marketing_email",
        "calendly_key": "calendly_default_link",
    },
    "finance": {
        "department": "Finance",
        "hod_email_key": "hod_finance_email",
        "calendly_key": "calendly_default_link",
    },
    "hr": {
        "department": "Human Resources",
        "hod_email_key": "hod_hr_email",
        "calendly_key": "calendly_default_link",
    },
}

# ── Pure helper functions (tested directly) ───────────────────────────────────


def _build_pipeline_counts(rows) -> dict[str, int]:
    """Return a counts dict keyed by stage; all PIPELINE_STAGES present."""
    counts: dict[str, int] = {s: 0 for s in PIPELINE_STAGES}
    for row in rows:
        stage = getattr(row, "stage", None)
        if stage in counts:
            counts[stage] += 1
    return counts


def _config_defaults() -> dict[str, Any]:
    """Return the Settings-based defaults for all CONFIG_KEYS."""
    settings = get_settings()
    return {key: getattr(settings, key) for key in CONFIG_KEYS}


def _next_stage(current: str) -> str:
    """Return the next pipeline stage; raise ValueError if not advanceable."""
    if current not in ADVANCE_MAP:
        raise ValueError(f"Stage '{current}' cannot be advanced via ADVANCE_MAP")
    return ADVANCE_MAP[current]


# ── Email helpers ─────────────────────────────────────────────────────────────


async def _send_offer_email(
    *,
    to_email: str,
    candidate_name: str,
    role: str,
    docx_path: str,
    smtp_config: dict[str, Any],
) -> bool:
    """Send offer letter .docx as email attachment. Returns True on success."""
    first_name = candidate_name.split()[0]
    role_display = role.replace("_", " ").title()

    def _send() -> None:
        msg = MIMEMultipart()
        msg["Subject"] = f"Offer Letter — {role_display} at YourCompany"
        msg["From"] = smtp_config["from_email"]
        msg["To"] = to_email
        body = (
            f"Hi {first_name},\n\n"
            f"Congratulations! We're delighted to extend you an offer for the {role_display} "
            f"position at YourCompany.\n\n"
            f"Please find your offer letter attached. Review it carefully and let us know "
            f"if you have any questions.\n\n"
            f"We're excited to have you join the team!\n\n"
            f"Best regards,\n"
            f"Hiring Team\n"
            f"hiring@example.com"
        )
        msg.attach(MIMEText(body, "plain"))
        with open(docx_path, "rb") as f:
            part = MIMEBase(
                "application",
                "vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename="offer_letter.docx")
            msg.attach(part)
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["from_email"], to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        return True
    except Exception as exc:
        logger.error("Offer email failed to %s: %s", to_email, exc)
        return False


async def _get_config_value(db: AsyncSession, key: str) -> str:
    """Fetch a single config value from hr_config, falling back to Settings."""
    result = await db.execute(
        text("SELECT value FROM hr_config WHERE id = :key"), {"key": key}
    )
    row = result.fetchone()
    if row:
        return row[0]
    return getattr(get_settings(), key, "")


async def _send_hod_invite_email(
    *,
    to_email: str,
    hod_name: str,
    department: str,
    candidate_name: str,
    role: str,
    resume_score: float | None,
    screen_score: float | None,
    hr_feedback: str,
    calendly_link: str | None,
    smtp_config: dict[str, Any],
) -> None:
    """Notify the department HOD that a candidate has passed HR round."""
    role_display = role.replace("_", " ").title()

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[2nd Round] {candidate_name} — {role_display} at YourCompany"
        msg["From"] = smtp_config["from_email"]
        msg["To"] = to_email

        score_line = ""
        if resume_score is not None:
            score_line += f"Resume Score: {resume_score}"
        if screen_score is not None:
            score_line += f"  |  Screen Score: {screen_score}"

        calendly_line = (
            f"\nSchedule the 2nd round here: {calendly_link}"
            if calendly_link
            else "\nPlease reach out to HR to schedule the second round."
        )
        body = (
            f"Hi {hod_name},\n\n"
            f"A candidate has cleared the HR round for the {role_display} role and is ready "
            f"for the 2nd round interview with you.\n\n"
            f"Candidate: {candidate_name}\n"
            f"Department: {department}\n"
            f"{score_line}\n\n"
            f"HR Feedback:\n{hr_feedback or '(No feedback provided)'}\n"
            f"{calendly_line}\n\n"
            f"Please review the profile and schedule when you're available.\n\n"
            f"Best regards,\n"
            f"Hiring Team\n"
            f"hiring@example.com"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["from_email"], to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        logger.info("HOD invite sent to %s for candidate %s", to_email, candidate_name)
    except Exception as exc:
        logger.error("HOD invite email failed to %s: %s", to_email, exc)


async def _send_second_round_candidate_email(
    *,
    to_email: str,
    candidate_name: str,
    role: str,
    department: str,
    calendly_link: str | None,
    smtp_config: dict[str, Any],
) -> None:
    """Congratulate candidate and share 2nd round scheduling link."""
    first_name = candidate_name.split()[0]
    role_display = role.replace("_", " ").title()

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Congratulations! You've progressed to Round 2 — {role_display} at YourCompany"
        msg["From"] = smtp_config["from_email"]
        msg["To"] = to_email

        calendly_line = (
            f"\nPlease use this link to schedule your second round interview at a time "
            f"that works for you:\n{calendly_link}\n"
            if calendly_link
            else "\nOur team will reach out shortly to schedule your second round interview.\n"
        )
        body = (
            f"Hi {first_name},\n\n"
            f"Congratulations! You've successfully cleared the first round of interviews "
            f"for the {role_display} role at YourCompany.\n\n"
            f"We'd like to invite you to a second round with the Head of {department}.\n"
            f"{calendly_line}\n"
            f"This round will help us understand your domain expertise and fit in more depth. "
            f"It typically takes 45–60 minutes.\n\n"
            f"We're excited about your candidacy and look forward to speaking with you again!\n\n"
            f"Best regards,\n"
            f"Hiring Team\n"
            f"hiring@example.com"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["from_email"], to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        logger.info("2nd round candidate email sent to %s", to_email)
    except Exception as exc:
        logger.error("2nd round candidate email failed to %s: %s", to_email, exc)


async def _send_interview_invite_email(
    *,
    to_email: str,
    candidate_name: str,
    role: str,
    start_iso: str,
    meet_link: str | None,
    smtp_config: dict[str, Any],
) -> None:
    """Send a Google Meet interview invite email to the candidate."""
    from datetime import datetime

    first_name = candidate_name.split()[0]
    role_display = role.replace("_", " ").title()

    try:
        dt = datetime.fromisoformat(start_iso)
        time_str = dt.strftime("%-d %B %Y at %-I:%M %p IST")
    except Exception:
        time_str = start_iso

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Interview scheduled — {role_display} at YourCompany"
        msg["From"] = smtp_config["from_email"]
        msg["To"] = to_email

        meet_line = f"\nGoogle Meet link: {meet_link}" if meet_link else ""
        body = (
            f"Hi {first_name},\n\n"
            f"We'd love to speak with you! Your interview for the {role_display} "
            f"role at YourCompany has been scheduled.\n\n"
            f"Date & Time: {time_str}{meet_line}\n\n"
            f"Please join a few minutes early. If you need to reschedule, "
            f"reply to this email as soon as possible.\n\n"
            f"Looking forward to speaking with you!\n\n"
            f"Best regards,\n"
            f"Hiring Team\n"
            f"hiring@example.com"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["from_email"], to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        logger.info("Interview invite email sent to %s", to_email)
    except Exception as exc:
        logger.error("Interview invite email failed to %s: %s", to_email, exc)


async def _send_rejection_email(
    *,
    to_email: str,
    candidate_name: str,
    role: str,
    smtp_config: dict[str, Any],
) -> None:
    """Send a polite rejection email. Errors are logged but not raised."""
    first_name = candidate_name.split()[0]
    role_display = role.replace("_", " ").title()

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your application — {role_display} at YourCompany"
        msg["From"] = smtp_config["from_email"]
        msg["To"] = to_email
        body = (
            f"Hi {first_name},\n\n"
            f"Thank you for your interest in the {role_display} role at YourCompany and for "
            f"the time you invested in our process.\n\n"
            f"After careful consideration, we've decided to move forward with other candidates "
            f"whose profiles more closely match our current requirements. This was a difficult "
            f"decision and we genuinely appreciate your effort.\n\n"
            f"We'll keep your profile on file and may reach out if a suitable opportunity arises.\n\n"
            f"We wish you all the best in your job search.\n\n"
            f"Best regards,\n"
            f"Hiring Team\n"
            f"hiring@example.com"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["from_email"], to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        logger.info("Rejection email sent to %s", to_email)
    except Exception as exc:
        logger.error("Rejection email failed to %s: %s", to_email, exc)


# ── Pydantic request bodies ────────────────────────────────────────────────────


class RejectBody(BaseModel):
    rejection_reason: str = ""


class ConfigPutBody(BaseModel):
    updates: dict[str, str]


class GenerateOfferBody(BaseModel):
    ctc_lpa: float
    joining_date: str
    reporting_to: str
    location: str


class ScheduleInterviewBody(BaseModel):
    start_iso: str  # ISO 8601, e.g. "2026-05-10T10:00:00+05:30"
    end_iso: str    # ISO 8601, e.g. "2026-05-10T11:00:00+05:30"


class HRDecisionBody(BaseModel):
    decision: str   # "yes" or "no"
    feedback: str = ""
    hod_name: str = "Head of Department"  # override HOD display name if needed


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _ensure_config_table(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS hr_config (
            id TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """))
    await db.commit()


async def _get_application(db: AsyncSession, app_id: str) -> dict[str, Any]:
    row = await db.execute(
        text("""
            SELECT
                a.id, a.stage, a.role_type AS role, a.source,
                a.rejection_reason, a.resume_score, a.screen_score,
                a.created_at, a.updated_at,
                e.name, e.attributes
            FROM hr_applications a
            JOIN entities e ON e.id = a.candidate_entity_id
            WHERE a.id = :id
        """),
        {"id": app_id},
    )
    r = row.mappings().first()
    if r is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return dict(r)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/pipeline")
async def get_pipeline(
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    """Return stage counts and candidate cards for the last 200 applications."""
    result = await db.execute(
        text("""
            SELECT
                a.id, a.stage, a.role_type AS role,
                a.resume_score, a.screen_score, a.updated_at,
                e.name, e.attributes
            FROM hr_applications a
            JOIN entities e ON e.id = a.candidate_entity_id
            ORDER BY a.created_at DESC
            LIMIT 200
        """)
    )
    rows = [dict(r) for r in result.mappings().all()]

    counts = _build_pipeline_counts(rows)

    by_stage: dict[str, list[dict[str, Any]]] = {stage: [] for stage in PIPELINE_STAGES}
    for row in rows:
        stage = row.get("stage", "applied")
        attrs: dict[str, Any] = row.get("attributes") or {}
        card = {
            "id": str(row["id"]),
            "name": row["name"],
            "email": attrs.get("email"),
            "role": row["role"],
            "resume_score": row["resume_score"],
            "screen_score": row["screen_score"],
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        if stage in by_stage:
            by_stage[stage].append(card)
        else:
            by_stage[stage] = [card]

    return {"counts": counts, "by_stage": by_stage}


@router.get("/applications")
async def list_applications(
    stage: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    """Paginated list of applications, optionally filtered by stage."""
    if stage and stage not in PIPELINE_STAGES:
        raise HTTPException(status_code=422, detail=f"Invalid stage '{stage}'")
    query = """
        SELECT
            a.id, a.stage, a.role_type AS role, a.source,
            a.rejection_reason, a.resume_score, a.screen_score,
            a.created_at, a.updated_at,
            e.name, e.attributes
        FROM hr_applications a
        JOIN entities e ON e.id = a.candidate_entity_id
    """
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if stage:
        query += " WHERE a.stage = :stage"
        params["stage"] = stage
    query += " ORDER BY a.created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()

    items = []
    for r in rows:
        attrs: dict[str, Any] = r.get("attributes") or {}
        items.append({
            "id": str(r["id"]),
            "stage": r["stage"],
            "role": r["role"],
            "source": r["source"],
            "name": r["name"],
            "email": attrs.get("email"),
            "resume_score": r["resume_score"],
            "screen_score": r["screen_score"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        })

    return {"items": items, "limit": limit, "offset": offset}


@router.get("/applications/{id}")
async def get_application_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    """Full detail: application + entity attributes + screen session + test session."""
    app = await _get_application(db, id)
    attrs: dict[str, Any] = app.get("attributes") or {}

    # Screen session
    screen_result = await db.execute(
        text("""
            SELECT id, conversation_state, started_at, completed_at
            FROM hr_screen_sessions
            WHERE application_id = :app_id
            ORDER BY started_at DESC
            LIMIT 1
        """),
        {"app_id": id},
    )
    screen_row = screen_result.mappings().first()
    screen_session = dict(screen_row) if screen_row else None
    if screen_session:
        for k in ("started_at", "completed_at"):
            if screen_session.get(k):
                screen_session[k] = screen_session[k].isoformat()
        screen_session["id"] = str(screen_session["id"])

    # Test session
    test_result = await db.execute(
        text("""
            SELECT id, status, aptitude_score, english_score, overall_score, completed_at
            FROM hr_test_sessions
            WHERE application_id = :app_id
            ORDER BY completed_at DESC NULLS LAST
            LIMIT 1
        """),
        {"app_id": id},
    )
    test_row = test_result.mappings().first()
    test_session = dict(test_row) if test_row else None
    if test_session:
        if test_session.get("completed_at"):
            test_session["completed_at"] = test_session["completed_at"].isoformat()
        test_session["id"] = str(test_session["id"])

    return {
        "id": str(app["id"]),
        "stage": app["stage"],
        "role": app["role"],
        "source": app["source"],
        "rejection_reason": app["rejection_reason"],
        "resume_score": app["resume_score"],
        "screen_score": app["screen_score"],
        "created_at": app["created_at"].isoformat() if app["created_at"] else None,
        "updated_at": app["updated_at"].isoformat() if app["updated_at"] else None,
        "name": app["name"],
        "email": attrs.get("email"),
        "phone": attrs.get("phone"),
        "location": attrs.get("location"),
        "current_ctc": attrs.get("current_ctc"),
        "expected_ctc": attrs.get("expected_ctc"),
        "notice_period_days": attrs.get("notice_period_days"),
        "years_experience": attrs.get("years_experience"),
        "linkedin_url": attrs.get("linkedin_url"),
        "application_answer": attrs.get("application_answer"),
        "screen_session": screen_session,
        "test_session": test_session,
    }


@router.post("/applications/{id}/advance")
async def advance_application(
    id: str,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    """Advance application to the next pipeline stage."""
    app = await _get_application(db, id)
    current_stage = app["stage"]
    try:
        next_stage = _next_stage(current_stage)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Stage '{current_stage}' cannot be advanced. Not in ADVANCE_MAP.",
        )

    # Fetch candidate info BEFORE commit (needed for test invite)
    candidate_row = None
    if next_stage == "test_invited":
        result = await db.execute(
            text(
                "SELECT e.attributes->>'name' AS name, e.attributes->>'email' AS email, "
                "a.role_type FROM hr_applications a "
                "JOIN entities e ON e.id = a.candidate_entity_id WHERE a.id = :id"
            ),
            {"id": id},
        )
        candidate_row = result.fetchone()

    await db.execute(
        text("UPDATE hr_applications SET stage = :next_stage, updated_at = NOW() WHERE id = :id"),
        {"next_stage": next_stage, "id": id},
    )
    await db.commit()

    # Send test invite after commit so session is clean
    if next_stage == "test_invited" and candidate_row and candidate_row.email:
        try:
            from src.workers.stage_advancement import _invite_to_test
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(
                _invite_to_test(
                    application_id=id,
                    candidate_email=candidate_row.email,
                    candidate_name=candidate_row.name or "Candidate",
                    role=candidate_row.role_type,
                    settings=get_settings(),
                )
            )
            logger.info("Test invite task queued for %s", candidate_row.email)
        except Exception as exc:
            logger.error("Test invite task failed: %s", exc)

    return {"id": id, "previous_stage": current_stage, "stage": next_stage}


@router.post("/applications/{id}/reject")
async def reject_application(
    id: str,
    body: RejectBody = RejectBody(),
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Reject an application with an optional reason and send a rejection email."""
    app = await _get_application(db, id)

    await db.execute(
        text("""
            UPDATE hr_applications
            SET stage = 'rejected', rejection_reason = :reason, updated_at = NOW()
            WHERE id = :id
        """),
        {"reason": body.rejection_reason, "id": id},
    )
    await db.commit()

    attrs: dict[str, Any] = app.get("attributes") or {}
    candidate_email = attrs.get("email")
    if candidate_email and settings.smtp_username and settings.smtp_password:
        await _send_rejection_email(
            to_email=candidate_email,
            candidate_name=app["name"],
            role=app["role"] or "Unknown Role",
            smtp_config={
                "host": settings.smtp_host,
                "port": settings.smtp_port,
                "username": settings.smtp_username,
                "password": settings.smtp_password,
                "from_email": settings.hiring_email,
            },
        )

    return {"id": id, "stage": "rejected", "rejection_reason": body.rejection_reason}


@router.post("/applications/{application_id}/generate-offer")
async def generate_offer(
    application_id: str,
    body: GenerateOfferBody,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Generate an offer letter .docx for a shortlisted application."""
    app = await _get_application(db, application_id)

    if app["stage"] != "shortlisted":
        raise HTTPException(
            status_code=422,
            detail=f"Application must be in 'shortlisted' stage to generate an offer (current: {app['stage']})",
        )

    candidate_name: str = app["name"]
    role: str = app["role"] or "Unknown Role"

    os.makedirs(settings.uploads_offers_dir, exist_ok=True)
    output_path = f"{settings.uploads_offers_dir}/{application_id}_offer.docx"

    offer_generator = make_offer_generator()
    narrative = await offer_generator.generate_narrative(
        candidate_name=candidate_name,
        role=role,
        ctc_lpa=body.ctc_lpa,
        joining_date=body.joining_date,
        reporting_to=body.reporting_to,
        location=body.location,
    )

    write_offer_docx(
        output_path=output_path,
        candidate_name=candidate_name,
        role=role,
        ctc_lpa=body.ctc_lpa,
        joining_date=body.joining_date,
        narrative=narrative,
        reporting_to=body.reporting_to,
        location=body.location,
    )

    await db.execute(
        text("""
            UPDATE hr_applications
            SET stage = 'offer_sent', updated_at = NOW()
            WHERE id = :id
        """),
        {"id": application_id},
    )
    await db.commit()

    filename = f"{application_id}_offer.docx"
    return {"message": "Offer generated", "file": filename, "stage": "offer_sent"}


@router.get("/applications/{application_id}/offer")
async def download_offer(
    application_id: str,
    settings: Settings = Depends(get_settings),
    token: str | None = Query(default=None),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_optional),
) -> FileResponse:
    """Download the generated offer letter .docx. Accepts Bearer header OR ?token= query param."""
    raw_token: str | None = None
    if credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        subject = verify_token(raw_token, settings)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid token")

    if subject != settings.admin_email:
        raise HTTPException(status_code=403, detail="Admin only")

    path = f"{settings.uploads_offers_dir}/{application_id}_offer.docx"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Offer letter not found")

    filename = f"offer_{application_id[:8]}.docx"
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.post("/applications/{application_id}/send-offer")
async def send_offer_email_endpoint(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Email the generated offer letter .docx to the candidate."""
    app = await _get_application(db, application_id)

    if app["stage"] != "offer_sent":
        raise HTTPException(
            status_code=422,
            detail=f"Application must be in 'offer_sent' stage (current: {app['stage']})",
        )

    attrs: dict[str, Any] = app.get("attributes") or {}
    candidate_email = attrs.get("email")
    if not candidate_email:
        raise HTTPException(status_code=422, detail="No email address on file for this candidate")

    docx_path = f"{settings.uploads_offers_dir}/{application_id}_offer.docx"
    if not os.path.exists(docx_path):
        raise HTTPException(status_code=404, detail="Offer letter file not found — generate it first")

    if not settings.smtp_username or not settings.smtp_password:
        raise HTTPException(status_code=503, detail="SMTP not configured")

    sent = await _send_offer_email(
        to_email=candidate_email,
        candidate_name=app["name"],
        role=app["role"] or "Unknown Role",
        docx_path=docx_path,
        smtp_config={
            "host": settings.smtp_host,
            "port": settings.smtp_port,
            "username": settings.smtp_username,
            "password": settings.smtp_password,
            "from_email": settings.hiring_email,
        },
    )

    if not sent:
        raise HTTPException(status_code=502, detail="Failed to send offer email — check SMTP config")

    return {"message": "Offer email sent", "to": candidate_email}


@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    """Return editable config: reads hr_config table, falls back to Settings defaults."""
    await _ensure_config_table(db)

    defaults = _config_defaults()
    result = await db.execute(text("SELECT id, value FROM hr_config WHERE id = ANY(:keys)"), {"keys": CONFIG_KEYS})
    stored = {r["id"]: r["value"] for r in result.mappings().all()}

    merged: dict[str, Any] = {}
    for key in CONFIG_KEYS:
        merged[key] = stored[key] if key in stored else defaults[key]

    return merged


@router.put("/config")
async def put_config(
    body: ConfigPutBody,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    """Save config key-value pairs to hr_config table (only CONFIG_KEYS allowed)."""
    await _ensure_config_table(db)

    unknown = [k for k in body.updates if k not in CONFIG_KEYS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown config keys: {unknown}")

    for key, value in body.updates.items():
        await db.execute(
            text("""
                INSERT INTO hr_config (id, value) VALUES (:key, :value)
                ON CONFLICT (id) DO UPDATE SET value = EXCLUDED.value
            """),
            {"key": key, "value": str(value)},
        )
    await db.commit()
    return {"saved": list(body.updates.keys())}


@router.post("/applications/{application_id}/schedule-interview")
async def schedule_interview(
    application_id: str,
    body: ScheduleInterviewBody,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Schedule a Google Meet interview for a screened candidate.
    Creates a Google Calendar event (if configured) and emails the candidate.
    Works without Google Calendar — still sends the candidate email.
    """
    app = await _get_application(db, application_id)

    if app["stage"] not in ("screened", "shortlisted", "pre_screened"):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot schedule interview for stage '{app['stage']}' "
                   f"(expected: screened, pre_screened, or shortlisted)",
        )

    attrs: dict[str, Any] = app.get("attributes") or {}
    candidate_email = attrs.get("email")
    if not candidate_email:
        raise HTTPException(status_code=422, detail="No email on file for this candidate")

    event_id = ""
    meet_link = ""

    from src.services.gcal_service import make_gcal_service
    gcal = make_gcal_service()
    if gcal:
        try:
            result = gcal.create_interview_event(
                candidate_name=app["name"],
                candidate_email=candidate_email,
                role=app["role"] or "Unknown Role",
                start_iso=body.start_iso,
                end_iso=body.end_iso,
            )
            event_id = result["event_id"]
            meet_link = result["meet_link"]
        except Exception as exc:
            logger.error("GCal event creation failed: %s", exc)

    if settings.smtp_username and settings.smtp_password:
        await _send_interview_invite_email(
            to_email=candidate_email,
            candidate_name=app["name"],
            role=app["role"] or "Unknown Role",
            start_iso=body.start_iso,
            meet_link=meet_link or None,
            smtp_config={
                "host": settings.smtp_host,
                "port": settings.smtp_port,
                "username": settings.smtp_username,
                "password": settings.smtp_password,
                "from_email": settings.hiring_email,
            },
        )

    return {
        "message": "Interview scheduled",
        "gcal_configured": gcal is not None,
        "event_id": event_id,
        "meet_link": meet_link,
        "candidate_email": candidate_email,
    }


@router.post("/applications/{application_id}/hr-decision")
async def hr_decision(
    application_id: str,
    body: HRDecisionBody,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Record HR's yes/no decision after the first interview round.

    - "yes"  → stage=hr_approved, email HOD with candidate summary,
                email candidate with 2nd-round Calendly link.
    - "no"   → stage=rejected, send rejection email to candidate.
    """
    if body.decision not in ("yes", "no"):
        raise HTTPException(status_code=422, detail="decision must be 'yes' or 'no'")

    app = await _get_application(db, application_id)

    if app["stage"] not in ("screened", "hr_approved"):
        raise HTTPException(
            status_code=422,
            detail=f"HR decision only valid for 'screened' or 'hr_approved' stage (current: {app['stage']})",
        )

    attrs: dict[str, Any] = app.get("attributes") or {}
    candidate_email = attrs.get("email")
    role = app["role"] or "unknown"

    smtp_config: dict[str, Any] | None = None
    if settings.smtp_username and settings.smtp_password:
        smtp_config = {
            "host": settings.smtp_host,
            "port": settings.smtp_port,
            "username": settings.smtp_username,
            "password": settings.smtp_password,
            "from_email": settings.hiring_email,
        }

    if body.decision == "no":
        await db.execute(
            text("""
                UPDATE hr_applications
                SET stage = 'rejected', rejection_reason = :reason, updated_at = NOW()
                WHERE id = :id
            """),
            {"reason": body.feedback or "Did not pass HR round", "id": application_id},
        )
        await db.commit()

        if candidate_email and smtp_config:
            await _send_rejection_email(
                to_email=candidate_email,
                candidate_name=app["name"],
                role=role,
                smtp_config=smtp_config,
            )

        return {"id": application_id, "stage": "rejected", "decision": "no"}

    # decision == "yes"
    await _ensure_config_table(db)

    role_cfg = ROLE_HOD_MAP.get(role, {
        "department": "HR",
        "hod_email_key": "hod_hr_email",
        "calendly_key": "calendly_default_link",
    })
    department = role_cfg["department"]
    hod_email = await _get_config_value(db, role_cfg["hod_email_key"])
    calendly_link = await _get_config_value(db, role_cfg["calendly_key"])
    if not calendly_link:
        calendly_link = await _get_config_value(db, "calendly_default_link")

    # Fall back to admin notify email if HOD not set
    if not hod_email:
        hod_email = settings.admin_notify_email

    await db.execute(
        text("UPDATE hr_applications SET stage = 'hr_approved', updated_at = NOW() WHERE id = :id"),
        {"id": application_id},
    )
    await db.commit()

    if smtp_config:
        await _send_hod_invite_email(
            to_email=hod_email,
            hod_name=body.hod_name,
            department=department,
            candidate_name=app["name"],
            role=role,
            resume_score=app.get("resume_score"),
            screen_score=app.get("screen_score"),
            hr_feedback=body.feedback,
            calendly_link=calendly_link or None,
            smtp_config=smtp_config,
        )
        if candidate_email:
            await _send_second_round_candidate_email(
                to_email=candidate_email,
                candidate_name=app["name"],
                role=role,
                department=department,
                calendly_link=calendly_link or None,
                smtp_config=smtp_config,
            )

    return {
        "id": application_id,
        "stage": "hr_approved",
        "decision": "yes",
        "hod_notified": hod_email,
        "calendly_link": calendly_link or None,
    }


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    """Pipeline analytics: stage funnel, score averages, weekly intake, conversion rates."""

    # Stage counts
    stage_result = await db.execute(
        text("SELECT stage, COUNT(*) AS cnt FROM hr_applications GROUP BY stage")
    )
    stage_counts: dict[str, int] = {r["stage"]: int(r["cnt"]) for r in stage_result.mappings().all()}
    total = sum(stage_counts.values())

    # Score averages by role
    score_result = await db.execute(
        text("""
            SELECT role_type,
                COUNT(*) AS total,
                ROUND(AVG(resume_score)::numeric, 1) AS avg_resume,
                ROUND(AVG(screen_score)::numeric, 1) AS avg_screen
            FROM hr_applications
            GROUP BY role_type
            ORDER BY total DESC
        """)
    )
    by_role = [
        {
            "role": r["role_type"] or "unknown",
            "total": int(r["total"]),
            "avg_resume": float(r["avg_resume"]) if r["avg_resume"] is not None else None,
            "avg_screen": float(r["avg_screen"]) if r["avg_screen"] is not None else None,
        }
        for r in score_result.mappings().all()
    ]

    # Weekly intake — last 10 weeks
    weekly_result = await db.execute(
        text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COUNT(*) AS cnt
            FROM hr_applications
            WHERE created_at >= NOW() - INTERVAL '10 weeks'
            GROUP BY 1
            ORDER BY 1
        """)
    )
    weekly_intake = [
        {"week": str(r["week"]), "count": int(r["cnt"])}
        for r in weekly_result.mappings().all()
    ]

    # Conversion rates relative to total applied
    applied_count = stage_counts.get("applied", 0) + sum(
        stage_counts.get(s, 0)
        for s in ["pre_screening", "pre_screened", "test_invited", "screened", "shortlisted", "offer_sent", "hired"]
    )
    funnel = []
    for stage in PIPELINE_STAGES:
        if stage == "rejected":
            continue
        count = stage_counts.get(stage, 0)
        funnel.append({
            "stage": stage,
            "count": count,
            "rate": round(count / applied_count * 100, 1) if applied_count > 0 else 0.0,
        })

    return {
        "total": total,
        "stage_counts": stage_counts,
        "by_role": by_role,
        "weekly_intake": weekly_intake,
        "funnel": funnel,
    }
