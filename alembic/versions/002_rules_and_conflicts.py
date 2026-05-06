"""Add rules and data_conflicts tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── rules ─────────────────────────────────────────────────────────────────
    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("condition", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("action", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("source_decision_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("source_conflict_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("fire_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rules_active", "rules", ["is_active"])
    op.create_index("ix_rules_created_by", "rules", ["created_by"])

    # ── data_conflicts ────────────────────────────────────────────────────────
    op.create_table(
        "data_conflicts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(255), nullable=False),
        sa.Column("value_a", sa.Text, nullable=False),
        sa.Column("source_a", sa.String(100), nullable=False),
        sa.Column("value_b", sa.Text, nullable=False),
        sa.Column("source_b", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="'open'"),
        sa.Column("resolved_value", sa.Text, nullable=True),
        sa.Column("resolved_by", sa.String(100), nullable=True),
        sa.Column("resolution_reasoning", sa.Text, nullable=True),
        sa.Column("generated_rule_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_conflicts_entity_field", "data_conflicts", ["entity_id", "field_name"])
    op.create_index("ix_conflicts_status", "data_conflicts", ["status"])


def downgrade() -> None:
    op.drop_table("data_conflicts")
    op.drop_table("rules")
