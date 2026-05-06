from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_context_engine
from src.config import Settings, get_settings
from src.database import get_db
from src.models.schemas import (
    ContextQuery,
    ContextResponse,
    EntityContext,
    ICPProfile,
    PricingContext,
    PricingQuery,
    QualityReport,
    RelationshipMap,
)
from src.reasoning.context_engine import ContextEngine

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/query", response_model=ContextResponse)
async def query_context(
    body: ContextQuery,
    engine: ContextEngine = Depends(get_context_engine),
) -> ContextResponse:
    """Answer a natural language question about the enterprise."""
    return await engine.query(
        question=body.question,
        entity_id=body.entity_id,
        context_type=body.context_type,
        max_context_entities=body.max_context_entities,
    )


@router.get("/entity/{identifier}", response_model=EntityContext)
async def get_entity_context(
    identifier: str,
    engine: ContextEngine = Depends(get_context_engine),
) -> EntityContext:
    """Full profile: entity + all relationships + decision history."""
    ctx = await engine.get_entity_context(identifier)
    if ctx is None:
        raise HTTPException(status_code=404, detail=f"Entity '{identifier}' not found")
    return ctx


@router.get("/icp", response_model=ICPProfile)
async def get_icp(
    engine: ContextEngine = Depends(get_context_engine),
) -> ICPProfile:
    """Learned Ideal Customer Profile based on approved leads and closed deals."""
    return await engine.get_icp()


@router.post("/pricing", response_model=PricingContext)
async def get_pricing(
    body: PricingQuery,
    engine: ContextEngine = Depends(get_context_engine),
) -> PricingContext:
    """Historical pricing patterns for a given seat count and location."""
    return await engine.get_pricing_context(body)


@router.get("/relationships/{entity_id}", response_model=RelationshipMap)
async def get_relationship_map(
    entity_id: str,
    depth: int = 2,
    engine: ContextEngine = Depends(get_context_engine),
) -> RelationshipMap:
    """Relationship graph centred on an entity, up to `depth` hops."""
    if depth > 3:
        raise HTTPException(status_code=400, detail="depth must be ≤ 3")
    result = await engine.get_relationship_map(entity_id, depth=depth)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
    return result


@router.get("/quality", response_model=QualityReport)
async def run_quality_check(
    engine: ContextEngine = Depends(get_context_engine),
) -> QualityReport:
    """Run data quality checks and return anomalies."""
    return await engine.run_quality_check()


@router.post("/feedback", response_model=dict, status_code=201)
async def submit_response_feedback(
    body: dict,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Submit feedback on a context response — the direct RLHF signal.

    When Claude gives a wrong, incomplete, or misaligned answer, call this endpoint
    with the original question, what Claude said, and what the correct answer should be.
    The system stores this as a negative/corrective decision and immediately uses it
    as a few-shot example to steer future responses.

    Body:
    ```json
    {
      "question": "What's our pricing for 100 seats in Gurugram?",
      "claude_answer": "Based on historical data, standard enterprise pricing is $8,000-10,000 per unit.",
      "correct_answer": "Our current standard is $12,000-14,000 per unit. The 8k figure is outdated.",
      "corrected_by": "admin",
      "feedback_type": "correction"
    }
    ```
    feedback_type: correction | missing_context | wrong_rule_applied | hallucination
    """
    import uuid as _uuid
    from src.models.entities import ExpertDecision

    question = body.get("question", "")
    claude_answer = body.get("claude_answer", "")
    correct_answer = body.get("correct_answer", "")
    corrected_by = body.get("corrected_by", "team")
    feedback_type = body.get("feedback_type", "correction")

    if not question or not correct_answer:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="question and correct_answer are required")

    # Store as an expert decision with negative signal on the old answer
    # and the corrected answer as the human_reasoning (this becomes a future few-shot example)
    decision = ExpertDecision(
        id=str(_uuid.uuid4()),
        decision_type="response_correction",
        actor=corrected_by,
        context_snapshot={
            "question": question,
            "claude_answer": claude_answer,
            "feedback_type": feedback_type,
        },
        human_action=f"Corrected Claude response [{feedback_type}]",
        human_reasoning=correct_answer,
        outcome="correction_recorded",
        feedback_signal="negative",  # the old answer; positive signal is on the correction
    )
    db.add(decision)

    # Also store the correction itself as a positive example
    correction_decision = ExpertDecision(
        id=str(_uuid.uuid4()),
        decision_type="response_correction",
        actor=corrected_by,
        context_snapshot={
            "question": question,
            "correct_answer": correct_answer,
            "feedback_type": feedback_type,
        },
        human_action=f"Correct answer provided [{feedback_type}]",
        human_reasoning=correct_answer,
        outcome="applied",
        feedback_signal="positive",  # this becomes a few-shot RLHF example
    )
    db.add(correction_decision)
    await db.flush()

    return {
        "status": "recorded",
        "message": "Correction stored. Claude will use this as a few-shot example in future responses.",
        "decision_id": correction_decision.id,
    }


@router.post("/learn", response_model=dict)
async def run_self_improvement(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Trigger the self-improvement evaluation loop.

    What this does:
    1. Recalibrates entity confidence scores from recorded decision outcomes
    2. Detects ICP drift (are your recent approvals shifting away from historical patterns?)
    3. Flags entities not updated in 30+ days as stale

    Run this after a batch of decisions have had their outcomes recorded, or weekly.
    """
    from src.reasoning.evaluator import SelfImprovementEvaluator
    evaluator = SelfImprovementEvaluator(settings, db)
    return await evaluator.run()


@router.post("/icp/refresh", response_model=ICPProfile)
async def refresh_icp(
    engine: ContextEngine = Depends(get_context_engine),
) -> ICPProfile:
    """
    Force a fresh ICP derivation from all decision history.
    Call this after recording a significant batch of lead approvals or deal closures.
    """
    from src.reasoning.icp_learner import ICPLearner
    learner = ICPLearner(engine.settings, engine.db)
    return await learner.refresh()
