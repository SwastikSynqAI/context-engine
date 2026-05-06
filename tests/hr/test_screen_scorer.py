"""Unit tests for screen scorer — Claude Haiku client is mocked."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


MOCK_SCREEN_RESPONSE = {
    "overall": 74,
    "question_scores": [
        {"question_index": 0, "score": 16, "notes": "Strong deal size, clear process"},
        {"question_index": 1, "score": 15, "notes": "Good qualification process"},
        {"question_index": 2, "score": 14, "notes": "Honest about failure"},
        {"question_index": 3, "score": 15, "notes": "Reasonable CTC expectation"},
        {"question_index": 4, "score": 14, "notes": "Understands managed office market"},
    ],
    "strong_signals": ["Named specific deal value", "Knows enterprise sales cycle"],
    "role": "bd_manager",
}


@pytest.fixture
def mock_client():
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text=json.dumps(MOCK_SCREEN_RESPONSE))]
    client.messages.create = AsyncMock(return_value=message)
    return client


@pytest.mark.asyncio
async def test_screen_scorer_returns_screen_score(mock_client):
    from src.engines.hr.screening.screen_scorer import ScreenScorer
    scorer = ScreenScorer(client=mock_client)
    qa_pairs = [
        {"question": "What is the largest deal you closed?", "answer": "I closed a 2 crore deal with a fintech startup last year by building a trusted relationship over 4 months."},
        {"question": "How do you qualify leads?", "answer": "I use a combination of company size, budget signals, and decision-maker access to qualify enterprise leads."},
        {"question": "Describe a lost deal.", "answer": "I lost a deal because I did not engage the CFO early enough. I learned to map all stakeholders upfront."},
        {"question": "What is your CTC?", "answer": "Current CTC is 12 LPA and I am expecting 18-20 LPA with a 30 day notice period."},
        {"question": "Why YourCompany?", "answer": "YourCompany is building the managed office category in India and I want to be part of that growth story."},
    ]
    result = await scorer.score(role="bd_manager", qa_pairs=qa_pairs)
    assert result.overall == 74
    assert len(result.question_scores) == 5
    assert result.role == "bd_manager"


@pytest.mark.asyncio
async def test_screen_scorer_calls_claude_haiku(mock_client):
    from src.engines.hr.screening.screen_scorer import ScreenScorer
    scorer = ScreenScorer(client=mock_client)
    await scorer.score(
        role="bd_manager",
        qa_pairs=[{"question": "q", "answer": "answer with enough words to be meaningful here"} for _ in range(5)],
    )
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


@pytest.mark.asyncio
async def test_screen_scorer_handles_parse_error(mock_client):
    bad_message = MagicMock()
    bad_message.content = [MagicMock(text="not json {{{")]
    mock_client.messages.create = AsyncMock(return_value=bad_message)
    from src.engines.hr.screening.screen_scorer import ScreenScorer
    scorer = ScreenScorer(client=mock_client)
    result = await scorer.score(
        role="bd_manager",
        qa_pairs=[{"question": "q", "answer": "a"} for _ in range(5)],
    )
    assert result.overall == 0.0
    assert "parse_error" in result.strong_signals[0] or len(result.question_scores) == 0
