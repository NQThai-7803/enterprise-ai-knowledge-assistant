from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.security import verify_password
from app.models import User, UserRole
from app.scripts.seed_admin import (
    ADMIN_CREATED_MESSAGE,
    ADMIN_EXISTS_MESSAGE,
    SeedAdminError,
    seed_development_admin,
)

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def make_settings(*, email: str, password: str, app_env: str = "test") -> Settings:
    return Settings(
        app_env=app_env,
        app_debug=app_env != "production",
        secret_key="test-secret-key-for-seed-admin-123456789",
        database_url="postgresql+asyncpg://app_user:change-me-for-local-development@localhost:5432/enterprise_ai",
        dev_admin_email=email,
        dev_admin_full_name="Development Admin",
        dev_admin_password=password,
        celery_broker_url=(
            "redis://redis.example.internal:6379/1"
            if app_env == "production"
            else "redis://localhost:6379/1"
        ),
        celery_result_backend=(
            "redis://redis.example.internal:6379/2"
            if app_env == "production"
            else "redis://localhost:6379/2"
        ),
    )


def test_seed_admin_first_run_creates_admin(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        password = "valid seed password"
        raw_email = f"  ADMIN-{uuid.uuid4()}@EXAMPLE.COM  "
        settings = make_settings(email=raw_email, password=password)

        message = await seed_development_admin(
            settings=settings,
            session_factory=async_session_factory_for_tests,
            prompt_for_password=False,
        )

        async with async_session_factory_for_tests() as session:
            users = (await session.scalars(select(User))).all()
            assert len(users) == 1
            admin = users[0]
            assert message == ADMIN_CREATED_MESSAGE
            assert admin.email == raw_email.strip().lower()
            assert admin.role == UserRole.ADMIN
            assert admin.department_id is None
            assert admin.is_active is True
            assert admin.hashed_password != password
            assert verify_password(password, admin.hashed_password)

    run_async(scenario())


def test_seed_admin_second_run_is_idempotent(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        settings = make_settings(
            email=f"idempotent-{uuid.uuid4()}@example.com",
            password="valid seed password",
        )

        first_message = await seed_development_admin(
            settings=settings,
            session_factory=async_session_factory_for_tests,
            prompt_for_password=False,
        )
        second_message = await seed_development_admin(
            settings=settings,
            session_factory=async_session_factory_for_tests,
            prompt_for_password=False,
        )

        async with async_session_factory_for_tests() as session:
            users = (await session.scalars(select(User))).all()
            assert first_message == ADMIN_CREATED_MESSAGE
            assert second_message == ADMIN_EXISTS_MESSAGE
            assert len(users) == 1

    run_async(scenario())


def test_seed_admin_existing_non_admin_is_not_promoted(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        email = f"non-admin-{uuid.uuid4()}@example.com"
        async with async_session_factory_for_tests() as session:
            session.add(
                User(
                    email=email,
                    full_name="Staff User",
                    hashed_password="already-hashed-value",
                    role=UserRole.STAFF,
                )
            )
            await session.commit()

        settings = make_settings(email=email, password="valid seed password")
        with pytest.raises(SeedAdminError):
            await seed_development_admin(
                settings=settings,
                session_factory=async_session_factory_for_tests,
                prompt_for_password=False,
            )

        async with async_session_factory_for_tests() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            assert user.role == UserRole.STAFF

    run_async(scenario())


def test_seed_admin_short_password_is_rejected_without_creating_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        settings = make_settings(
            email=f"short-password-{uuid.uuid4()}@example.com",
            password="too-short",
        )

        with pytest.raises(SeedAdminError):
            await seed_development_admin(
                settings=settings,
                session_factory=async_session_factory_for_tests,
                prompt_for_password=False,
            )

        async with async_session_factory_for_tests() as session:
            users = (await session.scalars(select(User))).all()
            assert users == []

    run_async(scenario())


def test_seed_admin_production_environment_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        settings = make_settings(
            email=f"production-{uuid.uuid4()}@example.com",
            password="valid seed password",
            app_env="production",
        )

        with pytest.raises(SeedAdminError):
            await seed_development_admin(
                settings=settings,
                session_factory=async_session_factory_for_tests,
                prompt_for_password=False,
            )

        async with async_session_factory_for_tests() as session:
            users = (await session.scalars(select(User))).all()
            assert users == []

    run_async(scenario())
