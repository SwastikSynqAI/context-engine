"""
SQLAlchemy 2.0 async models — the core schema for Context Engine.

Design decisions:
- JSONB attributes field is the flexible bag for source-specific fields (avoid schema churn)
- confidence float [0.0, 1.0] on every entity/relationship — reflects certainty of the data
- context_snapshot on expert_decisions is a JSONB copy, NOT a foreign key — snapshots must
  be immutable because the live data will change after the decision is made
- All PII fields are flagged via pii_fields JSONB on entities for DPDP compliance
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    # Flexible schema bag — source-specific fields live here
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Source of truth for this entity record
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    # External ID in the source system (e.g. HubSpot deal ID, Sheet row ID)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # [0.0, 1.0] — how certain we are this entity record is accurate
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    # DPDP: list of attribute keys that contain PII
    pii_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships (ORM)
    embeddings: Mapped[list["Embedding"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )
    outgoing_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.from_entity_id",
        back_populates="from_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.to_entity_id",
        back_populates="to_entity",
    )
    quality_logs: Mapped[list["DataQualityLog"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Unique constraint: same source should not produce two records for the same entity
        UniqueConstraint("source", "source_id", name="uq_entity_source_id"),
        Index("ix_entities_type_name", "type", "name"),
        Index("ix_entities_name_trgm", "name", postgresql_using="gin",
              postgresql_ops={"name": "gin_trgm_ops"}),
    )

    def __repr__(self) -> str:
        return f"<Entity {self.type}:{self.name} [{self.id[:8]}]>"


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    from_entity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_entity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Additional facts about the relationship (e.g. deal value, commission %, start date)
    # Named rel_metadata to avoid collision with SQLAlchemy's reserved 'metadata' attribute
    rel_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    from_entity: Mapped["Entity"] = relationship(
        foreign_keys=[from_entity_id], back_populates="outgoing_relationships"
    )
    to_entity: Mapped["Entity"] = relationship(
        foreign_keys=[to_entity_id], back_populates="incoming_relationships"
    )

    __table_args__ = (
        UniqueConstraint(
            "from_entity_id", "to_entity_id", "relationship_type",
            name="uq_relationship_pair_type",
        ),
        Index("ix_relationships_from_to", "from_entity_id", "to_entity_id"),
    )

    def __repr__(self) -> str:
        return f"<Relationship {self.from_entity_id[:8]} --{self.relationship_type}--> {self.to_entity_id[:8]}>"


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    entity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # The text that was embedded — stored so we can inspect/reindex without re-fetching
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    # 1536-dim vector (OpenAI ada-002 / Claude embedding compatible)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    # Chunk metadata: position, source document page, etc.
    emb_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    entity: Mapped["Entity"] = relationship(back_populates="embeddings")

    __table_args__ = (
        Index(
            "ix_embeddings_vector_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class ExpertDecision(Base):
    """
    Every human approval / rejection / override becomes a permanent training record.

    context_snapshot is stored as a JSONB copy at decision time — it must NOT be a
    reference because the underlying entity data will change after the decision.
    """
    __tablename__ = "expert_decisions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Everything the system knew at the moment this decision was made
    context_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # What the human actually did / decided
    human_action: Mapped[str] = mapped_column(String(500), nullable=False)
    # Optional free-text reasoning the human provided
    human_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Tracked asynchronously — did this decision lead to a good outcome?
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Feedback signal for the self-improvement loop: positive / negative / neutral
    feedback_signal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Primary entity this decision was about (if applicable)
    primary_entity_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    outcome_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_decisions_type_actor", "decision_type", "actor"),
        Index("ix_decisions_timestamp", "timestamp"),
    )


class Rule(Base):
    """
    Encoded expert reasoning — the "conflict resolution + rule" step from the Dialect demo.

    When a human resolves a conflict or makes a decision, they can optionally encode
    the reasoning as a Rule. The Rule then fires automatically on future queries and
    context assembly — the system applies it without needing the human present.

    Examples for YourCompany:
    - condition: {entity_type: "client", attribute: "headcount", sources_conflict: true}
      action: {prefer_source: "hubspot", over: "google_sheets"}
      → "when two sources disagree on headcount, trust HubSpot"

    - condition: {entity_type: "deal", attribute: "seats", gte: 500}
      action: {apply_pricing_tier: "enterprise", notify: "admin"}
      → "deals with 500+ seats always trigger enterprise pricing review"

    - condition: {lead_attribute: "industry", value: "bfsi", funded_recently: true}
      action: {priority: "high", icp_signal: "strong"}
      → "recently-funded BFSI companies are strong ICP signals"
    """
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    # Short human-readable name for this rule
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Free-text explanation of WHY this rule exists — the captured reasoning
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured condition: when does this rule apply?
    # Examples: {"entity_type": "client"}, {"deal_seats_gte": 500}, {"industry": "bfsi"}
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Structured action: what should the system do when the condition is met?
    # Examples: {"prefer_source": "hubspot"}, {"priority": "high"}, {"flag_for": "admin"}
    action: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Who created this rule
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    # The decision that triggered this rule (optional — rules can be created independently)
    source_decision_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True, index=True
    )
    # The conflict this rule resolves (optional)
    source_conflict_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # How many times this rule has fired — tracks usage and relevance
    fire_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_rules_active", "is_active"),
        Index("ix_rules_created_by", "created_by"),
    )


class DataConflict(Base):
    """
    When two data sources disagree about the same field on the same entity.

    Example: HubSpot says Acme Corp has 150 employees, Google Sheets says 300.
    A human reviews, picks the correct value, and optionally encodes a Rule so
    the same conflict never needs manual resolution again.
    """
    __tablename__ = "data_conflicts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    entity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which attribute has conflicting values
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The two conflicting values and their sources
    value_a: Mapped[str] = mapped_column(Text, nullable=False)
    source_a: Mapped[str] = mapped_column(String(100), nullable=False)
    value_b: Mapped[str] = mapped_column(Text, nullable=False)
    source_b: Mapped[str] = mapped_column(String(100), nullable=False)
    # Status: open | resolved
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)
    # The value the human chose as correct
    resolved_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Who resolved it
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Their reasoning — this is what gets encoded into a Rule
    resolution_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    # If resolving this conflict generated a Rule, track it
    generated_rule_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_conflicts_entity_field", "entity_id", "field_name"),
        Index("ix_conflicts_status", "status"),
    )


class DataQualityLog(Base):
    __tablename__ = "data_quality_log"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    entity_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    check_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # passed / failed / warning
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    anomaly_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    entity: Mapped["Entity | None"] = relationship(back_populates="quality_logs")


# ── Enterprise Oversight Layer ────────────────────────────────────────────────


class EvalCase(Base):
    """
    A test question with expected themes used to measure whether the intelligence
    layer is improving over time. Part of the EVALS component.

    expected_themes is a list of topics/facts the answer should cover
    (e.g. ["pricing range", "location context", "comparable deals"]).
    Claude acts as judge and scores how many themes were addressed.
    """
    __tablename__ = "eval_cases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_themes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    intent_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Minimum acceptable judge score [0.0, 1.0]; default 0.7 = "good answer"
    min_expected_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    results: Mapped[list["EvalResult"]] = relationship(
        back_populates="eval_case", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_eval_cases_active", "is_active"),
    )


class EvalRun(Base):
    """
    One complete evaluation run across all active EvalCases.
    delta_from_last tracks improvement: positive = getting better.
    """
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    triggered_by: Mapped[str] = mapped_column(String(100), nullable=False)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    cases_run: Mapped[int] = mapped_column(nullable=False, default=0)
    cases_passed: Mapped[int] = mapped_column(nullable=False, default=0)
    # Average judge score across all cases, normalised [0.0, 1.0]
    avg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Positive = improvement vs previous run; None = first run
    delta_from_last: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    results: Mapped[list["EvalResult"]] = relationship(
        back_populates="eval_run", cascade="all, delete-orphan"
    )


class EvalResult(Base):
    """Individual result for one EvalCase in one EvalRun."""
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    eval_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("eval_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    eval_run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actual_answer: Mapped[str] = mapped_column(Text, nullable=False)
    # Normalised judge score [0.0, 1.0]
    judge_score: Mapped[float] = mapped_column(Float, nullable=False)
    judge_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_themes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    eval_case: Mapped["EvalCase"] = relationship(back_populates="results")
    eval_run: Mapped["EvalRun"] = relationship(back_populates="results")

    __table_args__ = (
        Index("ix_eval_results_case_run", "eval_case_id", "eval_run_id"),
    )


class PolicyRule(Base):
    """
    Stored policy rules for the Policy Engine.

    These are higher-level guardrails than Rules (which shape context retrieval).
    PolicyRules gate the final response — they can block, warn, or flag.

    Example: enforce a pricing floor so the system never outputs a quote below
    a configured minimum value without a human override.
    """
    __tablename__ = "policy_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Matching condition — see PolicyEngine._matches() for supported keys
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # block | warn | flag
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="warn")
    # Message shown when the policy fires
    violation_message: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional guidance on how to fix the issue
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fire_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_policy_rules_active", "is_active"),
        Index("ix_policy_rules_severity", "severity"),
    )
