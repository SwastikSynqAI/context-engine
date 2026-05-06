"""
Tests for ApplicationService — tests pure logic without needing a real DB.
Uses a mock db session and mock entity_store.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.uploads_resumes_dir = "/tmp/test_uploads/resumes"
    s.hr_resume_score_threshold = 65.0
    return s


def test_dedup_checker_used_in_process():
    """DeduplicationChecker is used — pure logic test."""
    from src.engines.hr.inbound.deduplication import DeduplicationChecker
    checker = DeduplicationChecker()
    result = checker.check(
        incoming_name="New Person",
        incoming_email="new@example.com",
        incoming_phone=None,
        existing_candidates=[
            {"entity_id": "x", "name": "Someone Else", "email": "other@example.com", "phone": None}
        ],
    )
    assert result.is_duplicate is False


@pytest.mark.asyncio
async def test_process_new_candidate(mock_db, mock_settings):
    from src.engines.hr.inbound.form_receiver import ApplicationService
    from src.engines.hr.models import CandidateCreate

    with patch.object(ApplicationService, "_fetch_existing_candidates", new_callable=AsyncMock) as mock_fetch, \
         patch.object(ApplicationService, "_create_application", new_callable=AsyncMock) as mock_create, \
         patch.object(ApplicationService, "_log_activity", new_callable=AsyncMock), \
         patch.object(ApplicationService, "_upsert_candidate_entity", new_callable=AsyncMock) as mock_upsert:

        mock_fetch.return_value = []
        mock_create.return_value = "app-uuid-123"
        mock_upsert.return_value = "test-entity-uuid"

        service = ApplicationService(db=mock_db, settings=mock_settings)
        candidate = CandidateCreate(
            name="Rahul Gupta",
            email="rahul@example.com",
            phone="+919812345678",
            role="bd_manager",
            source="careers_form",
        )
        result = await service.process(candidate=candidate)

    assert result["entity_id"] == "test-entity-uuid"
    assert result["is_duplicate"] is False
    assert result["application_id"] == "app-uuid-123"


@pytest.mark.asyncio
async def test_process_duplicate_candidate(mock_db, mock_settings):
    from src.engines.hr.inbound.form_receiver import ApplicationService
    from src.engines.hr.models import CandidateCreate

    with patch.object(ApplicationService, "_fetch_existing_candidates", new_callable=AsyncMock) as mock_fetch, \
         patch.object(ApplicationService, "_create_application", new_callable=AsyncMock) as mock_create, \
         patch.object(ApplicationService, "_log_activity", new_callable=AsyncMock):

        mock_fetch.return_value = [
            {"entity_id": "existing-uuid", "name": "Rahul Gupta",
             "email": "rahul@example.com", "phone": "+919812345678"}
        ]
        mock_create.return_value = "app-uuid-456"

        service = ApplicationService(db=mock_db, settings=mock_settings)
        candidate = CandidateCreate(
            name="Rahul Gupta",
            email="rahul@example.com",
            role="bd_manager",
            source="careers_form",
        )
        result = await service.process(candidate=candidate)

    assert result["is_duplicate"] is True
    assert result["existing_entity_id"] == "existing-uuid"
