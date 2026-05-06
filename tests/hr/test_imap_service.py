"""Unit tests for IMAP service — imaplib is mocked."""
import pytest
from unittest.mock import MagicMock, patch


def test_extract_reply_body_from_raw_email():
    """Test that we can extract text from a simple raw email."""
    from src.services.imap_service import extract_reply_body
    raw = (
        "From: candidate@example.com\r\n"
        "To: hiring@example.com\r\n"
        "Subject: Re: YourCompany\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        "I closed a 2 crore deal with a fintech startup last year.\r\n"
        "\r\n"
        "On Mon, Apr 21 wrote:\r\n"
        "> Hi Ananya,\r\n"
    )
    body = extract_reply_body(raw.encode())
    assert "2 crore" in body
    assert len(body.strip()) > 10


def test_extract_reply_strips_quoted_content():
    """Quoted replies (lines starting with >) should be stripped."""
    from src.services.imap_service import extract_reply_body
    raw = (
        "From: candidate@example.com\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        "My answer is that I have 6 years of B2B sales experience.\r\n"
        "\r\n"
        "On Mon, Apr 21 YourCompany <hiring@example.com> wrote:\r\n"
        "> Question 1 of 5:\r\n"
        "> What is the largest deal?\r\n"
    )
    body = extract_reply_body(raw.encode())
    assert "My answer" in body
    assert "> Question" not in body


def test_imap_config_validation():
    """IMAPService raises if host/credentials missing."""
    from src.services.imap_service import IMAPService
    with pytest.raises(ValueError, match="IMAP"):
        IMAPService(host="", port=993, username="", password="")


def test_imap_service_fetch_returns_list():
    """fetch_candidate_replies returns a list (may be empty if IMAP unavailable)."""
    from src.services.imap_service import IMAPService
    service = IMAPService(host="imap.gmail.com", port=993, username="test@gmail.com", password="pass")
    with patch("src.services.imap_service.imaplib") as mock_imap_lib:
        mock_imap = MagicMock()
        mock_imap_lib.IMAP4_SSL.return_value.__enter__.return_value = mock_imap
        mock_imap.login.return_value = ("OK", [b"Logged in"])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b""])  # No messages
        replies = service.fetch_candidate_replies(candidate_email="candidate@example.com", since_hours=24)
    assert isinstance(replies, list)
