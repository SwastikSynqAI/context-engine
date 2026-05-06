"""
Screen scorer — scores the 5 pre-screen Q&A pairs using Claude Haiku.

Each question scored 0-20. Total possible: 100.
Returns ScreenScore from src.engines.hr.models.

Design mirrors resume_scorer — injected client, tenacity retry, parse_error fallback.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.engines.hr.models import QuestionScore, ScreenScore

logger = logging.getLogger(__name__)

CLAUDE_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_SCORING_PROMPT = """You are an experienced HR professional at YourCompany, evaluating a candidate's pre-screening answers.

Role: {role_display}
Number of questions: 5, each scored 0-20 (total 100)

Scoring criteria per question:
- 17-20: Excellent — specific, quantified, shows deep experience
- 13-16: Good — clear and relevant, some specifics
- 9-12: Average — generic but acceptable
- 5-8: Weak — vague or lacking substance
- 0-4: Very weak or irrelevant

Q&A pairs:
{qa_text}

Respond ONLY with valid JSON in this exact format:
{{
  "overall": <sum of question scores, 0-100>,
  "question_scores": [
    {{"question_index": 0, "score": <0-20>, "notes": "<one line>"}},
    {{"question_index": 1, "score": <0-20>, "notes": "<one line>"}},
    {{"question_index": 2, "score": <0-20>, "notes": "<one line>"}},
    {{"question_index": 3, "score": <0-20>, "notes": "<one line>"}},
    {{"question_index": 4, "score": <0-20>, "notes": "<one line>"}}
  ],
  "strong_signals": ["<signal 1>", "<signal 2>"],
  "role": "{role}"
}}"""


class ScreenScorer:
    def __init__(self, *, client: Any) -> None:
        self._client = client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def score(self, *, role: str, qa_pairs: list[dict]) -> ScreenScore:
        """Score 5 pre-screen Q&A pairs. Returns ScreenScore."""
        role_display = role.replace("_", " ").title()
        qa_text = "\n\n".join(
            f"Q{i+1}: {pair['question']}\nA: {pair['answer']}"
            for i, pair in enumerate(qa_pairs)
        )
        prompt = _SCORING_PROMPT.format(
            role_display=role_display,
            role=role,
            qa_text=qa_text,
        )
        message = await self._client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        return self._parse_response(raw_text, role=role)

    def _parse_response(self, raw_text: str, *, role: str) -> ScreenScore:
        try:
            data = json.loads(raw_text)
            return ScreenScore(
                overall=float(data.get("overall", 0)),
                question_scores=[
                    QuestionScore(
                        question_index=qs["question_index"],
                        score=float(qs["score"]),
                        notes=qs.get("notes", ""),
                    )
                    for qs in data.get("question_scores", [])
                ],
                role=role,
                strong_signals=data.get("strong_signals", []),
            )
        except Exception as exc:
            logger.error("Screen scorer parse error: %s | raw: %.200s", exc, raw_text)
            return ScreenScore(
                overall=0.0,
                question_scores=[],
                role=role,
                strong_signals=[f"parse_error: {exc}"],
            )


def make_screen_scorer() -> ScreenScorer:
    import anthropic
    from src.config import get_settings
    client = anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)
    return ScreenScorer(client=client)
