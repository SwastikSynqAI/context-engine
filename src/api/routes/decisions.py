from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_decision_service
from src.models.schemas import ExpertDecisionCreate, ExpertDecisionRead, OutcomeUpdate
from src.reasoning.decision_capture import DecisionCaptureService

router = APIRouter(prefix="/context/decisions", tags=["decisions"])


@router.post("", response_model=ExpertDecisionRead, status_code=201)
async def capture_decision(
    body: ExpertDecisionCreate,
    service: DecisionCaptureService = Depends(get_decision_service),
) -> ExpertDecisionRead:
    """
    Record a human expert decision as training signal.
    Include the full context snapshot — not a reference to it.
    """
    return await service.capture(body)


@router.patch("/{decision_id}/outcome", response_model=ExpertDecisionRead)
async def record_outcome(
    decision_id: str,
    body: OutcomeUpdate,
    service: DecisionCaptureService = Depends(get_decision_service),
) -> ExpertDecisionRead:
    """Record the outcome of a previously captured decision."""
    result = await service.record_outcome(
        decision_id=decision_id,
        outcome=body.outcome,
        outcome_notes=body.outcome_notes,
        feedback_signal=body.feedback_signal,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found")
    return result
