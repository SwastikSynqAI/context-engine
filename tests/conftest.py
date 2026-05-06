"""
Pytest configuration and shared fixtures.

Uses an in-memory SQLite database (via aiosqlite) for tests so no live
Postgres instance is needed to run the suite.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings
from src.models.entities import Base


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings with all external credentials blanked out — safe for unit tests."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="",
        hubspot_api_key="",
        gmail_user_email="",
        sheets_tenant_list_id="",
        log_level="WARNING",
    )


@pytest_asyncio.fixture
async def db_engine(test_settings):
    """Create tables in an in-memory SQLite DB for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        # pgvector Vector type not available in SQLite — patch it
        from sqlalchemy import Column, Text
        from src.models.entities import Embedding
        # Override the vector column to Text for SQLite compatibility
        Embedding.__table__.c.embedding.type = Text()

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """Provide an AsyncSession for each test, rolled back after the test."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_client(test_settings, db_engine):
    """FastAPI test client with a clean in-memory DB."""
    from src.main import app
    from src.database import get_db

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from src.config import get_settings
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    # Disable the scheduler during tests
    from src.ingestion import scheduler as sched_module
    original_start = sched_module.start_scheduler
    original_stop = sched_module.stop_scheduler
    sched_module.start_scheduler = lambda s: None
    sched_module.stop_scheduler = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
    sched_module.start_scheduler = original_start
    sched_module.stop_scheduler = original_stop
