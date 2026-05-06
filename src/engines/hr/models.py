"""
Pydantic v2 models for the AI Hire HR engine.

Design:
- CandidateCreate / CandidateRead are thin wrappers — actual storage is in
  the existing entities table with type='candidate'.
- Application holds per-role state (one candidate can apply to multiple roles).
- ResumeScore and ScreenScore always include a breakdown and reasoning so
  Admin can inspect exactly why a candidate got any given score.
- ScreenChannel is WHATSAPP | EMAIL only — no voice.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator


class CandidateStage(str, Enum):
    APPLIED = "applied"
    PARSED = "parsed"
    PRE_SCREENING = "pre_screening"
    PRE_SCREENED = "pre_screened"
    TEST_INVITED = "test_invited"
    TEST_COMPLETED = "test_completed"
    SCREENED = "screened"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    POST_SCREENED = "post_screened"
    OFFER_SENT = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    HIRED = "hired"
    REJECTED = "rejected"


class ScreenChannel(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    # NO VOICE — text-only pre-screening by design


class OfferStatus(str, Enum):
    DRAFTED = "drafted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TestStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FLAGGED = "flagged"
    TIMED_OUT = "timed_out"


# ── Candidate ─────────────────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: str | None = None
    role: str
    source: str
    location: str | None = None
    current_ctc: int | None = None
    expected_ctc: int | None = None
    notice_period_days: int | None = None
    years_experience: float | None = None
    application_answer: str | None = None
    resume_path: str | None = None
    linkedin_url: str | None = None

    @property
    def pii_fields(self) -> list[str]:
        fields = ["email"]
        if self.phone:
            fields.append("phone")
        return fields

    def to_entity_attributes(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "source": self.source,
            "location": self.location,
            "current_ctc": self.current_ctc,
            "expected_ctc": self.expected_ctc,
            "notice_period_days": self.notice_period_days,
            "years_experience": self.years_experience,
            "application_answer": self.application_answer,
            "resume_path": self.resume_path,
            "linkedin_url": self.linkedin_url,
        }


class CandidateRead(BaseModel):
    entity_id: str
    name: str
    email: str
    phone: str | None = None
    role: str
    source: str
    stage: CandidateStage = CandidateStage.APPLIED
    match_score: float | None = None
    created_at: datetime


# ── Scoring ───────────────────────────────────────────────────────────────────

class ResumeScore(BaseModel):
    overall: float = Field(ge=0, le=100)
    breakdown: dict[str, float]
    reasoning: str
    green_flags: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    role: str
    auto_reject: bool = False


class QuestionScore(BaseModel):
    question_index: int
    score: float = Field(ge=0, le=20)
    notes: str


class ScreenScore(BaseModel):
    overall: float = Field(ge=0, le=100)
    question_scores: list[QuestionScore]
    role: str
    strong_signals: list[str] = Field(default_factory=list)


# ── Application ───────────────────────────────────────────────────────────────

class Application(BaseModel):
    id: str
    candidate_entity_id: str
    role: str
    source: str
    stage: CandidateStage = CandidateStage.APPLIED
    resume_score: float | None = None
    screen_score: float | None = None
    resume_score_breakdown: ResumeScore | None = None
    screen_score_breakdown: ScreenScore | None = None
    rejection_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @computed_field
    @property
    def combined_score(self) -> float | None:
        if self.resume_score is None:
            return None
        if self.screen_score is None:
            return self.resume_score
        return round(self.resume_score * 0.4 + self.screen_score * 0.6, 2)


# ── Screen Session ────────────────────────────────────────────────────────────

class ScreenSessionState(BaseModel):
    current_question_index: int = 0
    probe_used: bool = False
    last_reply_at: datetime | None = None
    reminder_sent: bool = False
    completed: bool = False
    timed_out: bool = False


class ScreenSession(BaseModel):
    id: str
    application_id: str
    candidate_entity_id: str
    channel: ScreenChannel
    conversation_state: ScreenSessionState = Field(default_factory=ScreenSessionState)
    created_at: datetime | None = None


class ScreenResponse(BaseModel):
    id: str
    session_id: str
    question_index: int
    question_text: str
    response_text: str
    is_probe_response: bool = False
    received_at: datetime


# ── Interview ─────────────────────────────────────────────────────────────────

class InterviewSlot(BaseModel):
    id: str
    application_id: str
    candidate_entity_id: str
    slot_start: datetime
    slot_end: datetime
    gcal_event_id: str | None = None
    google_meet_link: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    status: str = "scheduled"


# ── Offer ─────────────────────────────────────────────────────────────────────

class OfferDetails(BaseModel):
    ctc_annual: int
    basic_monthly: int
    hra_monthly: int
    special_allowance_monthly: int
    pf_monthly: int
    joining_date: str
    designation: str
    department: str
    reporting_to: str
    probation_months: int = 6
    notice_period_days: int = 60


class Offer(BaseModel):
    id: str
    application_id: str
    candidate_entity_id: str
    details: OfferDetails
    letter_path: str | None = None
    status: OfferStatus = OfferStatus.DRAFTED
    docusign_envelope_id: str | None = None
    created_at: datetime | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None


# ── Rubric Version ────────────────────────────────────────────────────────────

class RubricVersion(BaseModel):
    id: str
    role: str
    version: int
    weights: dict[str, float]
    reasoning: str
    created_at: datetime | None = None

    @model_validator(mode="after")
    def weights_sum_to_100(self) -> "RubricVersion":
        total = sum(self.weights.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Rubric weights must sum to 100, got {total}")
        return self


# ── Deduplication ─────────────────────────────────────────────────────────────

class DeduplicationResult(BaseModel):
    is_duplicate: bool
    existing_entity_id: str | None = None
    match_reason: str | None = None
