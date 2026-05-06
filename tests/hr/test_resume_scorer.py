"""Unit tests for resume scorer — Claude Haiku client is mocked."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


MOCK_CLAUDE_RESPONSE = {
    "overall": 78,
    "breakdown": {
        "sales_experience": 20,
        "deal_size_complexity": 16,
        "b2b_track_record": 15,
        "industry_fit": 12,
        "communication_quality": 8,
        "ctc_fit": 7,
    },
    "reasoning": "Strong B2B sales background with 5 years experience.",
    "green_flags": ["Closed 1.5Cr deal", "Named fintech clients"],
    "red_flags": ["No real estate experience"],
    "auto_reject": False,
}


@pytest.fixture
def mock_anthropic_client():
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text=json.dumps(MOCK_CLAUDE_RESPONSE))]
    client.messages.create = AsyncMock(return_value=message)
    return client


@pytest.mark.asyncio
async def test_score_resume_returns_resume_score(mock_anthropic_client):
    from src.engines.hr.scoring.resume_scorer import ResumeScorer
    scorer = ResumeScorer(client=mock_anthropic_client)
    result = await scorer.score(
        resume_text="5 years B2B sales, closed 1.5Cr deal with fintech startup",
        application_answer="I have strong BD experience and want to grow with YourCompany in the managed office space.",
        role="bd_manager",
        role_salary_max=1500000,
    )
    assert result.overall == 78
    assert result.breakdown["sales_experience"] == 20
    assert len(result.green_flags) == 2
    assert result.auto_reject is False
    assert result.role == "bd_manager"


@pytest.mark.asyncio
async def test_score_calls_claude_haiku(mock_anthropic_client):
    from src.engines.hr.scoring.resume_scorer import ResumeScorer
    scorer = ResumeScorer(client=mock_anthropic_client)
    await scorer.score(
        resume_text="Resume text here",
        application_answer="Application answer with more than ten words here",
        role="bd_manager",
        role_salary_max=1200000,
    )
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 1024


@pytest.mark.asyncio
async def test_score_handles_json_parse_error(mock_anthropic_client):
    """If Claude returns garbled JSON, scorer returns a safe fallback score."""
    bad_message = MagicMock()
    bad_message.content = [MagicMock(text="not valid json {{{")]
    mock_anthropic_client.messages.create = AsyncMock(return_value=bad_message)

    from src.engines.hr.scoring.resume_scorer import ResumeScorer
    scorer = ResumeScorer(client=mock_anthropic_client)
    result = await scorer.score(
        resume_text="Resume",
        application_answer="Application answer with ten or more words total here",
        role="bd_manager",
        role_salary_max=1200000,
    )
    assert result.overall == 0
    assert result.auto_reject is False
    assert "parse_error" in result.reasoning


@pytest.mark.asyncio
async def test_score_for_operations_manager(mock_anthropic_client):
    ops_response = {
        "overall": 82,
        "breakdown": {
            "ops_experience": 22,
            "team_management": 17,
            "process_ownership": 18,
            "vendor_management": 13,
            "ctc_fit": 7,
            "communication_quality": 5,
        },
        "reasoning": "Strong facility management background.",
        "green_flags": ["Managed 100K sqft"],
        "red_flags": [],
        "auto_reject": False,
    }
    message = MagicMock()
    message.content = [MagicMock(text=json.dumps(ops_response))]
    mock_anthropic_client.messages.create = AsyncMock(return_value=message)

    from src.engines.hr.scoring.resume_scorer import ResumeScorer
    scorer = ResumeScorer(client=mock_anthropic_client)
    result = await scorer.score(
        resume_text="8 years facility management, 100K sqft, team of 40",
        application_answer="I am passionate about creating excellent workspace environments for enterprise clients.",
        role="operations_manager",
        role_salary_max=1200000,
    )
    assert result.overall == 82
    assert result.role == "operations_manager"
