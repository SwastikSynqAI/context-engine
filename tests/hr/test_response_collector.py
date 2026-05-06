"""Unit tests for response collector."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_is_answer_too_short_returns_true_for_short():
    from src.engines.hr.screening.response_collector import is_answer_too_short
    assert is_answer_too_short("ok") is True
    assert is_answer_too_short("yes I agree") is True


def test_is_answer_too_short_returns_false_for_good_answer():
    from src.engines.hr.screening.response_collector import is_answer_too_short
    long_answer = "I have worked in B2B sales for 6 years and closed multiple large deals with enterprise clients across various verticals."
    assert is_answer_too_short(long_answer) is False


def test_response_collector_imports():
    from src.engines.hr.screening.response_collector import ResponseCollector
    assert ResponseCollector is not None
