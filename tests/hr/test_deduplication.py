"""Unit tests for deduplication logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock


def test_exact_email_match_is_duplicate():
    from src.engines.hr.inbound.deduplication import DeduplicationChecker
    checker = DeduplicationChecker.__new__(DeduplicationChecker)
    result = checker._check_email_match(
        incoming_email="ananya@example.com",
        existing_emails=["ananya@example.com", "other@example.com"],
        existing_ids=["id-1", "id-2"],
    )
    assert result.is_duplicate is True
    assert result.existing_entity_id == "id-1"
    assert result.match_reason == "exact_email"


def test_email_mismatch_not_duplicate():
    from src.engines.hr.inbound.deduplication import DeduplicationChecker
    checker = DeduplicationChecker.__new__(DeduplicationChecker)
    result = checker._check_email_match(
        incoming_email="new@example.com",
        existing_emails=["ananya@example.com"],
        existing_ids=["id-1"],
    )
    assert result.is_duplicate is False


def test_exact_phone_match_is_duplicate():
    from src.engines.hr.inbound.deduplication import DeduplicationChecker
    checker = DeduplicationChecker.__new__(DeduplicationChecker)
    result = checker._check_phone_match(
        incoming_phone="+919876543210",
        existing_phones=["+919876543210"],
        existing_ids=["id-1"],
    )
    assert result.is_duplicate is True
    assert result.match_reason == "exact_phone"


def test_none_phone_never_matches():
    from src.engines.hr.inbound.deduplication import DeduplicationChecker
    checker = DeduplicationChecker.__new__(DeduplicationChecker)
    result = checker._check_phone_match(
        incoming_phone=None,
        existing_phones=["+919876543210"],
        existing_ids=["id-1"],
    )
    assert result.is_duplicate is False


def test_high_name_similarity_is_duplicate():
    from src.engines.hr.inbound.deduplication import DeduplicationChecker
    checker = DeduplicationChecker.__new__(DeduplicationChecker)
    score = checker._name_similarity("Ananya Sharma", "Ananya Sharma")
    assert score >= 0.9


def test_low_name_similarity_not_duplicate():
    from src.engines.hr.inbound.deduplication import DeduplicationChecker
    checker = DeduplicationChecker.__new__(DeduplicationChecker)
    score = checker._name_similarity("Ananya Sharma", "Rahul Gupta")
    assert score < 0.5


def test_normalise_phone_strips_spaces_and_dashes():
    from src.engines.hr.inbound.deduplication import normalise_phone
    assert normalise_phone("+91 98765-43210") == "+919876543210"
    assert normalise_phone("  9876543210  ") == "9876543210"
    assert normalise_phone(None) is None
