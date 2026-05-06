"""Unit tests for pre-screen email dispatcher — SMTP is mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def smtp_config():
    return {
        "host": "smtp.gmail.com",
        "port": 587,
        "username": "hiring@example.com",
        "password": "testpass",
        "from_email": "hiring@example.com",
    }


@pytest.mark.asyncio
async def test_send_first_question_uses_intro_template(smtp_config):
    from src.engines.hr.screening.dispatcher import PreScreenDispatcher
    with patch("src.engines.hr.screening.dispatcher.send_email_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        dispatcher = PreScreenDispatcher(smtp_config=smtp_config)
        await dispatcher.send_question(
            candidate_email="ananya@example.com",
            candidate_name="Ananya Sharma",
            role="bd_manager",
            question_index=0,
            is_probe=False,
        )
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert "ananya@example.com" == call_kwargs["to_email"]
    assert "YourCompany" in call_kwargs["subject"]
    assert "Ananya" in call_kwargs["body"]


@pytest.mark.asyncio
async def test_send_subsequent_question_uses_followup_template(smtp_config):
    from src.engines.hr.screening.dispatcher import PreScreenDispatcher
    with patch("src.engines.hr.screening.dispatcher.send_email_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        dispatcher = PreScreenDispatcher(smtp_config=smtp_config)
        await dispatcher.send_question(
            candidate_email="ananya@example.com",
            candidate_name="Ananya Sharma",
            role="bd_manager",
            question_index=2,
            is_probe=False,
        )
    body = mock_send.call_args.kwargs["body"]
    assert "next question" in body.lower() or "thanks for your answer" in body.lower()


@pytest.mark.asyncio
async def test_send_probe_uses_probe_template(smtp_config):
    from src.engines.hr.screening.dispatcher import PreScreenDispatcher
    with patch("src.engines.hr.screening.dispatcher.send_email_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        dispatcher = PreScreenDispatcher(smtp_config=smtp_config)
        await dispatcher.send_question(
            candidate_email="ananya@example.com",
            candidate_name="Ananya Sharma",
            role="bd_manager",
            question_index=0,
            is_probe=True,
        )
    body = mock_send.call_args.kwargs["body"]
    assert "follow-up" in body.lower() or "quick" in body.lower()


@pytest.mark.asyncio
async def test_send_completion_email(smtp_config):
    from src.engines.hr.screening.dispatcher import PreScreenDispatcher
    with patch("src.engines.hr.screening.dispatcher.send_email_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        dispatcher = PreScreenDispatcher(smtp_config=smtp_config)
        await dispatcher.send_completion(
            candidate_email="ananya@example.com",
            candidate_name="Ananya Sharma",
        )
    mock_send.assert_called_once()
    body = mock_send.call_args.kwargs["body"]
    assert "Ananya" in body


def test_dispatcher_raises_if_question_index_out_of_range(smtp_config):
    from src.engines.hr.screening.dispatcher import PreScreenDispatcher
    dispatcher = PreScreenDispatcher(smtp_config=smtp_config)
    with pytest.raises(IndexError):
        dispatcher._get_question_text(role="bd_manager", question_index=10)
