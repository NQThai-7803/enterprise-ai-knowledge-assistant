from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.user_service as user_service_module
from app.core.exceptions import (
    BusinessValidationError,
    LastActiveAdminError,
    ResourceNotFoundError,
    SelfModificationNotAllowedError,
    UserEmailAlreadyExistsError,
)
from app.core.security import hash_refresh_token, utc_now, verify_password
from app.models import Department, RefreshToken, User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditContext
from app.services.user_service import UserService

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fast_hash_for_non_hashing_tests(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    if request.node.name == "test_created_user_password_is_hashed":
        return
    monkeypatch.setattr(user_service_module, "hash_password", lambda password: f"hashed:{password}")


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def create_department(session: AsyncSession, *, name: str = "Engineering") -> Department:
    department = Department(name=f"{name} {uuid.uuid4()}", code=f"D{uuid.uuid4().hex[:8]}")
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def create_user_record(
    session: AsyncSession,
    *,
    email: str | None = None,
    role: UserRole = UserRole.STAFF,
    department_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        email=email or f"user-{uuid.uuid4()}@example.com",
        full_name="Test User",
        hashed_password="not-used-by-service-test",
        role=role,
        department_id=department_id,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def user_create_payload(
    *,
    email: str = "new-user@example.com",
    role: UserRole = UserRole.STAFF,
    department_id: uuid.UUID | None,
    password: str = "StrongPassword123!",
) -> UserCreate:
    return UserCreate(
        email=email,
        full_name="New User",
        password=password,
        role=role,
        department_id=department_id,
    )


def test_admin_can_create_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)

            user = await UserService(session).create_user(
                payload=user_create_payload(department_id=department.id),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert user.id is not None
            assert user.is_active is True

    run_async(scenario())


def test_created_user_password_is_hashed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            password = "StrongPassword123!"

            user = await UserService(session).create_user(
                payload=user_create_payload(department_id=department.id, password=password),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert user.hashed_password != password
            assert verify_password(password, user.hashed_password)

    run_async(scenario())


def test_created_user_email_is_lowercase(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)

            user = await UserService(session).create_user(
                payload=user_create_payload(
                    email=" MixedCase@Example.COM ",
                    department_id=department.id,
                ),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert user.email == "mixedcase@example.com"

    run_async(scenario())


def test_create_user_rejects_duplicate_email(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            await create_user_record(
                session,
                email="duplicate@example.com",
                department_id=department.id,
            )

            with pytest.raises(UserEmailAlreadyExistsError):
                await UserService(session).create_user(
                    payload=user_create_payload(
                        email="DUPLICATE@example.com",
                        department_id=department.id,
                    ),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_create_manager_requires_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)

            with pytest.raises(BusinessValidationError):
                await UserService(session).create_user(
                    payload=user_create_payload(role=UserRole.MANAGER, department_id=None),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_create_staff_requires_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)

            with pytest.raises(BusinessValidationError):
                await UserService(session).create_user(
                    payload=user_create_payload(role=UserRole.STAFF, department_id=None),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_create_user_rejects_missing_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)

            with pytest.raises(ResourceNotFoundError):
                await UserService(session).create_user(
                    payload=user_create_payload(department_id=uuid.uuid4()),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_admin_can_create_admin_without_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)

            created = await UserService(session).create_user(
                payload=user_create_payload(role=UserRole.ADMIN, department_id=None),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert created.role == UserRole.ADMIN
            assert created.department_id is None

    run_async(scenario())


def test_admin_can_update_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            user = await create_user_record(session, department_id=department.id)

            updated = await UserService(session).update_user(
                user_id=user.id,
                payload=UserUpdate(full_name="Updated User"),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert updated.full_name == "Updated User"

    run_async(scenario())


def test_update_user_rejects_duplicate_email(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            await create_user_record(
                session,
                email="existing@example.com",
                department_id=department.id,
            )
            user = await create_user_record(session, department_id=department.id)

            with pytest.raises(UserEmailAlreadyExistsError):
                await UserService(session).update_user(
                    user_id=user.id,
                    payload=UserUpdate(email="EXISTING@example.com"),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_update_role_to_staff_requires_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            target = await create_user_record(session, role=UserRole.ADMIN, department_id=None)

            with pytest.raises(BusinessValidationError):
                await UserService(session).update_user(
                    user_id=target.id,
                    payload=UserUpdate(role=UserRole.STAFF),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_admin_can_reactivate_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            user = await create_user_record(
                session,
                department_id=department.id,
                is_active=False,
            )

            updated = await UserService(session).update_user(
                user_id=user.id,
                payload=UserUpdate(is_active=True),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert updated.is_active is True

    run_async(scenario())


def test_delete_user_soft_deactivates_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            user = await create_user_record(session, department_id=department.id)

            await UserService(session).deactivate_user(
                user_id=user.id,
                current_user=admin,
                audit_context=AuditContext(),
            )

            saved_user = await session.scalar(select(User).where(User.id == user.id))
            assert saved_user is not None
            assert saved_user.is_active is False

    run_async(scenario())


def test_delete_user_revokes_refresh_tokens(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            user = await create_user_record(session, department_id=department.id)
            raw_token = "refresh-token-for-user"
            refresh_token = RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_token),
                expires_at=utc_now() + timedelta(days=1),
            )
            session.add(refresh_token)
            await session.commit()

            await UserService(session).deactivate_user(
                user_id=user.id,
                current_user=admin,
                audit_context=AuditContext(),
            )

            saved_token = await session.scalar(
                select(RefreshToken).where(RefreshToken.user_id == user.id)
            )
            assert saved_token is not None
            assert saved_token.revoked_at is not None

    run_async(scenario())


def test_delete_user_is_idempotent(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)
            department = await create_department(session)
            user = await create_user_record(
                session,
                department_id=department.id,
                is_active=False,
            )

            await UserService(session).deactivate_user(
                user_id=user.id,
                current_user=admin,
                audit_context=AuditContext(),
            )

            saved_user = await session.get(User, user.id)
            assert saved_user is not None
            assert saved_user.is_active is False

    run_async(scenario())


def test_admin_cannot_deactivate_self(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)

            with pytest.raises(SelfModificationNotAllowedError):
                await UserService(session).deactivate_user(
                    user_id=admin.id,
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_admin_cannot_change_own_role(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user_record(session, role=UserRole.ADMIN)

            with pytest.raises(SelfModificationNotAllowedError):
                await UserService(session).update_user(
                    user_id=admin.id,
                    payload=UserUpdate(role=UserRole.STAFF),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_last_active_admin_cannot_be_deactivated(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            target_admin = await create_user_record(session, role=UserRole.ADMIN)
            actor = User(
                id=uuid.uuid4(),
                email="actor@example.com",
                full_name="Actor Admin",
                hashed_password="not-used",
                role=UserRole.ADMIN,
                is_active=True,
            )

            with pytest.raises(LastActiveAdminError):
                await UserService(session).deactivate_user(
                    user_id=target_admin.id,
                    current_user=actor,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_last_active_admin_cannot_be_demoted(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            target_admin = await create_user_record(session, role=UserRole.ADMIN)
            actor = User(
                id=uuid.uuid4(),
                email="actor@example.com",
                full_name="Actor Admin",
                hashed_password="not-used",
                role=UserRole.ADMIN,
                is_active=True,
            )
            department = await create_department(session)

            with pytest.raises(LastActiveAdminError):
                await UserService(session).update_user(
                    user_id=target_admin.id,
                    payload=UserUpdate(role=UserRole.STAFF, department_id=department.id),
                    current_user=actor,
                    audit_context=AuditContext(),
                )

    run_async(scenario())
