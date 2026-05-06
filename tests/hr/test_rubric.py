"""Unit tests for HR scoring rubrics."""
import pytest


def test_bd_manager_rubric_weights_sum_to_100():
    from src.engines.hr.rubric import BDManagerRubric
    r = BDManagerRubric()
    total = sum(r.weights.values())
    assert abs(total - 100.0) < 0.01, f"Weights sum to {total}, not 100"


def test_operations_manager_rubric_weights_sum_to_100():
    from src.engines.hr.rubric import OperationsManagerRubric
    r = OperationsManagerRubric()
    total = sum(r.weights.values())
    assert abs(total - 100.0) < 0.01


def test_bd_manager_rubric_has_required_criteria():
    from src.engines.hr.rubric import BDManagerRubric
    r = BDManagerRubric()
    assert "sales_experience" in r.weights
    assert "deal_size_complexity" in r.weights
    assert "b2b_track_record" in r.weights
    assert "industry_fit" in r.weights
    assert "communication_quality" in r.weights
    assert "ctc_fit" in r.weights


def test_operations_manager_rubric_has_required_criteria():
    from src.engines.hr.rubric import OperationsManagerRubric
    r = OperationsManagerRubric()
    assert "ops_experience" in r.weights
    assert "team_management" in r.weights
    assert "process_ownership" in r.weights
    assert "vendor_management" in r.weights
    assert "ctc_fit" in r.weights
    assert "communication_quality" in r.weights


def test_rubric_builds_claude_prompt_for_bd():
    from src.engines.hr.rubric import BDManagerRubric
    r = BDManagerRubric()
    prompt = r.build_scoring_prompt(
        resume_text="10 years in enterprise B2B sales, closed deals up to 2Cr",
        application_answer="I want to grow with the company",
        role_salary_max=1500000,
    )
    assert "sales_experience" in prompt
    assert "deal_size_complexity" in prompt
    assert "JSON" in prompt
    assert "breakdown" in prompt


def test_rubric_builds_claude_prompt_for_ops():
    from src.engines.hr.rubric import OperationsManagerRubric
    r = OperationsManagerRubric()
    prompt = r.build_scoring_prompt(
        resume_text="5 years managing 200K sqft facility, team of 30",
        application_answer="Facility management is my passion",
        role_salary_max=1200000,
    )
    assert "ops_experience" in prompt
    assert "vendor_management" in prompt


def test_rubric_returns_ctc_fit_context():
    from src.engines.hr.rubric import BDManagerRubric
    r = BDManagerRubric()
    prompt = r.build_scoring_prompt(
        resume_text="Sales executive",
        application_answer="Expecting 18 LPA",
        role_salary_max=1500000,
    )
    assert "1,500,000" in prompt


def test_get_rubric_for_role():
    from src.engines.hr.rubric import get_rubric_for_role
    from src.models.enums import RoleType
    bd = get_rubric_for_role(RoleType.BD_MANAGER)
    ops = get_rubric_for_role(RoleType.OPERATIONS_MANAGER)
    assert bd.__class__.__name__ == "BDManagerRubric"
    assert ops.__class__.__name__ == "OperationsManagerRubric"


def test_get_rubric_raises_for_unknown_role():
    from src.engines.hr.rubric import get_rubric_for_role
    with pytest.raises(ValueError, match="No rubric defined"):
        get_rubric_for_role("nonexistent_role")
