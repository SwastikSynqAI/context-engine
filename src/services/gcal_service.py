"""
Google Calendar service — creates interview events with Google Meet links.

Uses a Google service account (JSON key file) for server-to-server auth.
Falls back gracefully if not configured (gcal_service_account_json empty).
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)

TIMEZONE = "Asia/Kolkata"


def format_interview_event(
    *,
    candidate_name: str,
    candidate_email: str,
    role: str,
    start_iso: str,
    end_iso: str,
    meet_link: str | None = None,
) -> dict[str, Any]:
    """Build a Google Calendar event body dict."""
    role_display = role.replace("_", " ").title()
    description = (
        f"Interview with {candidate_name} for the {role_display} role at YourCompany.\n\n"
        f"Candidate email: {candidate_email}\n"
    )
    if meet_link:
        description += f"Google Meet: {meet_link}\n"

    return {
        "summary": f"Interview — {candidate_name} ({role_display})",
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": TIMEZONE},
        "end": {"dateTime": end_iso, "timeZone": TIMEZONE},
        "attendees": [{"email": candidate_email}],
        "conferenceData": {
            "createRequest": {
                "requestId": f"synq-{candidate_email}-{start_iso[:10]}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 60},
                {"method": "popup", "minutes": 15},
            ],
        },
    }


class GoogleCalendarService:
    def __init__(self, *, service: Any, calendar_id: str) -> None:
        self._service = service
        self._calendar_id = calendar_id

    def create_interview_event(
        self,
        *,
        candidate_name: str,
        candidate_email: str,
        role: str,
        start_iso: str,
        end_iso: str,
    ) -> dict[str, str]:
        """Create a Google Calendar event with Meet link. Returns {event_id, meet_link}."""
        event_body = format_interview_event(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            role=role,
            start_iso=start_iso,
            end_iso=end_iso,
        )
        created = (
            self._service.events()
            .insert(
                calendarId=self._calendar_id,
                body=event_body,
                conferenceDataVersion=1,
                sendUpdates="all",
            )
            .execute()
        )
        meet_link = created.get("hangoutLink", "")
        logger.info("Calendar event created: %s", created.get("id"))
        return {"event_id": created.get("id", ""), "meet_link": meet_link}

    def delete_event(self, *, event_id: str) -> None:
        """Delete a calendar event (e.g., when interview is cancelled)."""
        self._service.events().delete(calendarId=self._calendar_id, eventId=event_id).execute()
        logger.info("Calendar event deleted: %s", event_id)


def make_gcal_service() -> GoogleCalendarService | None:
    """Factory from settings. Returns None if service account not configured."""
    s = get_settings()
    if not s.gcal_service_account_json:
        return None
    try:
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        with open(s.gcal_service_account_json) as f:
            info = json.load(f)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        service = build("calendar", "v3", credentials=credentials)
        return GoogleCalendarService(service=service, calendar_id=s.gcal_calendar_id)
    except Exception as exc:
        logger.warning("Google Calendar not available: %s", exc)
        return None
