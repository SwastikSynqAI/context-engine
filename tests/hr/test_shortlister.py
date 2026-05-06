"""Unit tests for shortlister."""
import pytest
from unittest.mock import AsyncMock, patch


def test_build_shortlist_ranks_by_combined_score():
    from src.engines.hr.ranking.shortlister import build_shortlist
    candidates = [
        {"entity_id": "a", "name": "Alice", "email": "a@x.com", "role": "bd_manager",
         "resume_score": 80, "screen_score": 90, "application_id": "app-1"},
        {"entity_id": "b", "name": "Bob", "email": "b@x.com", "role": "bd_manager",
         "resume_score": 90, "screen_score": 70, "application_id": "app-2"},
        {"entity_id": "c", "name": "Carol", "email": "c@x.com", "role": "bd_manager",
         "resume_score": 85, "screen_score": 85, "application_id": "app-3"},
    ]
    ranked = build_shortlist(candidates=candidates, top_n=2)
    assert len(ranked) == 2
    # combined: a=80*0.4+90*0.6=86, b=90*0.4+70*0.6=78, c=85*0.4+85*0.6=85
    assert ranked[0]["entity_id"] == "a"
    assert ranked[1]["entity_id"] == "c"
    assert "combined_score" in ranked[0]


def test_build_shortlist_no_top_n_returns_all():
    from src.engines.hr.ranking.shortlister import build_shortlist
    candidates = [
        {"entity_id": str(i), "name": f"Person {i}", "email": f"p{i}@x.com",
         "role": "bd_manager", "resume_score": 70, "screen_score": 70,
         "application_id": f"app-{i}"}
        for i in range(5)
    ]
    ranked = build_shortlist(candidates=candidates)
    assert len(ranked) == 5


def test_render_shortlist_email_has_candidates():
    from src.engines.hr.ranking.shortlister import render_shortlist_email
    candidates = [
        {"name": "Alice", "email": "a@x.com", "combined_score": 86.0,
         "resume_score": 80, "screen_score": 90, "role": "bd_manager",
         "application_id": "app-1"},
    ]
    body = render_shortlist_email(candidates=candidates, role="bd_manager", dashboard_url="http://localhost:3000")
    assert "Alice" in body
    assert "86.0" in body or "86" in body
    assert "bd" in body.lower() and "manager" in body.lower()


@pytest.mark.asyncio
async def test_send_shortlist_to_admin_calls_smtp():
    from src.engines.hr.ranking.shortlister import Shortlister
    smtp_config = {"host": "smtp.gmail.com", "port": 587, "username": "u", "password": "p", "from_email": "hiring@example.com"}
    s = Shortlister(admin_notify_email="admin@example.com", smtp_config=smtp_config, dashboard_url="http://localhost:3000")
    with patch("src.engines.hr.ranking.shortlister.send_email_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        candidates = [{"name": "Alice", "email": "a@x.com", "combined_score": 86.0,
                       "resume_score": 80, "screen_score": 90, "role": "bd_manager", "application_id": "app-1"}]
        await s.send_shortlist(candidates=candidates, role="bd_manager")
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to_email"] == "admin@example.com"
    assert "shortlist" in call_kwargs["subject"].lower() or "Shortlist" in call_kwargs["subject"]
