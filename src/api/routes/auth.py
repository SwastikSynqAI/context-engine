"""
Admin auth routes — JWT login for AI Hire dashboard.

Single admin user: Admin. Credentials stored in .env.
POST /auth/login  → returns access_token
POST /auth/verify → validates token, returns email
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.deps.auth import create_access_token, verify_password, verify_token
from src.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _get_settings_dep() -> Settings:  # indirection so patch("...auth.get_settings") works at call time
    return get_settings()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, settings: Settings = Depends(_get_settings_dep)) -> TokenResponse:
    """Authenticate admin. Returns JWT on success."""
    if body.email != settings.admin_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not settings.admin_password_hash:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin password not configured")
    if not verify_password(body.password, settings.admin_password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=body.email, settings=settings)
    return TokenResponse(access_token=token)


@router.post("/verify")
async def verify(
    credentials: dict,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Verify a JWT token. Used by the dashboard on page load."""
    token = credentials.get("token", "")
    try:
        subject = verify_token(token, settings)
        return {"valid": True, "email": subject}
    except ValueError:
        return {"valid": False, "email": None}
