"""
Tests for hr_dashboard pure helper functions.
No DB mocking needed — these are unit tests of business logic.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

from src.api.routes.hr_dashboard import (
    PIPELINE_STAGES,
    _build_pipeline_counts,
    _config_defaults,
    _next_stage,
)


def test_pipeline_returns_stage_counts():
    rows = [
        MagicMock(stage="applied"),
        MagicMock(stage="applied"),
        MagicMock(stage="pre_screening"),
    ]
    counts = _build_pipeline_counts(rows)
    assert counts["applied"] == 2
    assert counts["pre_screening"] == 1


def test_unknown_stage_ignored_in_pipeline_counts():
    from src.api.routes.hr_dashboard import _build_pipeline_counts
    rows = [MagicMock(stage="applied", cnt=1), MagicMock(stage="legacy_hold", cnt=1)]
    counts = _build_pipeline_counts(rows)
    assert "legacy_hold" not in counts
    assert counts["applied"] == 1


def test_invalid_stage_rejected():
    from src.api.routes.hr_dashboard import PIPELINE_STAGES
    invalid_stage = "nonexistent_stage"
    assert invalid_stage not in PIPELINE_STAGES


def test_all_stages_present_in_pipeline():
    counts = _build_pipeline_counts([])
    for stage in PIPELINE_STAGES:
        assert stage in counts
        assert counts[stage] == 0


def test_config_defaults_returned():
    defaults = _config_defaults()
    assert "hr_resume_score_threshold" in defaults
    assert "hiring_email" in defaults
    assert "frontend_url" in defaults


def test_advance_stage_mapping():
    assert _next_stage("applied") == "pre_screening"
    assert _next_stage("pre_screened") == "test_invited"
    assert _next_stage("screened") == "hr_approved"
    assert _next_stage("hr_approved") == "shortlisted"


def test_advance_stage_raises_for_invalid():
    with pytest.raises(ValueError):
        _next_stage("rejected")
