import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory


def test_database_url_uses_asyncpg_driver() -> None:
    settings = get_settings()

    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_session_factory_creates_async_session() -> None:
    session = async_session_factory()

    try:
        assert isinstance(session, AsyncSession)
    finally:
        asyncio.run(session.close())
