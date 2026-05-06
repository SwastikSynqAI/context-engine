"""Tests for HR Pydantic models and enum imports."""
import pytest

def test_hr_entity_type_enum_exists():
    from src.models.enums import EntityType
    assert EntityType.CANDIDATE == "candidate"
    assert EntityType.HR_ROLE == "hr_role"

def test_hr_relationship_type_enums_exist():
    from src.models.enums import RelationshipType
    assert RelationshipType.HIRED_FOR == "hired_for"
    assert RelationshipType.APPLIED_FOR == "applied_for"

def test_hr_decision_type_enums_exist():
    from src.models.enums import DecisionType
    assert DecisionType.HIRE_APPROVAL == "hire_approval"
    assert DecisionType.HIRE_REJECTION == "hire_rejection"
    assert DecisionType.SHORTLIST_APPROVAL == "shortlist_approval"

def test_hr_data_source_enums_exist():
    from src.models.enums import DataSource
    assert DataSource.LINKEDIN_INBOUND == "linkedin_inbound"
    assert DataSource.LINKEDIN_SOURCED == "linkedin_sourced"
    assert DataSource.NAUKRI == "naukri"
    assert DataSource.INSTAHYRE == "instahyre"
    assert DataSource.CAREERS_FORM == "careers_form"

def test_candidate_stage_enum_exists():
    from src.engines.hr.models import CandidateStage
    assert CandidateStage.APPLIED == "applied"
    assert CandidateStage.HIRED == "hired"
    assert CandidateStage.REJECTED == "rejected"

def test_screen_channel_enum_no_voice():
    from src.engines.hr.models import ScreenChannel
    assert ScreenChannel.WHATSAPP == "whatsapp"
    assert ScreenChannel.EMAIL == "email"
    assert not hasattr(ScreenChannel, "VOICE")
    assert not hasattr(ScreenChannel, "PHONE")

def test_candidate_model_pii_defaults():
    from src.engines.hr.models import CandidateCreate
    c = CandidateCreate(
        name="Ananya Sharma",
        email="ananya@example.com",
        phone="+919876543210",
        role="bd_manager",
        source="careers_form",
    )
    assert c.name == "Ananya Sharma"
    assert c.pii_fields == ["email", "phone"]

def test_resume_score_breakdown_required():
    from src.engines.hr.models import ResumeScore
    score = ResumeScore(
        overall=78.0,
        breakdown={"sales_experience": 20, "deal_size": 15},
        reasoning="Strong sales background",
        green_flags=["Named clients"],
        red_flags=[],
        role="bd_manager",
    )
    assert score.overall == 78.0
    assert score.breakdown["sales_experience"] == 20

def test_screen_score_per_question():
    from src.engines.hr.models import ScreenScore, QuestionScore
    ss = ScreenScore(
        overall=72.0,
        question_scores=[
            QuestionScore(question_index=0, score=15, notes="Specific deal cited"),
            QuestionScore(question_index=1, score=12, notes="Good process described"),
        ],
        role="bd_manager",
    )
    assert len(ss.question_scores) == 2
    assert ss.question_scores[0].score == 15

def test_application_combined_score():
    from src.engines.hr.models import Application, CandidateStage
    app = Application(
        id="test-uuid",
        candidate_entity_id="cand-uuid",
        role="bd_manager",
        source="careers_form",
        stage=CandidateStage.PARSED,
        resume_score=80.0,
        screen_score=70.0,
    )
    # combined = resume*0.4 + screen*0.6
    assert abs(app.combined_score - 74.0) < 0.01
