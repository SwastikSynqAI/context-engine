"""
Response collector — matches IMAP inbox replies to open screen sessions.

For each active screen session (not completed, not timed out):
1. Fetch recent emails from the candidate's email address via IMAP
2. Find emails received after the last question was sent
3. Record the response in hr_screen_responses
4. Decide: send probe (if answer < 15 words and no probe used yet), or send next question
5. If all 5 answers collected → mark session completed, trigger screen scorer

Design: stateless service, called by the reply_checker background worker.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

PROBE_WORD_THRESHOLD = 15
TOTAL_QUESTIONS = 5


def is_answer_too_short(answer: str) -> bool:
    """Return True if the answer has fewer than 15 words (triggers a probe)."""
    return len(answer.split()) < PROBE_WORD_THRESHOLD


class ResponseCollector:
    """
    Processes candidate email replies for an active pre-screen session.
    Stateless — receives session state, returns updated state + action.
    """

    def process_reply(
        self,
        *,
        reply_text: str,
        session_state: dict,
        question_index: int,
    ) -> dict:
        """
        Process a candidate reply for the current question.

        Returns action dict:
        - action: "send_probe" | "send_next_question" | "complete_screening"
        - updated_state: dict (merged into conversation_state)
        - response_recorded: True always
        """
        word_count = len(reply_text.split())
        probe_used = session_state.get("probe_used", False)

        if word_count < PROBE_WORD_THRESHOLD and not probe_used:
            return {
                "action": "send_probe",
                "updated_state": {**session_state, "probe_used": True},
                "response_recorded": True,
                "word_count": word_count,
            }

        next_index = question_index + 1
        if next_index >= TOTAL_QUESTIONS:
            return {
                "action": "complete_screening",
                "updated_state": {
                    **session_state,
                    "current_question_index": next_index,
                    "probe_used": False,
                    "completed": True,
                },
                "response_recorded": True,
                "word_count": word_count,
            }

        return {
            "action": "send_next_question",
            "updated_state": {
                **session_state,
                "current_question_index": next_index,
                "probe_used": False,
            },
            "response_recorded": True,
            "word_count": word_count,
        }
