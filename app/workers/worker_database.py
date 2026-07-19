from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    try:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()
