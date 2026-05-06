"""
Role-specific scoring rubrics for AI Hire.

Each rubric:
- Defines weighted criteria summing to 100
- Builds a Claude prompt that requests a structured JSON breakdown
- Returns enough detail for the admin to understand exactly WHY a candidate scored as they did

Design: rubrics are plain Python classes (no DB dependency) so they can be
unit-tested without a running database. Versioned weights live in hr_rubric_versions
and override these defaults after the self-improvement loop runs.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod


class BaseRubric(ABC):
    role_name: str
    weights: dict[str, float]
    criteria_descriptions: dict[str, str]

    @abstractmethod
    def build_scoring_prompt(
        self,
        *,
        resume_text: str,
        application_answer: str,
        role_salary_max: int,
    ) -> str: ...

    def _format_criteria_block(self) -> str:
        lines = []
        for key, max_pts in self.weights.items():
            label = self.criteria_descriptions.get(key, key)
            lines.append(f"- {key} ({label}): 0–{int(max_pts)} points")
        return "\n".join(lines)

    def _json_schema(self) -> str:
        breakdown_example = {k: 0 for k in self.weights}
        return json.dumps(
            {
                "overall": 0,
                "breakdown": breakdown_example,
                "reasoning": "Why this overall score in 2-3 sentences",
                "green_flags": ["list of specific strengths"],
                "red_flags": ["list of specific concerns"],
                "auto_reject": False,
            },
            indent=2,
        )


class BDManagerRubric(BaseRubric):
    role_name = "BD Manager"
    weights: dict[str, float] = {
        "sales_experience": 25.0,
        "deal_size_complexity": 20.0,
        "b2b_track_record": 20.0,
        "industry_fit": 15.0,
        "communication_quality": 10.0,
        "ctc_fit": 10.0,
    }
    criteria_descriptions: dict[str, str] = {
        "sales_experience": "Relevant sales experience (years, roles, progression)",
        "deal_size_complexity": "Deal size and complexity (ticket size, enterprise vs SMB)",
        "b2b_track_record": "B2B / enterprise sales track record (named clients, quotas)",
        "industry_fit": "Industry fit — real estate, managed offices, hospitality, proptech",
        "communication_quality": "Communication quality inferred from application answer",
        "ctc_fit": "CTC expectation fit against role budget",
    }

    def build_scoring_prompt(
        self,
        *,
        resume_text: str,
        application_answer: str,
        role_salary_max: int,
    ) -> str:
        return f"""You are a senior hiring evaluator for YourCompany, an enterprise managed office platform \
operating 500K+ sqft across NCR, Mumbai, and Chennai.

Score this candidate for the role of BD Manager.

ROLE CONTEXT:
- The BD Manager must independently source and close B2B enterprise deals (managed office memberships \
and enterprise contracts.
- Ideal background: corporate sales, real estate advisory, coworking/managed spaces, hospitality, \
enterprise SaaS, or facility services.
- Role budget (max CTC): {role_salary_max:,}

SCORING CRITERIA (score each on its stated maximum):
{self._format_criteria_block()}

CANDIDATE RESUME:
{resume_text}

APPLICATION ANSWER:
{application_answer}

INSTRUCTIONS:
- Score each criterion on its maximum points (e.g. sales_experience is out of 25).
- overall = sum of all breakdown scores (max 100).
- reasoning: 2-3 sentences explaining the overall score — be specific, cite the resume.
- green_flags: list concrete strengths (deal values mentioned, named clients, specific industries).
- red_flags: list concrete concerns (no B2B experience, CTC too high, gaps, vague answers).
- auto_reject: set true ONLY if the application answer is blank, fewer than 10 words, or \
  contains an obvious disqualifier (e.g. expected CTC > 2× role budget).

Respond ONLY with this JSON (no markdown, no commentary):
{self._json_schema()}"""


class OperationsManagerRubric(BaseRubric):
    role_name = "Operations Manager"
    weights: dict[str, float] = {
        "ops_experience": 25.0,
        "team_management": 20.0,
        "process_ownership": 20.0,
        "vendor_management": 15.0,
        "ctc_fit": 10.0,
        "communication_quality": 10.0,
    }
    criteria_descriptions: dict[str, str] = {
        "ops_experience": "Ops / facility management experience (sqft managed, industry)",
        "team_management": "Team management (size, diversity of function, retention)",
        "process_ownership": "Process ownership and documentation (SOPs, audits, compliance)",
        "vendor_management": "Vendor and contractor management (AMCs, capex, negotiations)",
        "ctc_fit": "CTC expectation fit against role budget",
        "communication_quality": "Communication quality inferred from application answer",
    }

    def build_scoring_prompt(
        self,
        *,
        resume_text: str,
        application_answer: str,
        role_salary_max: int,
    ) -> str:
        return f"""You are a senior hiring evaluator for YourCompany, an enterprise managed office platform \
operating 500K+ sqft across NCR, Mumbai, and Chennai.

Score this candidate for the role of Operations Manager.

ROLE CONTEXT:
- The Operations Manager oversees day-to-day operations of one or more managed office properties \
(10K–100K sqft each), managing a team of 15–50 people including housekeeping, security, \
maintenance, and admin.
- Ideal background: facility management, property management, hospitality ops, large-format \
retail ops, or corporate real estate.
- Role budget (max CTC): {role_salary_max:,}

SCORING CRITERIA (score each on its stated maximum):
{self._format_criteria_block()}

CANDIDATE RESUME:
{resume_text}

APPLICATION ANSWER:
{application_answer}

INSTRUCTIONS:
- Score each criterion on its maximum points (e.g. ops_experience is out of 25).
- overall = sum of all breakdown scores (max 100).
- reasoning: 2-3 sentences explaining the overall score — be specific, cite the resume.
- green_flags: list concrete strengths (sqft numbers, team sizes, specific certifications).
- red_flags: list concrete concerns (no people management, CTC mismatch, no facility background).
- auto_reject: set true ONLY if the application answer is blank, fewer than 10 words, or \
  contains an obvious disqualifier.

Respond ONLY with this JSON (no markdown, no commentary):
{self._json_schema()}"""


# ── Registry ──────────────────────────────────────────────────────────────────

_RUBRIC_REGISTRY: dict[str, type[BaseRubric]] = {
    "bd_manager": BDManagerRubric,
    "operations_manager": OperationsManagerRubric,
}


def get_rubric_for_role(role: str) -> BaseRubric:
    """Return a rubric instance for the given role. Raises ValueError if none defined."""
    key = role.lower().replace(" ", "_") if isinstance(role, str) else str(role.value)
    cls = _RUBRIC_REGISTRY.get(key)
    if cls is None:
        raise ValueError(
            f"No rubric defined for role '{role}'. "
            f"Available: {list(_RUBRIC_REGISTRY.keys())}"
        )
    return cls()
