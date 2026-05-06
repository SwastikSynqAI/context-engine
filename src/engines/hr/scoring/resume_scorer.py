"""
Resume scorer — uses Claude Haiku to evaluate a resume against a role rubric.

Design:
- Stateless scorer class injected with an anthropic.AsyncAnthropic client.
- Never imports anthropic at module level so the file stays importable in tests
  that only want to mock the client.
- Returns ResumeScore (from src.engines.hr.models) — always has a breakdown,
  always has reasoning. No black box.
- On JSON parse error: returns score=0 with reasoning="parse_error:..." so
  the pipeline does not crash — admin is notified via activity log.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.engines.hr.models import ResumeScore
from src.engines.hr.rubric import get_rubric_for_role

logger = logging.getLogger(__name__)

CLAUDE_HAIKU_MODEL = "claude-haiku-4-5-20251001"



_ROLE_KEYWORDS: dict[str, list[str]] = {
    "bd_manager": ["sales", "business development", "crm", "b2b", "enterprise", "revenue", "pipeline",
                   "client", "negotiation", "deal", "target", "account", "closing", "bd"],
    "operations_manager": ["operations", "facility", "facilities", "vendor", "sla", "mep", "maintenance",
                           "hse", "housekeeping", "contract", "procurement", "compliance", "fm"],
    "marketing": ["marketing", "brand", "campaign", "digital", "seo", "social media", "content", "growth"],
    "finance": ["finance", "accounting", "gst", "tds", "p&l", "balance sheet", "audit", "budget", "erp"],
    "it": ["software", "developer", "python", "cloud", "aws", "azure", "devops", "network", "infrastructure"],
    "ai": ["machine learning", "deep learning", "nlp", "llm", "python", "tensorflow", "pytorch", "ai", "ml"],
    "hr": ["recruitment", "hr", "talent", "payroll", "onboarding", "performance", "compensation", "hris"],
}

_EXPERIENCE_PATTERNS = ["years", "yr", "yrs", "experience", "worked at", "employed"]
_EDUCATION_KEYWORDS = ["mba", "btech", "b.tech", "mtech", "m.tech", "bsc", "msc", "graduate",
                       "university", "college", "degree", "pgdm", "ca", "cma"]


def _keyword_score(resume_text: str, role: str) -> ResumeScore:
    """Heuristic keyword-based scorer used as fallback when Claude is unavailable."""
    text_lower = resume_text.lower()
    keywords = _ROLE_KEYWORDS.get(role, _ROLE_KEYWORDS["bd_manager"])

    keyword_hits = sum(1 for kw in keywords if kw in text_lower)
    keyword_score = min(40.0, (keyword_hits / max(len(keywords), 1)) * 40 * 2)

    exp_hits = sum(1 for p in _EXPERIENCE_PATTERNS if p in text_lower)
    experience_score = min(30.0, exp_hits * 6.0)

    edu_hits = sum(1 for kw in _EDUCATION_KEYWORDS if kw in text_lower)
    education_score = min(20.0, edu_hits * 7.0)

    answer_score = 10.0 if len(resume_text) > 500 else 5.0

    overall = round(keyword_score + experience_score + education_score + answer_score, 1)
    overall = min(overall, 85.0)  # Cap fallback at 85 — Claude can give higher

    green_flags = [f"Matched keyword: {kw}" for kw in keywords if kw in text_lower][:3]
    red_flags = ["Scored via keyword fallback (Claude unavailable — review manually)"]

    return ResumeScore(
        overall=overall,
        breakdown={
            "role_keywords": keyword_score,
            "experience_signals": experience_score,
            "education": education_score,
            "completeness": answer_score,
        },
        reasoning=f"Keyword fallback: {keyword_hits}/{len(keywords)} role keywords found. Manual review recommended.",
        green_flags=green_flags,
        red_flags=red_flags,
        role=role,
        auto_reject=overall < 20.0,
    )


class ResumeScorer:
    def __init__(self, *, client: Any) -> None:
        self._client = client

    async def score(
        self,
        *,
        resume_text: str,
        application_answer: str,
        role: str,
        role_salary_max: int,
    ) -> ResumeScore:
        """Score resume via Claude Haiku, falling back to keyword heuristic on failure."""
        try:
            return await self._score_claude(
                resume_text=resume_text,
                application_answer=application_answer,
                role=role,
                role_salary_max=role_salary_max,
            )
        except Exception as exc:
            logger.warning("Claude resume scoring failed (%s), using keyword fallback.", exc)
            return _keyword_score(resume_text, role)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def _score_claude(
        self,
        *,
        resume_text: str,
        application_answer: str,
        role: str,
        role_salary_max: int,
    ) -> ResumeScore:
        rubric = get_rubric_for_role(role)
        prompt = rubric.build_scoring_prompt(
            resume_text=resume_text or "(no resume provided)",
            application_answer=application_answer or "(no answer provided)",
            role_salary_max=role_salary_max,
        )
        message = await self._client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        return self._parse_response(raw_text, role=role)

    def _parse_response(self, raw_text: str, *, role: str) -> ResumeScore:
        try:
            data = json.loads(raw_text)
            return ResumeScore(
                overall=float(data.get("overall", 0)),
                breakdown={k: float(v) for k, v in data.get("breakdown", {}).items()},
                reasoning=data.get("reasoning", ""),
                green_flags=data.get("green_flags", []),
                red_flags=data.get("red_flags", []),
                role=role,
                auto_reject=bool(data.get("auto_reject", False)),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse Claude scoring response: %s | raw: %.200s", exc, raw_text)
            return ResumeScore(
                overall=0.0,
                breakdown={},
                reasoning=f"parse_error: {exc}",
                green_flags=[],
                red_flags=["Scoring failed — admin review required"],
                role=role,
                auto_reject=False,
            )


def make_resume_scorer() -> ResumeScorer:
    import anthropic
    from src.config import get_settings
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return ResumeScorer(client=client)
