from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.models import (
    AuditLog,
    Department,
    Document,
    DocumentChunk,
    DocumentPermission,
    RefreshToken,
    User,
)


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL") or get_settings().database_url
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.skip(
            "DATABASE_URL must point to a PostgreSQL asyncpg database for integration tests."
        )
    if database_url == "postgresql+asyncpg:///enterprise_ai":
        pytest.skip("Integration tests require an explicit PostgreSQL host in DATABASE_URL.")
    if "production" in database_url.lower():
        pytest.fail("Refusing to run integration tests against a production-looking database URL.")
    return database_url


@pytest.fixture(scope="session")
def migrated_database(integration_database_url: str) -> Iterator[None]:
    env = os.environ.copy()
    env["DATABASE_URL"] = integration_database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail("Alembic migration failed before integration tests.")
    yield


@pytest.fixture(scope="session")
def async_session_factory_for_tests(
    integration_database_url: str,
    migrated_database: None,
) -> Iterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        integration_database_url,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    yield session_factory

    asyncio.run(engine.dispose())


async def _clear_database_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        await session.execute(delete(AuditLog))
        await session.execute(delete(RefreshToken))
        await session.execute(delete(DocumentPermission))
        await session.execute(delete(DocumentChunk))
        await session.execute(delete(Document))
        await session.execute(delete(User))
        await session.execute(delete(Department))
        await session.commit()


@pytest.fixture(autouse=True)
def clean_database_data(request: pytest.FixtureRequest) -> Iterator[None]:
    if request.node.get_closest_marker("integration") is None:
        yield
        return

    session_factory = request.getfixturevalue("async_session_factory_for_tests")
    asyncio.run(_clear_database_data(session_factory))
    yield
    asyncio.run(_clear_database_data(session_factory))
