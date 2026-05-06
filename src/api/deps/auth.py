"""
JWT auth helpers and FastAPI dependency.

Single admin user (Admin) — credentials come from settings.
No user table needed: admin_email + bcrypt hash in .env.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import bcrypt as _bcrypt_lib
from jose import JWTError, jwt

from src.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())


def create_access_token(*, subject: str, settings: Settings | None = None) -> str:
    if settings is None:
        settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str, settings: Settings | None = None) -> str:
    if settings is None:
        settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject: str = payload.get("sub", "")
        if not subject:
            raise ValueError("Missing subject")
        return subject
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    """FastAPI dependency — raises 401 if not a valid admin JWT."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        subject = verify_token(credentials.credentials, settings)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if subject != settings.admin_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return subject
