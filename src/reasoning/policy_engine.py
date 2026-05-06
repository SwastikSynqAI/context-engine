"""
Policy Engine — the guardrail layer applied to every Claude response.

Implements the POLICY component of Scale AI's Enterprise Oversight Layer.

Two tiers of policies:

1. Built-in code policies (always active, no DB required, <1ms):
   - NoPIIInResponse: block any answer containing email or phone numbers
   - HallucinationRisk: warn when no entity context was used
   - LowConfidenceDisclaimer: append a caveat when confidence < 0.5

2. Stored PolicyRule records (DB, configurable by the admin):
   - question_contains + answer_contains matching
   - answer_number_below: value-floor enforcement (e.g., never quote below configured minimum)
   - Severity: block | warn | flag

Violation severities:
  block  → response is replaced with the violation message (PII, critical errors)
  warn   → a ⚠️ disclaimer is appended to the response
  flag   → logged silently for human review; response unchanged
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Indian PII patterns
_PII_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # email
    re.compile(r"\b(\+91[\s\-]?)?[6-9]\d{9}\b"),                          # Indian mobile
    re.compile(r"\b0\d{10}\b"),                                             # landline with STD
]


@dataclass
class PolicyViolation:
    policy_name: str
    severity: str          # block | warn | flag
    message: str
    remediation: str = ""


@dataclass
class PolicyCheckResult:
    violations: list[PolicyViolation] = field(default_factory=list)
    is_blocked: bool = False
    appended_disclaimers: list[str] = field(default_factory=list)

    def add(self, v: PolicyViolation) -> None:
        self.violations.append(v)
        if v.severity == "block":
            self.is_blocked = True
        elif v.severity == "warn":
            self.appended_disclaimers.append(f"⚠️ {v.message}")


class PolicyEngine:
    """
    Runs all active policies against every (question, answer) pair before
    the ContextResponse leaves the context engine.
    """

    def __init__(self, db: "AsyncSession") -> None:
        self.db = db

    async def check(
        self,
        question: str,
        answer: str,
        confidence: float,
        context_entities_used: int,
    ) -> PolicyCheckResult:
        result = PolicyCheckResult()

        # Built-in policies (no DB, always run)
        self._check_pii(answer, result)
        self._check_hallucination_risk(context_entities_used, result)
        self._check_low_confidence(confidence, answer, result)

        # Stored policies (DB-backed, skip gracefully if table absent)
        await self._check_stored_policies(question, answer, result)

        return result

    # ── Built-in policies ────────────────────────────────────────────────────

    def _check_pii(self, answer: str, result: PolicyCheckResult) -> None:
        for pattern in _PII_PATTERNS:
            if pattern.search(answer):
                result.add(PolicyViolation(
                    policy_name="NoPIIInResponse",
                    severity="block",
                    message=(
                        "This response was blocked: it contained what appears to be a phone number "
                        "or email address. Raw contact details are not returned in answers to comply "
                        "with DPDP Act requirements. Look up the entity directly via GET /entities/{id}."
                    ),
                    remediation="Remove raw contact details; reference the entity by name instead.",
                ))
                return  # one PII hit is enough to block

    def _check_hallucination_risk(
        self, context_entities_used: int, result: PolicyCheckResult
    ) -> None:
        if context_entities_used == 0:
            result.add(PolicyViolation(
                policy_name="HallucinationRisk",
                severity="warn",
                message=(
                    "No entity context was found in the knowledge graph for this question. "
                    "This answer is based on general knowledge only — verify before acting on it."
                ),
            ))

    def _check_low_confidence(
        self, confidence: float, answer: str, result: PolicyCheckResult
    ) -> None:
        if confidence < 0.5:
            uncertainty_words = [
                "uncertain", "unsure", "low confidence", "not clear",
                "may be", "might be", "possibly", "unclear",
            ]
            if not any(w in answer.lower() for w in uncertainty_words):
                result.add(PolicyViolation(
                    policy_name="LowConfidenceDisclaimer",
                    severity="warn",
                    message=(
                        f"Data confidence is low ({confidence:.0%}). "
                        "Cross-check with source systems before making decisions."
                    ),
                ))

    # ── Stored policies ───────────────────────────────────────────────────────

    async def _check_stored_policies(
        self, question: str, answer: str, result: PolicyCheckResult
    ) -> None:
        try:
            from sqlalchemy import select
            from src.models.entities import PolicyRule
            stmt = select(PolicyRule).where(PolicyRule.is_active == True)
            db_result = await self.db.execute(stmt)
            rules = list(db_result.scalars().all())
        except Exception:
            # Table may not exist before migration 003 runs — skip silently
            return

        for rule in rules:
            if self._matches(rule.condition, question, answer):
                result.add(PolicyViolation(
                    policy_name=rule.name,
                    severity=rule.severity,
                    message=rule.violation_message,
                    remediation=rule.remediation or "",
                ))
                # Track how many times this policy has fired
                try:
                    rule.fire_count = (rule.fire_count or 0) + 1
                except Exception:
                    pass

    @staticmethod
    def _matches(condition: dict, question: str, answer: str) -> bool:
        """
        Evaluate a stored policy condition against the question+answer pair.

        Supported condition keys:
          question_contains: str   — substring match on question (case-insensitive)
          answer_contains: str     — substring match on answer (case-insensitive)
          answer_number_below: {threshold: float}
              fires when any number in the answer is below the threshold
              (price-floor enforcement: "never quote below configured minimum value")
        """
        if not condition:
            return True

        q_lower = question.lower()
        a_lower = answer.lower()

        if qc := condition.get("question_contains"):
            if qc.lower() not in q_lower:
                return False

        if ac := condition.get("answer_contains"):
            if ac.lower() not in a_lower:
                return False

        if nb := condition.get("answer_number_below"):
            threshold = float(nb.get("threshold", 0))
            numbers = [
                float(n.replace(",", ""))
                for n in re.findall(r"[\d,]+\.?\d*", answer)
                if n.replace(",", "")
            ]
            if not any(n < threshold for n in numbers):
                return False

        return True
