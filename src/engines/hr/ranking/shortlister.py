"""
Shortlister — ranks candidates by combined score and emails Admin.

After Gate 1: Admin responds via the admin dashboard (approve/reject per candidate).
This module handles only the ranking and the notification email.
Email only — no WhatsApp.
"""

from __future__ import annotations

import logging
from typing import Any

from jinja2 import Template

from src.engines.hr.inbound.acknowledger import send_email_smtp
from src.engines.hr.scoring.combined_scorer import compute_combined_score

logger = logging.getLogger(__name__)

_SHORTLIST_EMAIL_TEMPLATE = Template(
    "Hi,\n\n"
    "Here are the top {{ count }} candidate(s) ready for interview review for the "
    "{{ role_display }} role:\n\n"
    "{% for c in candidates %}"
    "{{ loop.index }}. {{ c.name }} — Combined Score: {{ c.combined_score }}/100\n"
    "   Resume: {{ c.resume_score }} | Screen: {{ c.screen_score }}\n"
    "   Email: {{ c.email }}\n"
    "   Dashboard: {{ dashboard_url }}/candidates/{{ c.application_id }}\n\n"
    "{% endfor %}"
    "Review and approve/reject at: {{ dashboard_url }}/pipeline\n\n"
    "— AI Hire\n"
)


def build_shortlist(
    candidates: list[dict],
    *,
    top_n: int | None = None,
) -> list[dict]:
    """Rank candidates by combined score. Returns sorted list with combined_score added."""
    for c in candidates:
        c["combined_score"] = compute_combined_score(
            resume_score=float(c.get("resume_score", 0)),
            screen_score=float(c.get("screen_score", 0)) if c.get("screen_score") is not None else None,
        )
    ranked = sorted(candidates, key=lambda c: c["combined_score"], reverse=True)
    return ranked[:top_n] if top_n else ranked


def render_shortlist_email(
    *,
    candidates: list[dict],
    role: str,
    dashboard_url: str,
) -> str:
    role_display = role.replace("_", " ").title()
    return _SHORTLIST_EMAIL_TEMPLATE.render(
        candidates=candidates,
        count=len(candidates),
        role_display=role_display,
        dashboard_url=dashboard_url,
    )


class Shortlister:
    def __init__(
        self,
        *,
        admin_notify_email: str,
        smtp_config: dict[str, Any],
        dashboard_url: str,
    ) -> None:
        self._admin_notify_email = admin_notify_email
        self._smtp_config = smtp_config
        self._dashboard_url = dashboard_url

    async def send_shortlist(self, *, candidates: list[dict], role: str) -> bool:
        """Email the shortlist to Admin for Gate 1 approval."""
        role_display = role.replace("_", " ").title()
        body = render_shortlist_email(
            candidates=candidates,
            role=role,
            dashboard_url=self._dashboard_url,
        )
        success = await send_email_smtp(
            to_email=self._admin_notify_email,
            subject=f"AI Hire — Shortlist ready for {role_display} ({len(candidates)} candidate(s))",
            body=body,
            smtp_config=self._smtp_config,
        )
        if success:
            logger.info("Shortlist email sent to Admin for role %s (%d candidates)", role, len(candidates))
        return success


def make_shortlister() -> Shortlister:
    from src.config import get_settings
    s = get_settings()
    smtp_config = {
        "host": s.smtp_host,
        "port": s.smtp_port,
        "username": s.smtp_username,
        "password": s.smtp_password,
        "from_email": s.hiring_email,
    }
    return Shortlister(
        admin_notify_email=s.admin_notify_email,
        smtp_config=smtp_config,
        dashboard_url=s.frontend_url,
    )
