"""
Evaluation Runner — measures whether the intelligence layer is improving.

Implements the EVALS component of Scale AI's Enterprise Oversight Layer.

Flow:
  1. Define EvalCases via POST /evals/cases (question + expected themes)
  2. POST /evals/run to trigger evaluation
  3. For each case, queries the context engine and sends the answer to Claude
     acting as judge — it scores coverage of expected_themes on a 1–10 scale
  4. Results stored in EvalRun + EvalResult records with pass/fail and delta
  5. Watch delta_from_last across runs: positive = RLHF corrections are working

This closes the oversight loop: POST /context/feedback corrections should
measurably drive up eval scores over time.
"""

from __future__ import annotations

import json
import logging
import uuid

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.entities import EvalCase, EvalResult, EvalRun
from src.models.schemas import EvalRunRead

logger = logging.getLogger(__name__)

_JUDGE_PROMPT = """\
You are an impartial evaluator for YourCompany's AI intelligence layer.

Question that was asked:
{question}

Expected themes the answer should cover:
{expected_themes}

Actual answer produced:
{actual_answer}

Score the actual answer on a scale of 1–10:
  10  — covers ALL expected themes with specific facts, cites sources, no hallucination
  7–9 — covers most themes, reasonably specific
  4–6 — partial coverage, missing key themes or too vague
  1–3 — misses most themes, generic, or factually wrong

Return JSON only (no markdown wrapper):
{{"score": <1-10>, "notes": "<one sentence explanation>", "missing_themes": ["<theme>", ...]}}
"""


class EvalRunner:
    """Runs all active EvalCases and stores scored results in a new EvalRun."""

    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        self.settings = settings
        self.db = db
        self._anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def run_all(self, triggered_by: str = "system") -> EvalRunRead:
        """Execute every active EvalCase and return a summary EvalRunRead."""
        result = await self.db.execute(
            select(EvalCase).where(EvalCase.is_active == True)
        )
        cases = list(result.scalars().all())

        if not cases:
            run = EvalRun(
                id=str(uuid.uuid4()),
                triggered_by=triggered_by,
                cases_run=0,
                cases_passed=0,
                avg_score=0.0,
                notes="No active eval cases. Add cases via POST /evals/cases.",
            )
            self.db.add(run)
            await self.db.flush()
            return EvalRunRead.model_validate(run)

        # Delta baseline: previous run's avg_score
        prev_result = await self.db.execute(
            select(EvalRun).order_by(EvalRun.run_at.desc()).limit(1)
        )
        prev_run = prev_result.scalar_one_or_none()
        prev_avg: float | None = prev_run.avg_score if prev_run else None

        run_id = str(uuid.uuid4())
        raw_scores: list[float] = []
        passed_count = 0

        # Lazy import to avoid circular dependency (context_engine imports schemas)
        from src.reasoning.context_engine import ContextEngine
        engine = ContextEngine(self.settings, self.db)

        for case in cases:
            score, notes, missing = await self._run_case(engine, case)
            normalised = score / 10.0
            case_passed = normalised >= case.min_expected_score
            if case_passed:
                passed_count += 1
            raw_scores.append(score)

            eval_result = EvalResult(
                id=str(uuid.uuid4()),
                eval_case_id=case.id,
                eval_run_id=run_id,
                actual_answer="(see notes)" if score == 0 else "",  # filled below
                judge_score=normalised,
                judge_notes=notes,
                missing_themes=missing,
                passed=case_passed,
            )
            self.db.add(eval_result)

        n = len(raw_scores)
        avg_score = (sum(raw_scores) / n / 10.0) if n else 0.0
        delta = round(avg_score - prev_avg, 4) if prev_avg is not None else None

        pass_pct = f"{passed_count}/{n} ({passed_count / n * 100:.0f}%)" if n else "0/0"
        trend = ""
        if delta is not None:
            trend = f" | delta vs last run: {delta:+.3f}"

        run = EvalRun(
            id=run_id,
            triggered_by=triggered_by,
            cases_run=n,
            cases_passed=passed_count,
            avg_score=round(avg_score, 4),
            delta_from_last=delta,
            notes=f"Pass rate: {pass_pct}{trend}",
        )
        self.db.add(run)
        await self.db.flush()

        logger.info(
            "Eval run %s complete — avg_score=%.3f delta=%s pass=%s",
            run_id[:8], avg_score, delta, pass_pct,
        )
        return EvalRunRead.model_validate(run)

    async def _run_case(
        self, engine, case: EvalCase
    ) -> tuple[float, str, list[str]]:
        """Query the engine for one case and judge the response."""
        try:
            response = await engine.query(question=case.question)
            actual_answer = response.answer
        except Exception as exc:
            logger.warning("Eval case %s — engine error: %s", case.id[:8], exc)
            return 0.0, f"Engine error: {exc}", list(case.expected_themes)

        return await self._judge(
            question=case.question,
            expected_themes=case.expected_themes,
            actual_answer=actual_answer,
        )

    async def _judge(
        self,
        question: str,
        expected_themes: list[str],
        actual_answer: str,
    ) -> tuple[float, str, list[str]]:
        """Ask Claude to score the response against the expected themes."""
        prompt = _JUDGE_PROMPT.format(
            question=question,
            expected_themes=", ".join(expected_themes),
            actual_answer=actual_answer[:2000],
        )
        try:
            message = self._anthropic.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            # Strip markdown fences if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return (
                float(data.get("score", 5)),
                data.get("notes", ""),
                data.get("missing_themes", []),
            )
        except Exception as exc:
            logger.warning("Judge call failed: %s", exc)
            return 5.0, f"Judge error: {exc}", []
