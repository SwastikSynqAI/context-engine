"""
Application answer scorer — fast, heuristic, no AI call needed.

Runs before the resume scorer. If auto_reject is True, the candidate is
rejected immediately and no Claude call is made (saves cost + time).

Auto-reject conditions:
- Blank or whitespace-only answer
- Answer under 10 words (signals disengagement)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnswerScoreResult:
    auto_reject: bool
    rejection_reason: str | None  # "blank_answer" | "answer_too_short" | None
    word_count: int


def score_answer(answer: str | None) -> AnswerScoreResult:
    """
    Evaluate a free-text application answer.
    Returns AnswerScoreResult with auto_reject flag.
    """
    if answer is None or answer.strip() == "":
        return AnswerScoreResult(
            auto_reject=True,
            rejection_reason="blank_answer",
            word_count=0,
        )

    words = answer.split()
    word_count = len(words)

    if word_count < 10:
        return AnswerScoreResult(
            auto_reject=True,
            rejection_reason="answer_too_short",
            word_count=word_count,
        )

    return AnswerScoreResult(
        auto_reject=False,
        rejection_reason=None,
        word_count=word_count,
    )
