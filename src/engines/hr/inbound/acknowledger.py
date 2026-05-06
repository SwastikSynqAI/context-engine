"""
Acknowledger — sends a warm acknowledgement to every new candidate.

Channels (in priority order):
1. WhatsApp via Twilio (if candidate has phone + Twilio is configured)
2. Email via SMTP (fallback)

All messages are text-only — no voice, no video.
Jinja2 templates are defined inline (no external template files needed at this stage).
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from jinja2 import Template

logger = logging.getLogger(__name__)

# ── Jinja2 templates ──────────────────────────────────────────────────────────

_WHATSAPP_TEMPLATE = Template(
    "Hi {{ name }}! 👋\n\n"
    "Thanks for applying for the *{{ role }}* role at YourCompany.\n\n"
    "We've received your application and our team will review it shortly. "
    "If you're shortlisted, you'll hear from us within 2–3 business days.\n\n"
    "In the meantime, feel free to learn more about us at yourcompany.com.\n\n"
    "— Hiring Team"
)

_EMAIL_SUBJECT_TEMPLATE = Template(
    "We received your application — {{ role }} at YourCompany"
)

_EMAIL_BODY_TEMPLATE = Template(
    "Hi {{ name }},\n\n"
    "Thank you for applying for the {{ role }} position at YourCompany — "
    "India's enterprise managed office platform, operating 500K+ sqft across NCR, Mumbai, and Chennai.\n\n"
    "We've received your application and will review it carefully. "
    "If your profile matches what we're looking for, you'll hear from us within 2–3 business days "
    "with the next steps.\n\n"
    "Best regards,\n"
    "Hiring Team\n"
    "hiring@example.com | yourcompany.com"
)


def render_whatsapp_ack(*, name: str, role: str) -> str:
    return _WHATSAPP_TEMPLATE.render(name=name.split()[0], role=role)


def render_email_ack(*, name: str, role: str) -> tuple[str, str]:
    subject = _EMAIL_SUBJECT_TEMPLATE.render(role=role)
    body = _EMAIL_BODY_TEMPLATE.render(name=name.split()[0], role=role)
    return subject, body


async def send_email_smtp(
    *,
    to_email: str,
    subject: str,
    body: str,
    smtp_config: dict[str, Any],
) -> bool:
    """Send a plain-text email via SMTP. Returns True on success."""
    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_config["from_email"]
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["from_email"], to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        return True
    except Exception as exc:
        logger.error("SMTP send failed to %s: %s", to_email, exc)
        return False


class Acknowledger:
    """
    Sends the post-application acknowledgement to a candidate.

    Inject a real Twilio client and SMTP config in production.
    Pass mocks in tests.
    """

    def __init__(
        self,
        *,
        twilio_client: Any | None,
        twilio_from: str,
        smtp_config: dict[str, Any] | None,
    ) -> None:
        self._twilio = twilio_client
        self._twilio_from = twilio_from
        self._smtp_config = smtp_config

    async def send(
        self,
        *,
        name: str,
        email: str,
        phone: str | None,
        role: str,
    ) -> dict[str, Any]:
        """
        Attempt WhatsApp first. Fall back to email on failure or missing phone.
        Returns dict with: channel ('whatsapp'|'email'), success (bool), error (str|None)
        """
        # Try WhatsApp if phone is available and Twilio is configured
        if phone and self._twilio:
            try:
                wa_message = render_whatsapp_ack(name=name, role=role)
                to = f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone
                self._twilio.messages.create(
                    body=wa_message,
                    from_=f"whatsapp:{self._twilio_from}",
                    to=to,
                )
                logger.info("WhatsApp ack sent to %s for role %s", phone, role)
                return {"channel": "whatsapp", "success": True, "error": None}
            except Exception as exc:
                logger.warning("WhatsApp ack failed for %s: %s. Falling back to email.", phone, exc)

        # Email fallback
        if self._smtp_config:
            subject, body = render_email_ack(name=name, role=role)
            success = await send_email_smtp(
                to_email=email,
                subject=subject,
                body=body,
                smtp_config=self._smtp_config,
            )
            return {"channel": "email", "success": success, "error": None if success else "smtp_failed"}

        logger.warning("No ack sent to %s — neither Twilio nor SMTP configured.", email)
        return {"channel": "none", "success": False, "error": "no_channel_configured"}


def make_acknowledger() -> Acknowledger:
    """Factory that creates an Acknowledger with live credentials from settings."""
    from src.config import get_settings
    settings = get_settings()

    twilio_client = None
    if settings.twilio_account_sid and settings.twilio_auth_token:
        from twilio.rest import Client
        twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    smtp_config = None
    if settings.smtp_username and settings.smtp_password:
        smtp_config = {
            "host": settings.smtp_host,
            "port": settings.smtp_port,
            "username": settings.smtp_username,
            "password": settings.smtp_password,
            "from_email": settings.hiring_email,
        }

    return Acknowledger(
        twilio_client=twilio_client,
        twilio_from=settings.twilio_whatsapp_number,
        smtp_config=smtp_config,
    )
