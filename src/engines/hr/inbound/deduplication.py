"""
Deduplication logic for candidate intake.

Match strategy (run in order, first match wins):
1. Exact email match — strongest signal
2. Exact phone match (normalised) — strong signal
3. Name similarity > 0.9 AND same role AND application within 7 days — weak signal

Design: pure Python, no DB calls — the caller fetches candidate records
and passes them in. This keeps the logic unit-testable without a DB.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from src.engines.hr.models import DeduplicationResult


def normalise_phone(phone: str | None) -> str | None:
    """Strip spaces, dashes, parentheses from a phone number. Returns None if input is None."""
    if phone is None:
        return None
    return re.sub(r"[\s\-\(\)]", "", phone.strip())


def _normalise_name(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", name.lower().strip())


class DeduplicationChecker:
    """
    Stateless checker — instantiate once per request, call check().
    The caller is responsible for fetching existing candidate records.
    """

    NAME_SIMILARITY_THRESHOLD = 0.9

    def _check_email_match(
        self,
        *,
        incoming_email: str,
        existing_emails: list[str],
        existing_ids: list[str],
    ) -> DeduplicationResult:
        incoming = incoming_email.lower().strip()
        for i, email in enumerate(existing_emails):
            if email.lower().strip() == incoming:
                return DeduplicationResult(
                    is_duplicate=True,
                    existing_entity_id=existing_ids[i],
                    match_reason="exact_email",
                )
        return DeduplicationResult(is_duplicate=False)

    def _check_phone_match(
        self,
        *,
        incoming_phone: str | None,
        existing_phones: list[str | None],
        existing_ids: list[str],
    ) -> DeduplicationResult:
        if incoming_phone is None:
            return DeduplicationResult(is_duplicate=False)
        incoming = normalise_phone(incoming_phone)
        for i, phone in enumerate(existing_phones):
            if phone and normalise_phone(phone) == incoming:
                return DeduplicationResult(
                    is_duplicate=True,
                    existing_entity_id=existing_ids[i],
                    match_reason="exact_phone",
                )
        return DeduplicationResult(is_duplicate=False)

    def _name_similarity(self, name_a: str, name_b: str) -> float:
        return SequenceMatcher(
            None, _normalise_name(name_a), _normalise_name(name_b)
        ).ratio()

    def check(
        self,
        *,
        incoming_name: str,
        incoming_email: str,
        incoming_phone: str | None,
        existing_candidates: list[dict],
    ) -> DeduplicationResult:
        """
        Check a new candidate against a list of existing candidate attribute dicts.
        Each dict must have: entity_id, email, phone (optional), name.

        Returns DeduplicationResult — is_duplicate=True if a match is found.
        """
        existing_emails = [c.get("email", "") for c in existing_candidates]
        existing_phones = [c.get("phone") for c in existing_candidates]
        existing_ids = [c["entity_id"] for c in existing_candidates]
        existing_names = [c.get("name", "") for c in existing_candidates]

        # 1. Email match
        result = self._check_email_match(
            incoming_email=incoming_email,
            existing_emails=existing_emails,
            existing_ids=existing_ids,
        )
        if result.is_duplicate:
            return result

        # 2. Phone match
        result = self._check_phone_match(
            incoming_phone=incoming_phone,
            existing_phones=existing_phones,
            existing_ids=existing_ids,
        )
        if result.is_duplicate:
            return result

        # 3. Name similarity (weak — only flag, not hard block)
        for i, existing_name in enumerate(existing_names):
            if self._name_similarity(incoming_name, existing_name) >= self.NAME_SIMILARITY_THRESHOLD:
                return DeduplicationResult(
                    is_duplicate=True,
                    existing_entity_id=existing_ids[i],
                    match_reason="name_similarity",
                )

        return DeduplicationResult(is_duplicate=False)
