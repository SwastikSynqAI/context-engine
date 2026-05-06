"""
Evals API — define test cases and trigger evaluation runs.

This is the EVALS component of Scale AI's Enterprise Oversight Layer.

Workflow:
  1. POST /evals/cases — define a question + expected themes
  2. POST /evals/run  — trigger a full evaluation run (async-friendly; runs in-process)
  3. GET  /evals/runs — view run history and delta trends
  4. GET  /evals/runs/{run_id}/results — drill into per-case scores for a specific run

The delta_from_last field in each EvalRun is the key metric:
  - Positive delta → the RLHF feedback loop is working
  - Flat or negative → the system needs more corrections or new rules
"""

from __future__ import annotations

import uuid

from fastapi.responses import Response
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.database import get_db
from src.models.entities import EvalCase, EvalResult, EvalRun
from src.models.schemas import EvalCaseRead, EvalResultRead, EvalRunRead

router = APIRouter(prefix="/evals", tags=["evals"])


# ── Eval Cases ────────────────────────────────────────────────────────────────

@router.post("/cases", response_model=EvalCaseRead, status_code=201)
async def create_eval_case(
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> EvalCaseRead:
    """
    Define a test case for the evaluation framework.

    ```json
    {
      "question": "What's our standard pricing for 50 seats in Gurugram?",
      "expected_themes": ["price range per seat", "comparable deals", "location context"],
      "intent_type": "pricing_query",
      "min_expected_score": 0.7,
      "tags": ["pricing", "ncr"],
      "created_by": "admin"
    }
    ```

    The evaluator will run this question through the context engine and ask Claude
    to judge whether the answer covers all expected_themes.
    """
    question = body.get("question", "")
    expected_themes = body.get("expected_themes", [])
    if not question or not expected_themes:
        raise HTTPException(status_code=400, detail="question and expected_themes are required")

    case = EvalCase(
        id=str(uuid.uuid4()),
        question=question,
        expected_themes=expected_themes,
        intent_type=body.get("intent_type"),
        min_expected_score=float(body.get("min_expected_score", 0.7)),
        tags=body.get("tags", []),
        created_by=body.get("created_by", "team"),
    )
    db.add(case)
    await db.flush()
    return EvalCaseRead.model_validate(case)


@router.get("/cases", response_model=list[EvalCaseRead])
async def list_eval_cases(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> list[EvalCaseRead]:
    """List eval cases, newest first."""
    query = select(EvalCase).order_by(EvalCase.created_at.desc())
    if active_only:
        query = query.where(EvalCase.is_active == True)
    result = await db.execute(query)
    return [EvalCaseRead.model_validate(c) for c in result.scalars().all()]


@router.patch("/cases/{case_id}", response_model=EvalCaseRead)
async def update_eval_case(
    case_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> EvalCaseRead:
    """Update a case's question, themes, or active status."""
    result = await db.execute(select(EvalCase).where(EvalCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"EvalCase '{case_id}' not found")

    if "question" in body:
        case.question = body["question"]
    if "expected_themes" in body:
        case.expected_themes = body["expected_themes"]
    if "min_expected_score" in body:
        case.min_expected_score = float(body["min_expected_score"])
    if "tags" in body:
        case.tags = body["tags"]
    if "is_active" in body:
        case.is_active = bool(body["is_active"])

    await db.flush()
    return EvalCaseRead.model_validate(case)


@router.delete("/cases/{case_id}")
async def deactivate_eval_case(
    case_id: str, db: AsyncSession = Depends(get_db)
) -> Response:
    """Deactivate a case (preserves history)."""
    result = await db.execute(select(EvalCase).where(EvalCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"EvalCase '{case_id}' not found")
    case.is_active = False
    await db.flush()
    return Response(status_code=204)


# ── Eval Runs ─────────────────────────────────────────────────────────────────

@router.post("/run", response_model=EvalRunRead, status_code=201)
async def trigger_eval_run(
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EvalRunRead:
    """
    Run all active eval cases through the context engine and score them.

    Returns the EvalRun summary including:
    - avg_score: overall quality [0.0, 1.0]
    - delta_from_last: improvement vs previous run (positive = getting better)
    - cases_passed / cases_run: pass rate

    Watch delta_from_last after submitting corrections via POST /context/feedback —
    it should trend positive as the RLHF examples accumulate.
    """
    from src.evals.runner import EvalRunner
    triggered_by = body.get("triggered_by", "api")
    runner = EvalRunner(settings, db)
    return await runner.run_all(triggered_by=triggered_by)


@router.get("/runs", response_model=list[EvalRunRead])
async def list_eval_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[EvalRunRead]:
    """List the most recent evaluation runs, newest first."""
    result = await db.execute(
        select(EvalRun).order_by(EvalRun.run_at.desc()).limit(limit)
    )
    return [EvalRunRead.model_validate(r) for r in result.scalars().all()]


@router.get("/runs/{run_id}", response_model=EvalRunRead)
async def get_eval_run(run_id: str, db: AsyncSession = Depends(get_db)) -> EvalRunRead:
    result = await db.execute(select(EvalRun).where(EvalRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"EvalRun '{run_id}' not found")
    return EvalRunRead.model_validate(run)


@router.get("/runs/{run_id}/results", response_model=list[EvalResultRead])
async def get_eval_run_results(
    run_id: str, db: AsyncSession = Depends(get_db)
) -> list[EvalResultRead]:
    """
    Per-case scores for a specific run.
    Use this to see which questions are improving and which are still failing.
    """
    result = await db.execute(
        select(EvalResult)
        .where(EvalResult.eval_run_id == run_id)
        .order_by(EvalResult.judge_score.asc())  # failing cases first
    )
    return [EvalResultRead.model_validate(r) for r in result.scalars().all()]
