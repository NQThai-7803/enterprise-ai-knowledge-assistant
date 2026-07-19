import logging
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> bool:
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return result.scalar_one() == 1
    except Exception as exc:
        logger.warning(
            "Database readiness check failed.",
            extra={"error_type": exc.__class__.__name__},
        )
        return False


async def dispose_database_engine() -> None:
    await engine.dispose()
