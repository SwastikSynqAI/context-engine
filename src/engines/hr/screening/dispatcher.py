"""
Pre-screen email dispatcher — email-only (no WhatsApp).

Sends one question at a time to a candidate via SMTP.
Reuses send_email_smtp from the acknowledger module.
"""

from __future__ import annotations

import logging
from typing import Any

from src.engines.hr.inbound.acknowledger import send_email_smtp
from src.engines.hr.screening.question_bank import (
    get_questions_for_role,
    make_question_subject,
    render_completion_email,
    render_probe_email,
    render_question_email,
)

logger = logging.getLogger(__name__)

TOTAL_QUESTIONS = 5


class PreScreenDispatcher:
    """Sends pre-screen question emails. Stateless — session state lives in DB."""

    def __init__(self, *, smtp_config: dict[str, Any]) -> None:
        self._smtp = smtp_config

    def _get_question_text(self, *, role: str, question_index: int) -> str:
        questions = get_questions_for_role(role)
        return questions[question_index]["text"]

    def _get_probe_text(self, *, role: str, question_index: int) -> str:
        questions = get_questions_for_role(role)
        return questions[question_index]["probe"]

    async def send_question(
        self,
        *,
        candidate_email: str,
        candidate_name: str,
        role: str,
        question_index: int,
        is_probe: bool,
    ) -> bool:
        """Send a question (or probe) email. Returns True on success."""
        if is_probe:
            probe_text = self._get_probe_text(role=role, question_index=question_index)
            body = render_probe_email(candidate_name=candidate_name, probe_text=probe_text)
            subject = make_question_subject(
                role=role, question_number=question_index + 1, total=TOTAL_QUESTIONS
            )
        else:
            question_text = self._get_question_text(role=role, question_index=question_index)
            is_first = question_index == 0
            body = render_question_email(
                candidate_name=candidate_name,
                question_text=question_text,
                question_number=question_index + 1,
                total_questions=TOTAL_QUESTIONS,
                is_first=is_first,
            )
            subject = make_question_subject(
                role=role, question_number=question_index + 1, total=TOTAL_QUESTIONS
            )

        success = await send_email_smtp(
            to_email=candidate_email,
            subject=subject,
            body=body,
            smtp_config=self._smtp,
        )
        if success:
            logger.info(
                "Pre-screen Q%d sent to %s (probe=%s)",
                question_index + 1, candidate_email, is_probe,
            )
        else:
            logger.error("Failed to send pre-screen Q%d to %s", question_index + 1, candidate_email)
        return success

    async def send_completion(
        self,
        *,
        candidate_email: str,
        candidate_name: str,
    ) -> bool:
        """Send the completion acknowledgement email."""
        body = render_completion_email(candidate_name=candidate_name)
        success = await send_email_smtp(
            to_email=candidate_email,
            subject="YourCompany — Pre-screening complete, thank you!",
            body=body,
            smtp_config=self._smtp,
        )
        return success


def make_dispatcher() -> PreScreenDispatcher:
    """Factory with live SMTP config from settings."""
    from src.config import get_settings
    s = get_settings()
    smtp_config = {
        "host": s.smtp_host,
        "port": s.smtp_port,
        "username": s.smtp_username,
        "password": s.smtp_password,
        "from_email": s.hiring_email,
    }
    return PreScreenDispatcher(smtp_config=smtp_config)
