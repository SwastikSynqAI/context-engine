"""Unit tests for JWT auth module."""
import pytest
from unittest.mock import MagicMock, patch


def test_create_access_token_returns_string():
    from src.api.deps.auth import create_access_token
    token = create_access_token(subject="admin@example.com")
    assert isinstance(token, str)
    assert len(token) > 20


def test_verify_token_returns_subject():
    from src.api.deps.auth import create_access_token, verify_token
    token = create_access_token(subject="admin@example.com")
    subject = verify_token(token)
    assert subject == "admin@example.com"


def test_verify_token_invalid_raises():
    from src.api.deps.auth import verify_token
    import pytest
    with pytest.raises(Exception):
        verify_token("not.a.valid.token")


def test_verify_password_correct():
    from src.api.deps.auth import hash_password, verify_password
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True


def test_verify_password_wrong():
    from src.api.deps.auth import hash_password, verify_password
    hashed = hash_password("secret123")
    assert verify_password("wrongpass", hashed) is False


def test_login_returns_token():
    from fastapi.testclient import TestClient
    from src.main import app
    from src.api.deps.auth import hash_password
    with patch("src.api.routes.auth.get_settings") as mock_settings:
        s = MagicMock()
        s.admin_email = "admin@example.com"
        s.admin_password_hash = hash_password("testpass123")
        s.jwt_secret_key = "test-secret"
        s.jwt_algorithm = "HS256"
        s.jwt_expire_minutes = 60
        mock_settings.return_value = s
        client = TestClient(app)
        resp = client.post("/auth/login", json={"email": "admin@example.com", "password": "testpass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
