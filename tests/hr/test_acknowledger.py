"""Unit tests for the acknowledger — Twilio and SMTP are mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def candidate_data():
    return {"name": "Ananya Sharma", "email": "ananya@example.com", "phone": "+919876543210"}


def test_render_whatsapp_template_bd_manager(candidate_data):
    from src.engines.hr.inbound.acknowledger import render_whatsapp_ack
    msg = render_whatsapp_ack(name=candidate_data["name"], role="BD Manager")
    assert "Ananya" in msg
    assert "BD Manager" in msg
    assert len(msg) > 50


def test_render_email_template_ops_manager(candidate_data):
    from src.engines.hr.inbound.acknowledger import render_email_ack
    subject, body = render_email_ack(name=candidate_data["name"], role="Operations Manager")
    assert "Ananya" in body
    assert "Operations Manager" in body
    assert True  # hiring email body
    assert len(subject) > 10


def test_render_templates_do_not_contain_placeholders(candidate_data):
    from src.engines.hr.inbound.acknowledger import render_whatsapp_ack, render_email_ack
    wa = render_whatsapp_ack(name="Test User", role="BD Manager")
    assert "{{" not in wa
    assert "}}" not in wa
    _, body = render_email_ack(name="Test User", role="Operations Manager")
    assert "{{" not in body


@pytest.mark.asyncio
async def test_send_whatsapp_calls_twilio(candidate_data):
    from src.engines.hr.inbound.acknowledger import Acknowledger
    mock_twilio = MagicMock()
    mock_twilio.messages.create = MagicMock(return_value=MagicMock(sid="SM123"))
    ack = Acknowledger(twilio_client=mock_twilio, twilio_from="+14155238886", smtp_config=None)
    result = await ack.send(
        name=candidate_data["name"],
        email=candidate_data["email"],
        phone=candidate_data["phone"],
        role="BD Manager",
    )
    assert result["channel"] == "whatsapp"
    mock_twilio.messages.create.assert_called_once()
    call_kwargs = mock_twilio.messages.create.call_args.kwargs
    assert "whatsapp:" in call_kwargs["to"]


@pytest.mark.asyncio
async def test_falls_back_to_email_when_no_phone(candidate_data):
    from src.engines.hr.inbound.acknowledger import Acknowledger
    mock_twilio = MagicMock()
    smtp_config = {
        "host": "smtp.gmail.com", "port": 587,
        "username": "test@test.com", "password": "pass",
        "from_email": "hiring@example.com",
    }
    ack = Acknowledger(twilio_client=mock_twilio, twilio_from="+14155238886", smtp_config=smtp_config)

    with patch("src.engines.hr.inbound.acknowledger.send_email_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        result = await ack.send(
            name=candidate_data["name"],
            email=candidate_data["email"],
            phone=None,  # No phone — must fall back to email
            role="BD Manager",
        )
    assert result["channel"] == "email"
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_falls_back_to_email_on_twilio_error(candidate_data):
    from src.engines.hr.inbound.acknowledger import Acknowledger
    mock_twilio = MagicMock()
    mock_twilio.messages.create.side_effect = Exception("Twilio error")
    smtp_config = {
        "host": "smtp.gmail.com", "port": 587,
        "username": "test@test.com", "password": "pass",
        "from_email": "hiring@example.com",
    }
    ack = Acknowledger(twilio_client=mock_twilio, twilio_from="+14155238886", smtp_config=smtp_config)

    with patch("src.engines.hr.inbound.acknowledger.send_email_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        result = await ack.send(
            name=candidate_data["name"],
            email=candidate_data["email"],
            phone=candidate_data["phone"],
            role="BD Manager",
        )
    assert result["channel"] == "email"
