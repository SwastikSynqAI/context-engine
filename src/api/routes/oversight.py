"""
Oversight API — manage stored policy rules.

This is the POLICY component of Scale AI's Enterprise Oversight Layer.

PolicyRules are different from Rules (which shape context retrieval).
PolicyRules gate the final response:
  - block: prevents the response from being returned (PII, critical violations)
  - warn:  appends a ⚠️ disclaimer to the response
  - flag:  logs the violation silently; response unchanged

Built-in policies (always active, no DB required):
  - NoPIIInResponse     — blocks responses containing email or phone numbers
  - HallucinationRisk   — warns when no entity context was used
  - LowConfidenceDisclaimer — appends caveat when confidence < 50%

Use this API to add custom business policies on top of the built-ins, e.g.:
  - Never quote below the configured minimum price without a flag
  - Always warn when answering questions about a specific sensitive client
  - Block any response that mentions a competitor by name
"""

from __future__ import annotations

import uuid

from fastapi.responses import Response
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.entities import PolicyRule
from src.models.schemas import PolicyRuleCreate, PolicyRuleRead, PolicyRuleUpdate

router = APIRouter(prefix="/oversight", tags=["oversight"])

_VALID_SEVERITIES = {"block", "warn", "flag"}


@router.post("/policies", response_model=PolicyRuleRead, status_code=201)
async def create_policy(
    body: PolicyRuleCreate,
    db: AsyncSession = Depends(get_db),
) -> PolicyRuleRead:
    """
    Create a stored policy rule.

    Example — pricing floor enforcement:
    ```json
    {
      "name": "Pricing floor: never quote below minimum",
      "description": "Any response quoting below configured minimum should be flagged.",
      "condition": {
        "question_contains": "price",
        "answer_number_below": {"threshold": 8000}
      },
      "severity": "warn",
      "violation_message": "Quote appears below the configured price floor. Verify with Admin.",
      "created_by": "admin"
    }
    ```

    Example — sensitive client guard:
    ```json
    {
      "name": "Sensitive client: Acme Corp",
      "description": "Responses about Acme Corp should always carry a confidentiality note.",
      "condition": {"answer_contains": "Acme Corp"},
      "severity": "warn",
      "violation_message": "This response concerns a confidential client. Do not share externally.",
      "created_by": "admin"
    }
    ```
    """
    if body.severity not in _VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=f"severity must be one of: {', '.join(sorted(_VALID_SEVERITIES))}",
        )

    rule = PolicyRule(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        condition=body.condition,
        severity=body.severity,
        violation_message=body.violation_message,
        remediation=body.remediation,
        created_by=body.created_by,
    )
    db.add(rule)
    await db.flush()
    return PolicyRuleRead.model_validate(rule)


@router.get("/policies", response_model=list[PolicyRuleRead])
async def list_policies(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> list[PolicyRuleRead]:
    """List all policy rules, sorted by fire_count (most triggered first)."""
    query = select(PolicyRule).order_by(PolicyRule.fire_count.desc(), PolicyRule.created_at.desc())
    if active_only:
        query = query.where(PolicyRule.is_active == True)
    result = await db.execute(query)
    return [PolicyRuleRead.model_validate(r) for r in result.scalars().all()]


@router.get("/policies/{policy_id}", response_model=PolicyRuleRead)
async def get_policy(
    policy_id: str, db: AsyncSession = Depends(get_db)
) -> PolicyRuleRead:
    result = await db.execute(select(PolicyRule).where(PolicyRule.id == policy_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return PolicyRuleRead.model_validate(rule)


@router.patch("/policies/{policy_id}", response_model=PolicyRuleRead)
async def update_policy(
    policy_id: str,
    body: PolicyRuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> PolicyRuleRead:
    """Update condition, severity, message, or active status."""
    result = await db.execute(select(PolicyRule).where(PolicyRule.id == policy_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")

    if body.name is not None:
        rule.name = body.name
    if body.description is not None:
        rule.description = body.description
    if body.condition is not None:
        rule.condition = body.condition
    if body.severity is not None:
        if body.severity not in _VALID_SEVERITIES:
            raise HTTPException(status_code=400, detail=f"severity must be one of: {_VALID_SEVERITIES}")
        rule.severity = body.severity
    if body.violation_message is not None:
        rule.violation_message = body.violation_message
    if body.remediation is not None:
        rule.remediation = body.remediation
    if body.is_active is not None:
        rule.is_active = body.is_active

    await db.flush()
    return PolicyRuleRead.model_validate(rule)


@router.delete("/policies/{policy_id}")
async def deactivate_policy(
    policy_id: str, db: AsyncSession = Depends(get_db)
) -> Response:
    """Deactivate a policy (preserves fire history)."""
    result = await db.execute(select(PolicyRule).where(PolicyRule.id == policy_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    rule.is_active = False
    await db.flush()
    return Response(status_code=204)


@router.get("/summary", response_model=dict)
async def oversight_summary(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Overview of the Enterprise Oversight Layer:
    active policies, recent policy violations, and eval run trend.
    """
    from sqlalchemy import func
    from src.models.entities import EvalRun

    # Active policy count by severity
    result = await db.execute(
        select(PolicyRule.severity, func.count(PolicyRule.id).label("count"))
        .where(PolicyRule.is_active == True)
        .group_by(PolicyRule.severity)
    )
    policy_counts = {row.severity: row.count for row in result.all()}

    # Top firing policies
    result = await db.execute(
        select(PolicyRule)
        .where(PolicyRule.fire_count > 0)
        .order_by(PolicyRule.fire_count.desc())
        .limit(5)
    )
    top_policies = [
        {"name": r.name, "severity": r.severity, "fire_count": r.fire_count}
        for r in result.scalars().all()
    ]

    # Last 3 eval runs for trend
    result = await db.execute(
        select(EvalRun).order_by(EvalRun.run_at.desc()).limit(3)
    )
    recent_runs = [
        {
            "run_at": r.run_at.isoformat(),
            "avg_score": r.avg_score,
            "delta_from_last": r.delta_from_last,
            "pass_rate": f"{r.cases_passed}/{r.cases_run}",
        }
        for r in result.scalars().all()
    ]

    return {
        "active_policies": policy_counts,
        "top_firing_policies": top_policies,
        "recent_eval_runs": recent_runs,
        "built_in_policies": [
            "NoPIIInResponse (block)",
            "HallucinationRisk (warn)",
            "LowConfidenceDisclaimer (warn)",
        ],
    }
