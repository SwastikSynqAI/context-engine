"""HR Engine: 13 new tables for AI Hire

Revision ID: 004
Revises: 003
Create Date: 2026-04-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── hr_roles ──────────────────────────────────────────────────────────────
    op.create_table(
        "hr_roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("role_type", sa.String(50), nullable=False),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requirements", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("salary_range", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("employment_type", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("posting_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_roles_role_type", "hr_roles", ["role_type"])
    op.create_index("ix_hr_roles_is_active", "hr_roles", ["is_active"])

    # ── hr_applications ───────────────────────────────────────────────────────
    op.create_table(
        "hr_applications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "candidate_entity_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("hr_roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("role_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False, server_default="applied"),
        sa.Column("stage_history", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("resume_path", sa.String(500), nullable=True),
        sa.Column("resume_text", sa.Text, nullable=True),
        sa.Column("resume_score", sa.Float, nullable=True),
        sa.Column("resume_score_data", postgresql.JSONB, nullable=True),
        sa.Column("screen_score", sa.Float, nullable=True),
        sa.Column("screen_score_data", postgresql.JSONB, nullable=True),
        sa.Column("match_reasoning", sa.Text, nullable=True),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("auto_rejected", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_applications_candidate", "hr_applications", ["candidate_entity_id"])
    op.create_index("ix_hr_applications_stage", "hr_applications", ["stage"])
    op.create_index("ix_hr_applications_role_type", "hr_applications", ["role_type"])
    op.create_unique_constraint(
        "uq_hr_application_candidate_role",
        "hr_applications",
        ["candidate_entity_id", "role_type"],
    )

    # ── hr_screen_sessions ────────────────────────────────────────────────────
    op.create_table(
        "hr_screen_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("hr_applications.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("conversation_state", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timed_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_screen_sessions_candidate", "hr_screen_sessions", ["candidate_entity_id"])

    # ── hr_screen_responses ───────────────────────────────────────────────────
    op.create_table(
        "hr_screen_responses",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("hr_screen_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_index", sa.Integer, nullable=False),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("response_text", sa.Text, nullable=False),
        sa.Column("is_probe_response", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_screen_responses_session", "hr_screen_responses", ["session_id"])

    # ── hr_test_sessions ──────────────────────────────────────────────────────
    op.create_table(
        "hr_test_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("hr_applications.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("questions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("aptitude_score", sa.Float, nullable=True),
        sa.Column("ai_proficiency_score", sa.Float, nullable=True),
        sa.Column("english_score", sa.Float, nullable=True),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column("proctoring_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_test_sessions_token", "hr_test_sessions", ["token"])
    op.create_index("ix_hr_test_sessions_status", "hr_test_sessions", ["status"])

    # ── hr_booking_slots ──────────────────────────────────────────────────────
    op.create_table(
        "hr_booking_slots",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("slot_date", sa.Date, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="45"),
        sa.Column("is_available", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_booking_slots_date", "hr_booking_slots", ["slot_date"])
    op.create_index("ix_hr_booking_slots_available", "hr_booking_slots", ["is_available"])

    # ── hr_interview_slots ────────────────────────────────────────────────────
    op.create_table(
        "hr_interview_slots",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("hr_applications.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "booking_slot_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("hr_booking_slots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("slot_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slot_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gcal_event_id", sa.String(255), nullable=True),
        sa.Column("google_meet_link", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="scheduled"),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── hr_offers ─────────────────────────────────────────────────────────────
    op.create_table(
        "hr_offers",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("hr_applications.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("offer_details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("letter_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="drafted"),
        sa.Column("docusign_envelope_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hr_offers_status", "hr_offers", ["status"])

    # ── hr_email_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "hr_email_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email_type", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("sent_to", sa.String(255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gmail_message_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="sent"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_email_logs_candidate", "hr_email_logs", ["candidate_entity_id"])
    op.create_index("ix_hr_email_logs_type", "hr_email_logs", ["email_type"])

    # ── hr_activity_log ───────────────────────────────────────────────────────
    op.create_table(
        "hr_activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("performed_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_activity_log_candidate", "hr_activity_log", ["candidate_entity_id"])
    op.create_index("ix_hr_activity_log_action", "hr_activity_log", ["action"])
    op.create_index("ix_hr_activity_log_created", "hr_activity_log", ["created_at"])

    # ── hr_rubric_versions ────────────────────────────────────────────────────
    op.create_table(
        "hr_rubric_versions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("role_type", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("weights", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_hr_rubric_role_version", "hr_rubric_versions", ["role_type", "version"]
    )
    op.create_index("ix_hr_rubric_versions_role_active", "hr_rubric_versions", ["role_type", "is_active"])

    # ── hr_notifications ──────────────────────────────────────────────────────
    op.create_table(
        "hr_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("candidate_entity_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("notification_type", sa.String(100), nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hr_notifications_is_read", "hr_notifications", ["is_read"])

    # ── hr_engine_config ─────────────────────────────────────────────────────
    op.create_table(
        "hr_engine_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("is_paused", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resume_score_threshold", sa.Float, nullable=False, server_default="65.0"),
        sa.Column("screen_score_threshold", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("test_pass_threshold", sa.Float, nullable=False, server_default="60.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("INSERT INTO hr_engine_config (id, is_paused) VALUES (1, false)")


def downgrade() -> None:
    op.drop_table("hr_engine_config")
    op.drop_table("hr_notifications")
    op.drop_table("hr_rubric_versions")
    op.drop_table("hr_activity_log")
    op.drop_table("hr_email_logs")
    op.drop_table("hr_offers")
    op.drop_table("hr_interview_slots")
    op.drop_table("hr_booking_slots")
    op.drop_table("hr_test_sessions")
    op.drop_table("hr_screen_responses")
    op.drop_table("hr_screen_sessions")
    op.drop_table("hr_applications")
    op.drop_table("hr_roles")
