from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.database import get_db
from src.reasoning.context_engine import ContextEngine
from src.reasoning.decision_capture import DecisionCaptureService


async def get_context_engine(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> ContextEngine:
    return ContextEngine(settings, db)


async def get_decision_service(
    db: AsyncSession = Depends(get_db),
) -> DecisionCaptureService:
    return DecisionCaptureService(db)
