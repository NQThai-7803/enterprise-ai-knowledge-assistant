from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import (
    DepartmentCodeAlreadyExistsError,
    DepartmentInUseError,
    DepartmentNameAlreadyExistsError,
)
from app.models import Department, User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.audit_service import AuditContext
from app.services.department_service import DepartmentService

pytestmark = pytest.mark.integration


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


async def create_department_record(
    session: AsyncSession,
    *,
    name: str | None = None,
    code: str | None = None,
) -> Department:
    department = Department(
        name=name or f"Department {uuid.uuid4()}",
        code=code or f"D{uuid.uuid4().hex[:8]}",
    )
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def create_user_record(
    session: AsyncSession,
    *,
    department_id: uuid.UUID,
    is_active: bool,
) -> User:
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        full_name="Department User",
        hashed_password="not-used-by-service-test",
        role=UserRole.STAFF,
        department_id=department_id,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def test_admin_can_create_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)

            department = await DepartmentService(session).create_department(
                payload=DepartmentCreate(
                    name="Information Technology",
                    code="IT",
                    description="Internal IT",
                ),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert department.id is not None
            assert department.name == "Information Technology"

    run_async(scenario())


def test_department_code_is_stored_uppercase(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)

            department = await DepartmentService(session).create_department(
                payload=DepartmentCreate(
                    name="Information Technology", code="it", description=None
                ),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert department.code == "IT"

    run_async(scenario())


def test_duplicate_department_name_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            await create_department_record(session, name="Finance", code="FIN")

            with pytest.raises(DepartmentNameAlreadyExistsError):
                await DepartmentService(session).create_department(
                    payload=DepartmentCreate(name="Finance", code="FIN2", description=None),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_duplicate_department_code_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            await create_department_record(session, name="Finance", code="FIN")

            with pytest.raises(DepartmentCodeAlreadyExistsError):
                await DepartmentService(session).create_department(
                    payload=DepartmentCreate(name="Finance Ops", code="fin", description=None),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_admin_can_update_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)

            updated = await DepartmentService(session).update_department(
                department_id=department.id,
                payload=DepartmentUpdate(name="Updated Department"),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert updated.name == "Updated Department"

    run_async(scenario())


def test_department_update_rejects_duplicate_name(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            await create_department_record(session, name="Finance", code="FIN")
            department = await create_department_record(session, name="Engineering", code="ENG")

            with pytest.raises(DepartmentNameAlreadyExistsError):
                await DepartmentService(session).update_department(
                    department_id=department.id,
                    payload=DepartmentUpdate(name="Finance"),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_department_update_rejects_duplicate_code(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            await create_department_record(session, name="Finance", code="FIN")
            department = await create_department_record(session, name="Engineering", code="ENG")

            with pytest.raises(DepartmentCodeAlreadyExistsError):
                await DepartmentService(session).update_department(
                    department_id=department.id,
                    payload=DepartmentUpdate(code="fin"),
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_delete_department_without_active_users_succeeds(
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

            assert await session.get(Department, department.id) is None

    run_async(scenario())


def test_delete_department_with_active_users_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            await create_user_record(session, department_id=department.id, is_active=True)

            with pytest.raises(DepartmentInUseError):
                await DepartmentService(session).delete_department(
                    department_id=department.id,
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())


def test_delete_department_sets_inactive_user_department_to_null(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await create_department_record(session)
            user = await create_user_record(session, department_id=department.id, is_active=False)

            await DepartmentService(session).delete_department(
                department_id=department.id,
                current_user=admin,
                audit_context=AuditContext(),
            )
            await session.refresh(user)

            assert user.department_id is None

    run_async(scenario())
