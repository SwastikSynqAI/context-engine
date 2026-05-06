"""Unit tests for offer letter generator — Claude mocked."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_offer_generator_imports():
    from src.services.offer_generator import OfferGenerator
    assert OfferGenerator is not None


def test_build_offer_context():
    from src.services.offer_generator import build_offer_context
    ctx = build_offer_context(
        candidate_name="Ananya Sharma",
        role="bd_manager",
        ctc_lpa=18.0,
        joining_date="2026-06-01",
        reporting_to="Admin Doshi",
        location="Bangalore",
    )
    assert ctx["candidate_name"] == "Ananya Sharma"
    assert ctx["role_display"] == "Bd Manager"
    assert ctx["ctc_lpa"] == 18.0
    assert "joining_date" in ctx


@pytest.mark.asyncio
async def test_generate_offer_narrative_calls_claude():
    from src.services.offer_generator import OfferGenerator
    mock_client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text="Dear Ananya, We are pleased to offer you the position...")]
    mock_client.messages.create = AsyncMock(return_value=message)

    gen = OfferGenerator(client=mock_client)
    narrative = await gen.generate_narrative(
        candidate_name="Ananya Sharma",
        role="bd_manager",
        ctc_lpa=18.0,
        joining_date="2026-06-01",
    )
    assert "Ananya" in narrative
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"


def test_write_offer_docx_creates_file(tmp_path):
    from src.services.offer_generator import write_offer_docx
    output_path = tmp_path / "offer.docx"
    write_offer_docx(
        output_path=str(output_path),
        candidate_name="Ananya Sharma",
        role="bd_manager",
        ctc_lpa=18.0,
        joining_date="2026-06-01",
        narrative="Dear Ananya, We are pleased to offer you the BD Manager position at YourCompany.",
        reporting_to="Admin Doshi",
        location="Bangalore",
    )
    assert output_path.exists()
    assert output_path.stat().st_size > 0
