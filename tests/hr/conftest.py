"""HR-specific pytest fixtures."""
from __future__ import annotations
import pytest


@pytest.fixture
def sample_candidate_attrs():
    return {
        "name": "Ananya Sharma",
        "email": "ananya@example.com",
        "phone": "+919876543210",
        "role": "bd_manager",
        "source": "careers_form",
        "years_experience": 5.0,
    }
