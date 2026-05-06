"""
Pydantic v2 request/response schemas for the Context Engine API.
Kept separate from SQLAlchemy models to avoid coupling the API contract to DB internals.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    ContentType,
    DataSource,
    DecisionActor,
    DecisionType,
    EntityType,
    QualityCheckType,
    RelationshipType,
)


# ── Base ──────────────────────────────────────────────────────────────────────

class ContextBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ── Entity ────────────────────────────────────────────────────────────────────

class EntityCreate(ContextBase):
    type: EntityType
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    source: DataSource
    source_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    pii_fields: list[str] = Field(default_factory=list)


class EntityUpdate(ContextBase):
    name: str | None = None
    attributes: dict[str, Any] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    is_active: bool | None = None


class EntityRead(ContextBase):
    id: str
    type: str
    name: str
    attributes: dict[str, Any]
    source: str
    source_id: str | None
    confidence: float
    pii_fields: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Relationship ──────────────────────────────────────────────────────────────

class RelationshipCreate(ContextBase):
    from_entity_id: str
    to_entity_id: str
    relationship_type: RelationshipType
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: DataSource


class RelationshipRead(ContextBase):
    id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    metadata: dict[str, Any] = Field(validation_alias="rel_metadata", default_factory=dict)
    confidence: float
    source: str
    is_active: bool
    created_at: datetime


# ── Expert Decision ───────────────────────────────────────────────────────────

class ExpertDecisionCreate(ContextBase):
    decision_type: DecisionType
    actor: DecisionActor
    context_snapshot: dict[str, Any] = Field(
        description="Full context at decision time — do not pass a reference, pass the data"
    )
    human_action: str
    human_reasoning: str | None = None
    primary_entity_id: str | None = None


class ExpertDecisionRead(ContextBase):
    id: str
    decision_type: str
    actor: str
    human_action: str
    human_reasoning: str | None
    outcome: str | None
    feedback_signal: str | None
    primary_entity_id: str | None
    timestamp: datetime


class OutcomeUpdate(ContextBase):
    outcome: str
    outcome_notes: str | None = None
    feedback_signal: str = Field(description="positive / negative / neutral")


# ── Context Query ─────────────────────────────────────────────────────────────

class ContextQuery(ContextBase):
    question: str = Field(min_length=3, max_length=2000)
    entity_id: str | None = None
    context_type: str | None = None
    # Max number of entity contexts to include in reasoning
    max_context_entities: int = Field(default=10, ge=1, le=50)


class SourceCitation(ContextBase):
    entity_id: str
    entity_name: str
    entity_type: str
    source: str
    relevance_score: float


class ContextResponse(ContextBase):
    answer: str
    citations: list[SourceCitation]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_trace: str | None = None
    context_entities_used: int
    # Enterprise Oversight additions
    intent: str | None = None                      # classified query intent
    policy_violations: list[str] = Field(default_factory=list)  # fired policy names


# ── Entity Context (full profile) ─────────────────────────────────────────────

class EntityContext(ContextBase):
    entity: EntityRead
    relationships: list[RelationshipRead]
    related_entities: list[EntityRead]
    recent_decisions: list[ExpertDecisionRead]
    quality_flags: list[str]
    context_summary: str


# ── ICP Profile ───────────────────────────────────────────────────────────────

class ICPProfile(ContextBase):
    description: str
    industries: list[str]
    company_size_range: dict[str, int]  # {min: 50, max: 500}
    geographies: list[str]
    seat_range: dict[str, int]          # {min: 20, max: 200}
    signals: list[str]                  # "recently funded", "expanding NCR", etc.
    based_on_decisions: int
    confidence: float
    generated_at: datetime


# ── Pricing Context ───────────────────────────────────────────────────────────

class PricingQuery(ContextBase):
    seats: int = Field(ge=1)
    location: str
    building_name: str | None = None


class PricingDataPoint(ContextBase):
    deal_id: str
    client_name: str
    seats: int
    location: str
    price_per_seat: float | None
    total_value: float | None
    closed_at: datetime | None


class PricingContext(ContextBase):
    recommended_range: dict[str, float]   # {min, max, median}
    comparable_deals: list[PricingDataPoint]
    pricing_notes: str
    confidence: float


# ── Relationship Map ──────────────────────────────────────────────────────────

class RelationshipMapNode(ContextBase):
    entity: EntityRead
    relationship_to_root: str
    depth: int


class RelationshipMap(ContextBase):
    root_entity: EntityRead
    nodes: list[RelationshipMapNode]
    edges: list[RelationshipRead]


# ── Quality Report ────────────────────────────────────────────────────────────

class QualityIssue(ContextBase):
    entity_id: str | None
    entity_name: str | None
    check_type: str
    description: str
    severity: str  # critical / warning / info


class QualityReport(ContextBase):
    total_entities: int
    total_relationships: int
    issues: list[QualityIssue]
    overall_health_score: float = Field(ge=0.0, le=1.0)
    generated_at: datetime


# ── Rules ─────────────────────────────────────────────────────────────────────

class RuleCreate(ContextBase):
    name: str = Field(min_length=3, max_length=500)
    reasoning: str = Field(
        min_length=10,
        description="Why does this rule exist? What expert judgment does it encode?"
    )
    condition: dict[str, Any] = Field(
        description="When does this rule apply? Keys: entity_type, field_name, field_value, "
                    "industry, location, deal_seats_gte, confidence_lte, source"
    )
    action: dict[str, Any] = Field(
        description="What should the system do? Keys: prefer_source, override_field, "
                    "priority, flag_for, icp_signal, apply_pricing_tier, note"
    )
    created_by: str
    source_decision_id: str | None = None
    source_conflict_id: str | None = None


class RuleRead(ContextBase):
    id: str
    name: str
    reasoning: str
    condition: dict[str, Any]
    action: dict[str, Any]
    created_by: str
    source_decision_id: str | None
    source_conflict_id: str | None
    is_active: bool
    fire_count: int
    created_at: datetime
    updated_at: datetime


class RuleUpdate(ContextBase):
    name: str | None = None
    reasoning: str | None = None
    condition: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    is_active: bool | None = None


# ── Data Conflicts ────────────────────────────────────────────────────────────

class ConflictCreate(ContextBase):
    entity_id: str
    field_name: str
    value_a: str
    source_a: str
    value_b: str
    source_b: str


class ConflictResolve(ContextBase):
    resolved_value: str
    resolved_by: str
    resolution_reasoning: str = Field(
        min_length=10,
        description="Why is this the correct value? This reasoning can be encoded as a rule."
    )
    create_rule: bool = Field(
        default=False,
        description="If true, automatically encode the resolution reasoning as a Rule "
                    "so future conflicts of this type resolve automatically."
    )


class ConflictRead(ContextBase):
    id: str
    entity_id: str
    field_name: str
    value_a: str
    source_a: str
    value_b: str
    source_b: str
    status: str
    resolved_value: str | None
    resolved_by: str | None
    resolution_reasoning: str | None
    generated_rule_id: str | None
    detected_at: datetime
    resolved_at: datetime | None


# ── Eval Cases / Runs ─────────────────────────────────────────────────────────

class EvalCaseCreate(ContextBase):
    question: str = Field(min_length=5, max_length=2000)
    expected_themes: list[str] = Field(
        min_length=1,
        description="Topics or facts the answer should cover. Claude judges coverage.",
    )
    intent_type: str | None = None
    min_expected_score: float = Field(default=0.7, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    created_by: str


class EvalCaseRead(ContextBase):
    id: str
    question: str
    expected_themes: list[str]
    intent_type: str | None
    min_expected_score: float
    tags: list[str]
    is_active: bool
    created_by: str
    created_at: datetime


class EvalResultRead(ContextBase):
    id: str
    eval_case_id: str
    eval_run_id: str
    actual_answer: str
    judge_score: float
    judge_notes: str | None
    missing_themes: list[str]
    passed: bool
    evaluated_at: datetime


class EvalRunRead(ContextBase):
    id: str
    triggered_by: str
    run_at: datetime
    cases_run: int
    cases_passed: int
    avg_score: float
    delta_from_last: float | None
    notes: str | None


# ── Policy Rules ───────────────────────────────────────────────────────────────

class PolicyRuleCreate(ContextBase):
    name: str = Field(min_length=3, max_length=500)
    description: str = Field(
        min_length=10,
        description="What does this policy enforce and why?",
    )
    condition: dict[str, Any] = Field(
        description=(
            "Matching condition. Supported keys:\n"
            "  question_contains: str — substring match on the question\n"
            "  answer_contains: str — substring match on the answer\n"
            "  answer_number_below: {threshold: float} — fires when any number in the "
            "answer is below this threshold (use for price-floor enforcement)"
        )
    )
    severity: str = Field(
        default="warn",
        description="block | warn | flag. block prevents the response from returning.",
    )
    violation_message: str = Field(
        description="Message shown to the caller when this policy fires."
    )
    remediation: str | None = None
    created_by: str


class PolicyRuleRead(ContextBase):
    id: str
    name: str
    description: str
    condition: dict[str, Any]
    severity: str
    violation_message: str
    remediation: str | None
    is_active: bool
    fire_count: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class PolicyRuleUpdate(ContextBase):
    name: str | None = None
    description: str | None = None
    condition: dict[str, Any] | None = None
    severity: str | None = None
    violation_message: str | None = None
    remediation: str | None = None
    is_active: bool | None = None


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(ContextBase):
    status: str
    db_connected: bool
    entity_count: int
    relationship_count: int
    last_ingestion: datetime | None
    version: str = "0.1.0"
