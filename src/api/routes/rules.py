"""
Rules API — create and manage human-encoded expert rules.

This is the "doctor adds a rule" step from the Dialect demo:
  1. Human sees a pattern or makes a judgment call
  2. They POST /rules to encode it as a condition + action + reasoning
  3. The system applies it to every future query automatically
  4. GET /rules/evaluate lets you test a rule against a specific entity before saving
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.responses import Response
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.entities import DataConflict, Rule
from src.models.schemas import (
    ConflictCreate,
    ConflictRead,
    ConflictResolve,
    RuleCreate,
    RuleRead,
    RuleUpdate,
)
from src.reasoning.rules_engine import RulesEngine

router = APIRouter(prefix="/rules", tags=["rules"])


# ── Rules CRUD ────────────────────────────────────────────────────────────────

@router.post("", response_model=RuleRead, status_code=201)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db),
) -> RuleRead:
    """
    Encode a piece of expert reasoning as a reusable rule.

    Example — after Admin approves a BFSI lead and explains why:
    ```json
    {
      "name": "Priority: recently-funded BFSI companies",
      "reasoning": "These companies are expanding aggressively and have capital to spend. "
                   "NCR expansion is almost always on their roadmap within 6 months of funding.",
      "condition": {"industry": "bfsi", "field_name": "funded_recently", "field_value": "true"},
      "action": {"priority": "high", "icp_signal": "strong", "flag_for": "admin"},
      "created_by": "admin"
    }
    ```
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        name=body.name,
        reasoning=body.reasoning,
        condition=body.condition,
        action=body.action,
        created_by=body.created_by,
        source_decision_id=body.source_decision_id,
        source_conflict_id=body.source_conflict_id,
    )
    db.add(rule)
    await db.flush()
    return RuleRead.model_validate(rule)


