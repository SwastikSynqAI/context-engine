"""
Pre-screen question bank — email-based, one question at a time.

Each role has exactly 5 questions. Each question has:
- text: the main question text
- probe: a follow-up if the candidate's answer is too short (< 15 words)

All communication is via email only (no WhatsApp).
"""

from __future__ import annotations

from jinja2 import Template

# ── Question sets ─────────────────────────────────────────────────────────────

_BD_MANAGER_QUESTIONS = [
    {
        "text": (
            "What's the largest B2B deal you've personally closed? "
            "Share the deal value and briefly describe how you got there."
        ),
        "probe": "Could you share a rough deal value and the key steps that got you there?",
    },
    {
        "text": (
            "How do you typically identify and qualify new enterprise leads? "
            "Walk us through your process from first contact to qualified opportunity."
        ),
        "probe": "Which signals or criteria matter most to you when qualifying a lead?",
    },
    {
        "text": (
            "Describe a deal you lost. What happened and what did you learn from it?"
        ),
        "probe": "What specifically would you do differently if you had that deal again?",
    },
    {
        "text": (
            "What's your current CTC and what are you expecting? "
            "Also, what's your notice period?"
        ),
        "probe": "Please share both the current and expected figures — this helps us move faster.",
    },
    {
        "text": (
            "Why are you interested in YourCompany specifically? "
            "What do you know about the managed office space in India?"
        ),
        "probe": "What draws you to this sector compared to other industries you could work in?",
    },
]

_OPERATIONS_MANAGER_QUESTIONS = [
    {
        "text": (
            "Describe the largest facility or operational portfolio you've managed. "
            "What was the square footage, team size, and your key responsibilities?"
        ),
        "probe": "Could you share rough numbers for team size and the scope of the facility?",
    },
    {
        "text": (
            "How do you handle vendor escalations when a critical service (HVAC, housekeeping, security) "
            "fails at a client site? Walk us through a real example."
        ),
        "probe": "What was the client impact and how did you ensure it didn't recur?",
    },
    {
        "text": (
            "Tell us about a process improvement you drove in facility or operations management. "
            "What was the problem, your solution, and the measurable outcome?"
        ),
        "probe": "Can you quantify the outcome — cost saved, time reduced, or SLA improvement?",
    },
    {
        "text": (
            "What's your current CTC and what are you expecting? "
            "Also, what's your notice period?"
        ),
        "probe": "Please share both figures — it helps us align quickly.",
    },
    {
        "text": (
            "Why are you drawn to managed office / flex workspace operations "
            "rather than traditional facility management or corporate real estate?"
        ),
        "probe": "What specifically about this sector interests you at this stage of your career?",
    },
]

_GENERIC_QUESTIONS = [
    {
        "text": (
            "Tell us about your most significant professional achievement in the last two years. "
            "What was the challenge, what did you do, and what was the outcome?"
        ),
        "probe": "Can you share a rough sense of scale — team size, revenue impact, or another measurable result?",
    },
    {
        "text": (
            "Walk us through your experience most relevant to this role. "
            "What have you built, managed, or improved that directly applies here?"
        ),
        "probe": "Which part of that experience do you feel is the strongest fit for what we're hiring for?",
    },
    {
        "text": (
            "Describe a situation where you had to work under pressure or tight deadlines. "
            "How did you handle it and what was the result?"
        ),
        "probe": "What specifically did you prioritise and what would you do differently now?",
    },
    {
        "text": (
            "What's your current CTC and what are you expecting? "
            "Also, what's your notice period?"
        ),
        "probe": "Please share both figures — it helps us move faster.",
    },
    {
        "text": (
            "Why are you interested in YourCompany specifically, "
            "and what do you know about the managed office space sector in India?"
        ),
        "probe": "What draws you to this role and company at this point in your career?",
    },
]

_QUESTION_REGISTRY: dict[str, list[dict]] = {
    "bd_manager": _BD_MANAGER_QUESTIONS,
    "operations_manager": _OPERATIONS_MANAGER_QUESTIONS,
}

# ── Email templates ───────────────────────────────────────────────────────────

_QUESTION_EMAIL_TEMPLATE = Template(
    "Hi {{ first_name }},\n\n"
    "Thanks for applying to YourCompany! We'd love to learn a bit more about you "
    "before we schedule a conversation.\n\n"
    "We'll ask you 5 short questions — one at a time — over email. "
    "Just reply to each email with your answer. Takes about 10–15 minutes total.\n\n"
    "Question {{ question_number }} of {{ total_questions }}:\n\n"
    "{{ question_text }}\n\n"
    "Looking forward to your reply.\n\n"
    "Best,\n"
    "Hiring Team\n"
    "hiring@example.com"
)

_SUBSEQUENT_QUESTION_TEMPLATE = Template(
    "Hi {{ first_name }},\n\n"
    "Thanks for your answer! Here's the next question.\n\n"
    "Question {{ question_number }} of {{ total_questions }}:\n\n"
    "{{ question_text }}\n\n"
    "Best,\n"
    "Hiring Team\n"
    "hiring@example.com"
)

_PROBE_TEMPLATE = Template(
    "Hi {{ first_name }},\n\n"
    "Thanks! Just a quick follow-up on that:\n\n"
    "{{ probe_text }}\n\n"
    "Best,\n"
    "Hiring Team\n"
    "hiring@example.com"
)

_COMPLETION_TEMPLATE = Template(
    "Hi {{ first_name }},\n\n"
    "Thank you for completing the pre-screening questions! "
    "We've received all your answers and will be in touch shortly.\n\n"
    "If shortlisted for the next round, you'll receive a link to a short online assessment.\n\n"
    "Best,\n"
    "Hiring Team\n"
    "hiring@example.com"
)


# ── Public API ────────────────────────────────────────────────────────────────

def get_questions_for_role(role: str) -> list[dict]:
    """Return the list of 5 pre-screen question dicts for a role, falling back to generic questions."""
    if role not in _QUESTION_REGISTRY:
        return _GENERIC_QUESTIONS
    return _QUESTION_REGISTRY[role]


def render_question_email(
    *,
    candidate_name: str,
    question_text: str,
    question_number: int,
    total_questions: int,
    is_first: bool = True,
) -> str:
    """Render the email body for a pre-screen question."""
    first_name = candidate_name.split()[0]
    template = _QUESTION_EMAIL_TEMPLATE if is_first else _SUBSEQUENT_QUESTION_TEMPLATE
    return template.render(
        first_name=first_name,
        question_number=question_number,
        total_questions=total_questions,
        question_text=question_text,
    )


def render_probe_email(*, candidate_name: str, probe_text: str) -> str:
    """Render the probe follow-up email body."""
    return _PROBE_TEMPLATE.render(
        first_name=candidate_name.split()[0],
        probe_text=probe_text,
    )


def render_completion_email(*, candidate_name: str) -> str:
    """Render the completion acknowledgement email body."""
    return _COMPLETION_TEMPLATE.render(first_name=candidate_name.split()[0])


def make_question_subject(*, role: str, question_number: int, total: int = 5) -> str:
    role_display = role.replace("_", " ").title()
    if question_number == 1:
        return f"YourCompany — {role_display} pre-screening (Q{question_number} of {total})"
    return f"Re: YourCompany — {role_display} pre-screening (Q{question_number} of {total})"
