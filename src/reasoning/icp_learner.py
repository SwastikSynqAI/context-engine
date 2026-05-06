"""
ICPLearner — extracts and updates the Ideal Customer Profile from decision history.

Kept separate from context_engine.py so it can be called from the scheduler
independently on a weekly cadence.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.reasoning.context_engine import ContextEngine

logger = logging.getLogger(__name__)


class ICPLearner:
    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        self.settings = settings
        self.db = db
        self._engine = ContextEngine(settings, db)

    async def refresh(self):
        """Re-derive ICP from all decisions and return the profile."""
        logger.info("Refreshing ICP from decision history")
        profile = await self._engine.get_icp()
        logger.info(
            "ICP refreshed: %d industries, %d signals, confidence=%.2f, based on %d decisions",
            len(profile.industries),
            len(profile.signals),
            profile.confidence,
            profile.based_on_decisions,
        )
        return profile
