"""
IMAP inbox poller — reads candidate replies from hiring@example.com.

Uses imaplib with SSL. Designed to work with Gmail (imap.gmail.com:993)
using an App Password. Gracefully handles IMAP unavailability.

Design: synchronous (imaplib is sync) — called in a thread executor when
needed from async contexts, or scheduled as a periodic job.
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
from datetime import UTC, datetime, timedelta
from email.message import Message

logger = logging.getLogger(__name__)


def extract_reply_body(raw_bytes: bytes) -> str:
    """
    Extract the reply text from a raw email bytes object.

    Strips quoted lines (starting with '>') and Gmail-style
    "On [date] [sender] wrote:" attribution lines.
    """
    msg: Message = email.message_from_bytes(raw_bytes)

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")

    return _strip_quoted_text(body)


def _strip_quoted_text(body: str) -> str:
    """Remove quoted reply lines and 'On ... wrote:' attribution lines."""
    lines = body.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if re.match(r"^On .+ wrote:$", stripped):
            break  # Everything after this is quoted
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()


class IMAPService:
    """Polls an IMAP inbox for candidate replies."""

    def __init__(self, *, host: str, port: int, username: str, password: str) -> None:
        if not host or not username:
            raise ValueError("IMAP host and username are required")
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def fetch_candidate_replies(
        self,
        *,
        candidate_email: str,
        since_hours: int = 24,
    ) -> list[dict]:
        """
        Search the inbox for emails from candidate_email in the last since_hours.

        Returns list of dicts: {subject, body, received_at, message_id}
        Returns empty list if IMAP is unavailable or no messages found.
        """
        since_date = (datetime.now(UTC) - timedelta(hours=since_hours)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{candidate_email}" SINCE "{since_date}")'

        results = []
        try:
            with imaplib.IMAP4_SSL(self.host, self.port) as imap:
                imap.login(self.username, self.password)
                imap.select("INBOX")
                status, data = imap.search(None, search_criteria)
                if status != "OK" or not data[0]:
                    return []
                for num in data[0].split():
                    status, msg_data = imap.fetch(num, "(RFC822)")
                    if status != "OK":
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    results.append({
                        "subject": msg.get("Subject", ""),
                        "body": extract_reply_body(raw),
                        "received_at": msg.get("Date", ""),
                        "message_id": msg.get("Message-ID", ""),
                    })
        except Exception as exc:
            logger.warning("IMAP fetch failed for %s: %s", candidate_email, exc)
        return results


def make_imap_service() -> "IMAPService | None":
    """Factory from settings. Returns None if IMAP not configured."""
    from src.config import get_settings
    s = get_settings()
    if not s.smtp_username or not s.smtp_password:
        return None
    # Gmail IMAP uses imap.gmail.com regardless of smtp_host
    host = "imap.gmail.com"
    return IMAPService(host=host, port=993, username=s.smtp_username, password=s.smtp_password)
