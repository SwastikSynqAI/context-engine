"""Initial schema: entities, relationships, embeddings, expert_decisions, data_quality_log

Revision ID: 001
Revises:
Create Date: 2026-04-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions — must exist before any vector column
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── entities ──────────────────────────────────────────────────────────────
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("pii_fields", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_entities_type", "entities", ["type"])
    op.create_index("ix_entities_name", "entities", ["name"])
    op.create_index("ix_entities_source_id", "entities", ["source_id"])
    op.create_index("ix_entities_type_name", "entities", ["type", "name"])
    op.create_unique_constraint("uq_entity_source_id", "entities", ["source", "source_id"])
    # Trigram index for fuzzy name search
    op.execute(
        "CREATE INDEX ix_entities_name_trgm ON entities USING gin (name gin_trgm_ops)"
    )

    # ── relationships ─────────────────────────────────────────────────────────
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "from_entity_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_entity_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_relationships_from_entity_id", "relationships", ["from_entity_id"])
    op.create_index("ix_relationships_to_entity_id", "relationships", ["to_entity_id"])
    op.create_index("ix_relationships_type", "relationships", ["relationship_type"])
    op.create_index("ix_relationships_from_to", "relationships", ["from_entity_id", "to_entity_id"])
    op.create_unique_constraint(
        "uq_relationship_pair_type",
        "relationships",
        ["from_entity_id", "to_entity_id", "relationship_type"],
    )

    # ── embeddings ────────────────────────────────────────────────────────────
    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("content_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_embeddings_entity_id", "embeddings", ["entity_id"])
    # HNSW index for approximate nearest-neighbour search (cosine distance)
    op.execute(
        "CREATE INDEX ix_embeddings_vector_hnsw ON embeddings "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    # ── expert_decisions ──────────────────────────────────────────────────────
    op.create_table(
        "expert_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("decision_type", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("human_action", sa.String(500), nullable=False),
        sa.Column("human_reasoning", sa.Text, nullable=True),
        sa.Column("outcome", sa.String(100), nullable=True),
        sa.Column("outcome_notes", sa.Text, nullable=True),
        sa.Column("feedback_signal", sa.String(50), nullable=True),
        sa.Column("primary_entity_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("outcome_recorded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_decisions_type", "expert_decisions", ["decision_type"])
    op.create_index("ix_decisions_actor", "expert_decisions", ["actor"])
    op.create_index("ix_decisions_primary_entity_id", "expert_decisions", ["primary_entity_id"])
    op.create_index("ix_decisions_timestamp", "expert_decisions", ["timestamp"])
    op.create_index("ix_decisions_type_actor", "expert_decisions", ["decision_type", "actor"])

    # ── data_quality_log ──────────────────────────────────────────────────────
    op.create_table(
        "data_quality_log",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("entities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("check_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("anomaly_description", sa.Text, nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_quality_log_entity_id", "data_quality_log", ["entity_id"])
    op.create_index("ix_quality_log_check_type", "data_quality_log", ["check_type"])
    op.create_index("ix_quality_log_timestamp", "data_quality_log", ["timestamp"])


def downgrade() -> None:
    op.drop_table("data_quality_log")
    op.drop_table("expert_decisions")
    op.drop_table("embeddings")
    op.drop_table("relationships")
    op.drop_table("entities")
