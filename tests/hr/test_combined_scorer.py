"""Unit tests for combined score calculation."""


def test_combined_score_resume_only():
    from src.engines.hr.scoring.combined_scorer import compute_combined_score
    score = compute_combined_score(resume_score=80.0, screen_score=None)
    assert score == 80.0


def test_combined_score_both():
    from src.engines.hr.scoring.combined_scorer import compute_combined_score
    # 80*0.4 + 70*0.6 = 32 + 42 = 74
    score = compute_combined_score(resume_score=80.0, screen_score=70.0)
    assert abs(score - 74.0) < 0.01


def test_combined_score_perfect():
    from src.engines.hr.scoring.combined_scorer import compute_combined_score
    score = compute_combined_score(resume_score=100.0, screen_score=100.0)
    assert score == 100.0


def test_combined_score_zero():
    from src.engines.hr.scoring.combined_scorer import compute_combined_score
    score = compute_combined_score(resume_score=0.0, screen_score=0.0)
    assert score == 0.0


def test_passes_screen_gate():
    from src.engines.hr.scoring.combined_scorer import passes_screen_gate
    assert passes_screen_gate(resume_score=76.0, threshold=75.0) is True
    assert passes_screen_gate(resume_score=74.9, threshold=75.0) is False
    assert passes_screen_gate(resume_score=75.0, threshold=75.0) is True


def test_shortlist_rank_order():
    from src.engines.hr.scoring.combined_scorer import rank_candidates
    candidates = [
        {"entity_id": "a", "resume_score": 80, "screen_score": 90},
        {"entity_id": "b", "resume_score": 90, "screen_score": 70},
        {"entity_id": "c", "resume_score": 85, "screen_score": 80},
    ]
    ranked = rank_candidates(candidates, top_n=2)
    assert len(ranked) == 2
    # c: 85*0.4 + 80*0.6 = 34+48 = 82
    # a: 80*0.4 + 90*0.6 = 32+54 = 86
    # b: 90*0.4 + 70*0.6 = 36+42 = 78
    assert ranked[0]["entity_id"] == "a"
    assert ranked[1]["entity_id"] == "c"
