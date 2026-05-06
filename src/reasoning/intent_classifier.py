"""
Intent Classifier — routes queries to the right context retrieval strategy.

Uses a keyword-pattern approach (no LLM call, microsecond latency) to classify
every incoming question before context assembly. The intent shapes what gets
fetched: a pricing query pulls more closed-deal decisions, a lead evaluation
pulls more approval/rejection decisions, etc.

This is the INTENT component of Scale AI's Enterprise Oversight Layer.
"""

from __future__ import annotations

import re
from enum import Enum


class QueryIntent(str, Enum):
    PRICING = "pricing_query"
    LEAD_EVAL = "lead_evaluation"
    VENDOR = "vendor_lookup"
    RELATIONSHIP = "relationship_query"
    DOCUMENT = "document_search"
    QUALITY = "quality_check"
    GENERAL = "general"


# Each intent maps to a list of regex patterns (matched against lowercased question)
_INTENT_KEYWORDS: dict[QueryIntent, list[str]] = {
    QueryIntent.PRICING: [
        r"\bpric(e|ing|ed)\b",
        r"\bcost\b",
        r"\$", r"₹", r"€",
        r"\brs\.?\b",
        r"\brate\b",
        r"\bquot(e|ation)\b",
        r"\bbudget\b",
        r"\bper seat\b",
        r"\bdeal value\b",
        r"\btotal value\b",
        r"\bcharge\b",
        r"\bfee\b",
        r"\binvoice\b",
    ],
    QueryIntent.LEAD_EVAL: [
        r"\blead\b",
        r"\bprospect\b",
        r"\bapprove\b",
        r"\breject\b",
        r"\bqualif(y|ied|ication)\b",
        r"\bicp\b",
        r"\bideal customer\b",
        r"\bfit\b",
        r"\bconvert\b",
        r"\bpipeline\b",
        r"\bscore\b.*\b(lead|prospect)\b",
    ],
    QueryIntent.VENDOR: [
        r"\bvendor\b",
        r"\bsupplier\b",
        r"\bfitout\b",
        r"\bmaintenance\b",
        r"\bcontractor\b",
        r"\bservice provider\b",
        r"\bamc\b",
        r"\bcleaning\b",
        r"\bsecurity\b.*\bservice\b",
        r"\bfacilities\b",
    ],
    QueryIntent.RELATIONSHIP: [
        r"\bbroker\b",
        r"\bcontact\b",
        r"\bconnect(ed|ion)\b",
        r"\bnetwork\b",
        r"\bintroduc(e|tion)\b",
        r"\brelat(ed|ionship|ion)\b",
        r"\bknow(s)?\b.*\bwho\b",
        r"\bwho (is|are)\b",
        r"\bpoint of contact\b",
        r"\bpoc\b",
    ],
    QueryIntent.DOCUMENT: [
        r"\bcontract\b",
        r"\bdocument\b",
        r"\bagreement\b",
        r"\bloi\b",
        r"\bclause\b",
        r"\bterm(s)?\b",
        r"\bsign(ed|ing)?\b",
        r"\bpdf\b",
        r"\blease\b",
        r"\bmou\b",
    ],
    QueryIntent.QUALITY: [
        r"\bquality\b",
        r"\bduplicate\b",
        r"\bmissing\b",
        r"\bstale\b",
        r"\banomaly\b",
        r"\boutdate(d)?\b",
        r"\bincorrect\b.*\bdata\b",
        r"\berror\b.*\bdata\b",
        r"\bclean\b.*\bdata\b",
    ],
}

# Map intent → decision types to prioritise when fetching RLHF examples
INTENT_DECISION_TYPES: dict[QueryIntent, list[str]] = {
    QueryIntent.PRICING: ["deal_closure", "pricing_override", "response_correction"],
    QueryIntent.LEAD_EVAL: ["lead_approval", "lead_rejection", "response_correction"],
    QueryIntent.VENDOR: ["vendor_approval", "vendor_rejection", "response_correction"],
    QueryIntent.RELATIONSHIP: ["contact_linking", "relationship_update", "response_correction"],
    QueryIntent.DOCUMENT: ["document_review", "contract_signed", "response_correction"],
    QueryIntent.QUALITY: ["data_correction", "conflict_resolution", "response_correction"],
    QueryIntent.GENERAL: [],  # no filter — use pure recency
}


def classify_intent(question: str) -> QueryIntent:
    """
    Fast keyword-based intent classification.
    No LLM call — runs in microseconds.
    Returns the intent with the most pattern hits; defaults to GENERAL.
    """
    q = question.lower()
    scores: dict[QueryIntent, int] = {}

    for intent, patterns in _INTENT_KEYWORDS.items():
        count = sum(1 for p in patterns if re.search(p, q))
        if count > 0:
            scores[intent] = count

    if not scores:
        return QueryIntent.GENERAL

    return max(scores, key=lambda k: scores[k])


def get_intent_decision_types(intent: QueryIntent) -> list[str]:
    """Return decision types most relevant to this intent for targeted RLHF retrieval."""
    return INTENT_DECISION_TYPES.get(intent, [])
