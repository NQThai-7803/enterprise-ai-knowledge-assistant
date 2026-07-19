from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import (
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    UserInactiveError,
)
from app.core.security import generate_refresh_token, hash_password, hash_refresh_token, utc_now
from app.models import RefreshToken, User, UserRole
from app.services.auth_service import AuthService

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def create_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    password: str = "valid auth password",
    is_active: bool = True,
) -> User:
    user = User(
        email=email or f"auth-{uuid.uuid4()}@example.com",
        full_name="Auth User",
        hashed_password=hash_password(password),
        role=UserRole.STAFF,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def count_refresh_tokens(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(RefreshToken)) or 0


def test_active_user_can_login(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            user = await create_user(session, email="active-login@example.com")

            token_pair = await AuthService(session).login(
                email=" active-login@example.com ",
                password="valid auth password",
            )

            assert token_pair.user.id == user.id
            assert token_pair.access_token
            assert token_pair.refresh_token

    run_async(scenario())


def test_login_returns_access_and_refresh_tokens(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="token-pair@example.com")

            token_pair = await AuthService(session).login(
                email="token-pair@example.com",
                password="valid auth password",
            )

            assert len(token_pair.access_token.split(".")) == 3
            assert token_pair.refresh_token
            assert token_pair.expires_in == 900

    run_async(scenario())


def test_login_persists_only_refresh_token_hash(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="hash-only@example.com")

            token_pair = await AuthService(session).login(
                email="hash-only@example.com",
                password="valid auth password",
            )
            stored_token = await session.scalar(select(RefreshToken))

            assert stored_token is not None
            assert stored_token.token_hash == hash_refresh_token(token_pair.refresh_token)
            assert stored_token.token_hash != token_pair.refresh_token
            assert len(stored_token.token_hash) == 64

    run_async(scenario())


def test_login_does_not_store_raw_refresh_token(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="raw-not-stored@example.com")

            token_pair = await AuthService(session).login(
                email="raw-not-stored@example.com",
                password="valid auth password",
            )
            stored_token = await session.scalar(select(RefreshToken))

            assert stored_token is not None
            assert not hasattr(stored_token, "raw_token")
            assert not hasattr(stored_token, "refresh_token")
            assert stored_token.token_hash != token_pair.refresh_token

    run_async(scenario())


def test_wrong_password_returns_invalid_credentials(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="wrong-password@example.com")

            with pytest.raises(InvalidCredentialsError):
                await AuthService(session).login(
                    email="wrong-password@example.com",
                    password="wrong password",
                )

            assert await count_refresh_tokens(session) == 0

    run_async(scenario())


def test_unknown_email_returns_same_invalid_credentials(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            with pytest.raises(InvalidCredentialsError) as exc_info:
                await AuthService(session).login(
                    email="unknown@example.com",
                    password="wrong password",
                )

            assert exc_info.value.code == "INVALID_CREDENTIALS"
            assert exc_info.value.message == "Email or password is incorrect."
            assert await count_refresh_tokens(session) == 0

    run_async(scenario())


def test_inactive_user_cannot_login(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="inactive-login@example.com", is_active=False)

            with pytest.raises(UserInactiveError):
                await AuthService(session).login(
                    email="inactive-login@example.com",
                    password="valid auth password",
                )

            assert await count_refresh_tokens(session) == 0

    run_async(scenario())


def test_failed_login_does_not_create_refresh_token(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="failed-login@example.com")

            with pytest.raises(InvalidCredentialsError):
                await AuthService(session).login(
                    email="failed-login@example.com",
                    password="bad password",
                )

            assert await count_refresh_tokens(session) == 0

    run_async(scenario())


def test_valid_refresh_token_returns_new_token_pair(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="refresh-valid@example.com")
            original = await AuthService(session).login(
                email="refresh-valid@example.com",
                password="valid auth password",
            )

            refreshed = await AuthService(session).refresh(refresh_token=original.refresh_token)

            assert refreshed.access_token
            assert refreshed.refresh_token
            assert refreshed.refresh_token != original.refresh_token

    run_async(scenario())


def test_refresh_rotates_refresh_token(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="refresh-rotate@example.com")
            original = await AuthService(session).login(
                email="refresh-rotate@example.com",
                password="valid auth password",
            )

            refreshed = await AuthService(session).refresh(refresh_token=original.refresh_token)
            old_row = await session.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(original.refresh_token)
                )
            )
            new_row = await session.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(refreshed.refresh_token)
                )
            )

            assert old_row is not None
            assert old_row.revoked_at is not None
            assert new_row is not None
            assert new_row.revoked_at is None

    run_async(scenario())


def test_old_refresh_token_cannot_be_reused(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="refresh-reuse@example.com")
            original = await AuthService(session).login(
                email="refresh-reuse@example.com",
                password="valid auth password",
            )
            await AuthService(session).refresh(refresh_token=original.refresh_token)

            with pytest.raises(RefreshTokenInvalidError):
                await AuthService(session).refresh(refresh_token=original.refresh_token)

    run_async(scenario())


def test_revoked_refresh_token_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await create_user(session, email="revoked-refresh@example.com")
            token_pair = await AuthService(session).login(
                email="revoked-refresh@example.com",
                password="valid auth password",
            )
            stored_token = await session.scalar(select(RefreshToken))
            assert stored_token is not None
            stored_token.revoked_at = utc_now()
            await session.commit()

            with pytest.raises(RefreshTokenInvalidError):
                await AuthService(session).refresh(refresh_token=token_pair.refresh_token)

    run_async(scenario())


def test_expired_refresh_token_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            user = await create_user(session, email="expired-refresh@example.com")
            raw_token = generate_refresh_token()
            session.add(
                RefreshToken(
                    user_id=user.id,
                    token_hash=hash_refresh_token(raw_token),
                    expires_at=utc_now() - timedelta(seconds=1),
                )
            )
            await session.commit()

            with pytest.raises(RefreshTokenInvalidError):
                await AuthService(session).refresh(refresh_token=raw_token)

    run_async(scenario())


def test_unknown_refresh_token_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            with pytest.raises(RefreshTokenInvalidError):
                await AuthService(session).refresh(refresh_token=generate_refresh_token())

    run_async(scenario())


def test_inactive_user_cannot_refresh(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            user = await create_user(session, email="inactive-refresh@example.com")
            token_pair = await AuthService(session).login(
                email="inactive-refresh@example.com",
                password="valid auth password",
            )
            user.is_active = False
            await session.commit()

            with pytest.raises(UserInactiveError):
                await AuthService(session).refresh(refresh_token=token_pair.refresh_token)

            old_row = await session.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(token_pair.refresh_token)
                )
            )
            assert old_row is not None
            assert old_row.revoked_at is not None

    run_async(scenario())