@router.get("", response_model=list[RuleRead])
async def list_rules(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> list[RuleRead]:
    """List all rules, ordered by how often they've fired (most used first)."""
    query = select(Rule).order_by(Rule.fire_count.desc(), Rule.created_at.desc())
    if active_only:
        query = query.where(Rule.is_active == True)
    result = await db.execute(query)
    return [RuleRead.model_validate(r) for r in result.scalars().all()]


@router.get("/{rule_id}", response_model=RuleRead)
async def get_rule(rule_id: str, db: AsyncSession = Depends(get_db)) -> RuleRead:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return RuleRead.model_validate(rule)


@router.patch("/{rule_id}", response_model=RuleRead)
async def update_rule(
    rule_id: str,
    body: RuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> RuleRead:
    """Update a rule's condition, action, or active status."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    if body.name is not None:
        rule.name = body.name
    if body.reasoning is not None:
        rule.reasoning = body.reasoning
    if body.condition is not None:
        rule.condition = body.condition
    if body.action is not None:
        rule.action = body.action
    if body.is_active is not None:
        rule.is_active = body.is_active

    await db.flush()
    return RuleRead.model_validate(rule)


@router.delete("/{rule_id}")
async def deactivate_rule(rule_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Deactivate a rule (it stops firing but is preserved for audit history)."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    rule.is_active = False
    await db.flush()
    return Response(status_code=204)


@router.post("/evaluate", response_model=list[str])
async def evaluate_rules_against_entity(
    entity_attrs: dict,
    entity_type: str,
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """
    Test which active rules would fire against a given entity.
    Useful before adding an entity to check what rules apply.
    Returns a list of rule names that matched.
    """
    engine = RulesEngine(db)
    applied = await engine.evaluate_entity(entity_attrs, entity_type)
    return [app.rule.name for app in applied]


# ── Data Conflicts ────────────────────────────────────────────────────────────

conflicts_router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@conflicts_router.post("", response_model=ConflictRead, status_code=201)
async def flag_conflict(
    body: ConflictCreate,
    db: AsyncSession = Depends(get_db),
) -> ConflictRead:
    """
    Flag a data conflict: two sources disagree about the same field on the same entity.

    Example: HubSpot says Acme Corp has 150 employees, Google Sheets says 300.
    ```json
    {
      "entity_id": "...",
      "field_name": "headcount",
      "value_a": "150",
      "source_a": "hubspot",
      "value_b": "300",
      "source_b": "google_sheets"
    }
    ```
    """
    # Check entity exists
    from src.graph.entity_store import EntityStore
    store = EntityStore(db)
    entity = await store.get_entity_by_id(body.entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{body.entity_id}' not found")

    conflict = DataConflict(
        id=str(uuid.uuid4()),
        entity_id=body.entity_id,
        field_name=body.field_name,
        value_a=body.value_a,
        source_a=body.source_a,
        value_b=body.value_b,
        source_b=body.source_b,
        status="open",
    )
    db.add(conflict)
    await db.flush()
    return ConflictRead.model_validate(conflict)


@conflicts_router.get("", response_model=list[ConflictRead])
async def list_conflicts(
    status: str = "open",
    db: AsyncSession = Depends(get_db),
) -> list[ConflictRead]:
    """List conflicts. Default: open conflicts only."""
    query = select(DataConflict).order_by(DataConflict.detected_at.desc())
    if status != "all":
        query = query.where(DataConflict.status == status)
    result = await db.execute(query)
    return [ConflictRead.model_validate(c) for c in result.scalars().all()]


@conflicts_router.patch("/{conflict_id}/resolve", response_model=ConflictRead)
async def resolve_conflict(
    conflict_id: str,
    body: ConflictResolve,
    db: AsyncSession = Depends(get_db),
) -> ConflictRead:
    """
    Resolve a data conflict.

    If `create_rule=true`, the resolution reasoning is automatically encoded as a Rule
    so future conflicts of the same type resolve without human intervention.

    Example: "HubSpot headcount is always more accurate — they pull it from LinkedIn."
    → Creates rule: condition={field_name: headcount, sources_conflict: true}
                    action={prefer_source: hubspot}
    """
    result = await db.execute(
        select(DataConflict).where(DataConflict.id == conflict_id)
    )
    conflict = result.scalar_one_or_none()
    if not conflict:
        raise HTTPException(status_code=404, detail=f"Conflict '{conflict_id}' not found")
    if conflict.status == "resolved":
        raise HTTPException(status_code=400, detail="Conflict is already resolved")

    conflict.resolved_value = body.resolved_value
    conflict.resolved_by = body.resolved_by
    conflict.resolution_reasoning = body.resolution_reasoning
    conflict.status = "resolved"
    conflict.resolved_at = datetime.now(UTC)

    # Update the entity's attribute with the resolved value
    from src.graph.entity_store import EntityStore
    store = EntityStore(db)
    entity = await store.get_entity_by_id(conflict.entity_id)
    if entity:
        entity.attributes = {
            **entity.attributes,
            conflict.field_name: body.resolved_value,
        }
        await db.flush()

    # Optionally encode the reasoning as a permanent rule
    generated_rule_id = None
    if body.create_rule:
        # Infer which source to prefer from the resolved value
        preferred_source = (
            conflict.source_a if body.resolved_value == conflict.value_a
            else conflict.source_b
        )
        rule = Rule(
            id=str(uuid.uuid4()),
            name=f"Source preference: {conflict.field_name} ({preferred_source} wins)",
            reasoning=body.resolution_reasoning,
            condition={
                "field_name": conflict.field_name,
                "sources_conflict": True,
            },
            action={
                "prefer_source": preferred_source,
                "note": f"Resolved by {body.resolved_by}: {body.resolution_reasoning[:100]}",
            },
            created_by=body.resolved_by,
            source_conflict_id=conflict_id,
        )
        db.add(rule)
        await db.flush()
        generated_rule_id = rule.id
        conflict.generated_rule_id = generated_rule_id

    await db.flush()
    return ConflictRead.model_validate(conflict)


# conflicts_router is registered separately in main.py at /conflicts
