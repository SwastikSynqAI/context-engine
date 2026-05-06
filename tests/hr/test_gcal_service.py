"""Unit tests for Google Calendar service — Google client mocked."""
import pytest
from unittest.mock import MagicMock, patch


def test_gcal_service_imports():
    from src.services.gcal_service import GoogleCalendarService
    assert GoogleCalendarService is not None


def test_format_event_body():
    from src.services.gcal_service import format_interview_event
    event = format_interview_event(
        candidate_name="Ananya Sharma",
        candidate_email="ananya@example.com",
        role="bd_manager",
        start_iso="2026-05-01T10:00:00+05:30",
        end_iso="2026-05-01T10:45:00+05:30",
        meet_link=None,
    )
    assert event["summary"] == "Interview — Ananya Sharma (Bd Manager)"
    assert "Ananya" in event["description"]
    assert event["start"]["dateTime"] == "2026-05-01T10:00:00+05:30"


def test_gcal_service_create_event_calls_api():
    from src.services.gcal_service import GoogleCalendarService
    mock_service = MagicMock()
    mock_events = MagicMock()
    mock_service.events.return_value = mock_events
    mock_insert = MagicMock()
    mock_events.insert.return_value = mock_insert
    mock_insert.execute.return_value = {
        "id": "event123",
        "hangoutLink": "https://meet.google.com/abc-def-ghi",
    }

    gcal = GoogleCalendarService(service=mock_service, calendar_id="primary")
    result = gcal.create_interview_event(
        candidate_name="Ananya Sharma",
        candidate_email="ananya@example.com",
        role="bd_manager",
        start_iso="2026-05-01T10:00:00+05:30",
        end_iso="2026-05-01T10:45:00+05:30",
    )
    assert result["event_id"] == "event123"
    assert "meet.google.com" in result["meet_link"]
    mock_events.insert.assert_called_once()


def test_make_gcal_service_returns_none_if_not_configured():
    from src.services.gcal_service import make_gcal_service
    with patch("src.services.gcal_service.get_settings") as mock_settings:
        s = MagicMock()
        s.gcal_service_account_json = ""
        mock_settings.return_value = s
        result = make_gcal_service()
    assert result is None
