from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.user_service as user_service_module
from app.core.exceptions import UserEmailAlreadyExistsError
from app.models import AuditLog, Department, User, UserRole
from app.repositories import audit_log_repository
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditAction, AuditContext
from app.services.department_service import DepartmentService
from app.services.user_service import UserService

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fast_hash_for_audit_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(user_service_module, "hash_password", lambda password: f"hashed:{password}")


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def create_admin(session: AsyncSession) -> User:
    admin = User(
        email=f"admin-{uuid.uuid4()}@example.com",
        full_name="Admin User",
        hashed_password="not-used-by-service-test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def create_department_record(session: AsyncSession) -> Department:
    department = Department(name=f"Department {uuid.uuid4()}", code=f"D{uuid.uuid4().hex[:8]}")
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def create_user_record(
    session: AsyncSession,
    *,
    department_id: uuid.UUID,
    is_active: bool = True,
) -> User:
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        full_name="Audit User",
        hashed_password="not-used-by-service-test",
        role=UserRole.STAFF,
        department_id=department_id,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def count_audit_logs(session: AsyncSession, action: AuditAction | None = None) -> int:
    statement = select(func.count()).select_from(AuditLog)
    if action is not None:
        statement = statement.where(AuditLog.action == action.value)
    return await session.scalar(statement) or 0


async def latest_audit_log(session: AsyncSession) -> AuditLog:
    audit_log = await session.scalar(select(AuditLog).order_by(AuditLog.created_at.desc()))
    assert audit_log is not None
    return audit_log


def user_create_payload(department_id: uuid.UUID, email: str | None = None) -> UserCreate:
    return UserCreate(
        email=email or f"created-{uuid.uuid4()}@example.com",
        full_name="Created User",
        password="StrongPassword123!",
        role=UserRole.STAFF,
        department_id=department_id,
    )


def test_create_user_creates_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)

            await UserService(session).create_user(
                payload=user_create_payload(department.id),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await count_audit_logs(session, AuditAction.USER_CREATED) == 1

    run_async(scenario())


def test_update_user_creates_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            user = await create_user_record(session, department_id=department.id)

            await UserService(session).update_user(
                user_id=user.id,
                payload=UserUpdate(full_name="Updated Audit User"),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await count_audit_logs(session, AuditAction.USER_UPDATED) == 1

    run_async(scenario())


def test_deactivate_user_creates_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            user = await create_user_record(session, department_id=department.id)

            await UserService(session).deactivate_user(
                user_id=user.id,
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await count_audit_logs(session, AuditAction.USER_DEACTIVATED) == 1

    run_async(scenario())


def test_reactivate_user_creates_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            user = await create_user_record(
                session,
                department_id=department.id,
                is_active=False,
            )

            await UserService(session).update_user(
                user_id=user.id,
                payload=UserUpdate(is_active=True),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await count_audit_logs(session, AuditAction.USER_REACTIVATED) == 1

    run_async(scenario())


def test_create_department_creates_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)

            await DepartmentService(session).create_department(
                payload=DepartmentCreate(name="Finance", code="FIN", description=None),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await count_audit_logs(session, AuditAction.DEPARTMENT_CREATED) == 1

    run_async(scenario())


def test_update_department_creates_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)

            await DepartmentService(session).update_department(
                department_id=department.id,
                payload=DepartmentUpdate(name="Updated Department"),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await count_audit_logs(session, AuditAction.DEPARTMENT_UPDATED) == 1

    run_async(scenario())


def test_delete_department_creates_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)

            await DepartmentService(session).delete_department(
                department_id=department.id,
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await count_audit_logs(session, AuditAction.DEPARTMENT_DELETED) == 1

    run_async(scenario())


def test_failed_duplicate_create_does_not_create_audit_log(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            await create_user_record(session, department_id=department.id)
            existing_user = await session.scalar(select(User).where(User.role == UserRole.STAFF))
            assert existing_user is not None

            with pytest.raises(UserEmailAlreadyExistsError):
                await UserService(session).create_user(
                    payload=user_create_payload(department.id, email=existing_user.email),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

            assert await count_audit_logs(session) == 0

    run_async(scenario())


def test_audit_metadata_does_not_contain_password(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)

            await UserService(session).create_user(
                payload=user_create_payload(department.id),
                current_user=admin,
                audit_context=AuditContext(),
            )
            audit_log = await latest_audit_log(session)

            assert "password" not in str(audit_log.metadata_json).lower()

    run_async(scenario())


def test_audit_metadata_does_not_contain_password_hash(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            user = await create_user_record(session, department_id=department.id)

            await UserService(session).update_user(
                user_id=user.id,
                payload=UserUpdate(full_name="No Hash Metadata"),
                current_user=admin,
                audit_context=AuditContext(),
            )
            audit_log = await latest_audit_log(session)

            assert "hashed_password" not in str(audit_log.metadata_json).lower()
            assert "password_hash" not in str(audit_log.metadata_json).lower()

    run_async(scenario())


def test_audit_insert_failure_rolls_back_business_mutation(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_create(*args: object, **kwargs: object) -> AuditLog:
        raise RuntimeError("audit insert failed")

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            email = "rollback-user@example.com"
            monkeypatch.setattr(audit_log_repository, "create", failing_create)

            with pytest.raises(RuntimeError):
                await UserService(session).create_user(
                    payload=user_create_payload(department.id, email=email),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

            assert await session.scalar(select(User).where(User.email == email)) is None

    run_async(scenario())
