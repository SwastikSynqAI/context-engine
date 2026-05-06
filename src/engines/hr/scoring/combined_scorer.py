"""
Combined score calculation and shortlist ranking.

Formula: combined = resume_score * 0.4 + screen_score * 0.6
If screen_score is None (pre-screen not yet done): combined = resume_score
"""

from __future__ import annotations

RESUME_WEIGHT = 0.4
SCREEN_WEIGHT = 0.6


def compute_combined_score(
    *,
    resume_score: float,
    screen_score: float | None,
) -> float:
    """Return the weighted combined score, rounded to 2 decimal places."""
    if screen_score is None:
        return round(resume_score, 2)
    return round(resume_score * RESUME_WEIGHT + screen_score * SCREEN_WEIGHT, 2)


def passes_screen_gate(*, resume_score: float, threshold: float) -> bool:
    """Return True if resume_score meets or exceeds the threshold for pre-screening."""
    return resume_score >= threshold


def rank_candidates(
    candidates: list[dict],
    *,
    top_n: int | None = None,
) -> list[dict]:
    """
    Sort candidates by combined score descending.
    Each dict must have: entity_id, resume_score, screen_score (optional).
    Adds 'combined_score' key to each dict.
    """
    for c in candidates:
        c["combined_score"] = compute_combined_score(
            resume_score=c.get("resume_score", 0.0),
            screen_score=c.get("screen_score"),
        )
    ranked = sorted(candidates, key=lambda c: c["combined_score"], reverse=True)
    return ranked[:top_n] if top_n else ranked
