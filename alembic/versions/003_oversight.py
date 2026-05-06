"""Add Enterprise Oversight Layer tables: eval_cases, eval_runs, eval_results, policy_rules

Revision ID: 003
Revises: 002
Create Date: 2026-04-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── eval_cases ────────────────────────────────────────────────────────────
    op.create_table(
        "eval_cases",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("expected_themes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("intent_type", sa.String(100), nullable=True),
        sa.Column("min_expected_score", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_eval_cases_active", "eval_cases", ["is_active"])

    # ── eval_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("triggered_by", sa.String(100), nullable=False),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cases_run", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cases_passed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("delta_from_last", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_eval_runs_run_at", "eval_runs", ["run_at"])

    # ── eval_results ──────────────────────────────────────────────────────────
    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "eval_case_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("eval_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "eval_run_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actual_answer", sa.Text, nullable=False),
        sa.Column("judge_score", sa.Float, nullable=False),
        sa.Column("judge_notes", sa.Text, nullable=True),
        sa.Column("missing_themes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("passed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_eval_results_case", "eval_results", ["eval_case_id"])
    op.create_index("ix_eval_results_run", "eval_results", ["eval_run_id"])
    op.create_index("ix_eval_results_case_run", "eval_results", ["eval_case_id", "eval_run_id"])

    # ── policy_rules ──────────────────────────────────────────────────────────
    op.create_table(
        "policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("condition", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("severity", sa.String(50), nullable=False, server_default="warn"),
        sa.Column("violation_message", sa.Text, nullable=False),
        sa.Column("remediation", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("fire_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_policy_rules_active", "policy_rules", ["is_active"])
    op.create_index("ix_policy_rules_severity", "policy_rules", ["severity"])


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("eval_cases")
    op.drop_table("policy_rules")
