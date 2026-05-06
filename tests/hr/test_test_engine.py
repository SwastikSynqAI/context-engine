"""Unit tests for proctored test engine — Claude mocked."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


MOCK_APTITUDE_QUESTIONS = [
    {
        "question": "If a train travels 120 km in 2 hours, what is its speed?",
        "options": ["40 km/h", "60 km/h", "80 km/h", "100 km/h"],
        "correct_index": 1,
        "module": "aptitude",
    }
] * 10  # 10 MCQs for aptitude

MOCK_ENGLISH_QUESTIONS = [
    {
        "question": "Which sentence is grammatically correct?",
        "options": [
            "She go to office every day.",
            "She goes to office every day.",
            "She going to office every day.",
            "She gone to office every day.",
        ],
        "correct_index": 1,
        "module": "english",
    }
] * 10  # 10 for English


@pytest.fixture
def mock_client():
    client = MagicMock()
    aptitude_resp = MagicMock()
    aptitude_resp.content = [MagicMock(text=json.dumps(MOCK_APTITUDE_QUESTIONS))]
    english_resp = MagicMock()
    english_resp.content = [MagicMock(text=json.dumps(MOCK_ENGLISH_QUESTIONS))]
    client.messages.create = AsyncMock(side_effect=[aptitude_resp, english_resp])
    return client


@pytest.mark.asyncio
async def test_generate_test_returns_questions_dict(mock_client):
    from src.services.test_engine import TestEngine
    engine = TestEngine(client=mock_client)
    questions = await engine.generate_questions(role="bd_manager", ai_required=False)
    assert "aptitude" in questions
    assert "english" in questions
    assert len(questions["aptitude"]) == 10
    assert len(questions["english"]) == 10


@pytest.mark.asyncio
async def test_generate_test_with_ai_module(mock_client):
    ai_resp = MagicMock()
    ai_resp.content = [MagicMock(text=json.dumps([
        {"question": "What is RAG?", "options": ["A", "B", "C", "D"], "correct_index": 0, "module": "ai"}
    ] * 5))]
    aptitude_resp = MagicMock()
    aptitude_resp.content = [MagicMock(text=json.dumps(MOCK_APTITUDE_QUESTIONS))]
    english_resp = MagicMock()
    english_resp.content = [MagicMock(text=json.dumps(MOCK_ENGLISH_QUESTIONS))]
    mock_client.messages.create = AsyncMock(side_effect=[
        aptitude_resp,
        english_resp,
        ai_resp,
    ])
    from src.services.test_engine import TestEngine
    engine = TestEngine(client=mock_client)
    questions = await engine.generate_questions(role="tech", ai_required=True)
    assert "aptitude" in questions
    assert "ai" in questions
    assert "english" in questions


def test_score_test_perfect():
    from src.services.test_engine import score_test
    questions = {
        "aptitude": [{"correct_index": 1} for _ in range(10)],
        "english": [{"correct_index": 0} for _ in range(10)],
    }
    answers = {
        "aptitude": [1] * 10,
        "english": [0] * 10,
    }
    result = score_test(questions=questions, answers=answers, ai_required=False)
    assert result["aptitude_score"] == 100.0
    assert result["english_score"] == 100.0
    assert result["overall_score"] == 100.0
    assert result["passed"] is True


def test_score_test_below_threshold():
    from src.services.test_engine import score_test
    questions = {
        "aptitude": [{"correct_index": 1} for _ in range(10)],
        "english": [{"correct_index": 0} for _ in range(10)],
    }
    answers = {
        "aptitude": [0] * 10,  # all wrong
        "english": [0] * 10,   # all correct
    }
    result = score_test(questions=questions, answers=answers, ai_required=False)
    assert result["aptitude_score"] == 0.0
    assert result["english_score"] == 100.0
    # overall = 0*0.55 + 100*0.45 = 45 — below 60 threshold
    assert result["passed"] is False


def test_generate_test_token_is_unique():
    from src.services.test_engine import generate_test_token
    tokens = {generate_test_token() for _ in range(100)}
    assert len(tokens) == 100
