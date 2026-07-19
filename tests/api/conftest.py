from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_document_processing_enqueue
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import app
from app.models import Department, User, UserRole


@pytest.fixture
def api_client(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> Iterator[TestClient]:
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with async_session_factory_for_tests() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_document_processing_enqueue] = lambda: lambda document_id: True
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


async def create_department(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    name: str | None = None,
    code: str | None = None,
) -> Department:
    async with session_factory() as session:
        department = Department(
            name=name or f"Department {uuid.uuid4()}",
            code=code or f"D{uuid.uuid4().hex[:8]}",
        )
        session.add(department)
        await session.commit()
        await session.refresh(department)
        return department


async def create_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    role: UserRole,
    email: str | None = None,
    full_name: str = "API User",
    department_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> User:
    async with session_factory() as session:
        user = User(
            email=email or f"api-{uuid.uuid4()}@example.com",
            full_name=full_name,
            hashed_password="not-used-by-token-auth",
            role=role,
            department_id=department_id,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def create_test_department(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    name: str | None = None,
    code: str | None = None,
) -> Department:
    return asyncio.run(create_department(session_factory, name=name, code=code))


def create_test_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    role: UserRole,
    email: str | None = None,
    full_name: str = "API User",
    department_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> User:
    return asyncio.run(
        create_user(
            session_factory,
            role=role,
            email=email,
            full_name=full_name,
            department_id=department_id,
            is_active=is_active,
        )
    )


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def make_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> Callable[..., Department]:
    def factory(**kwargs: object) -> Department:
        return create_test_department(async_session_factory_for_tests, **kwargs)

    return factory


@pytest.fixture
def make_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> Callable[..., User]:
    def factory(**kwargs: object) -> User:
        return create_test_user(async_session_factory_for_tests, **kwargs)

    return factory


@pytest.fixture
def make_auth_headers() -> Callable[[User], dict[str, str]]:
    return auth_headers
