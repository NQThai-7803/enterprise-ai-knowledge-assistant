from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password, verify_password
from app.models import Department, User, UserRole

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def _create_department(session: AsyncSession, *, name: str, code: str) -> Department:
    department = Department(name=name, code=code)
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


def test_create_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await _create_department(
                session,
                name=f"Engineering {uuid.uuid4()}",
                code=f"ENG-{uuid.uuid4().hex[:8]}",
            )

            saved_department = await session.get(Department, department.id)
            assert saved_department is not None
            assert saved_department.name == department.name

    run_async(scenario())


def test_create_user_with_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await _create_department(
                session,
                name=f"Support {uuid.uuid4()}",
                code=f"SUP-{uuid.uuid4().hex[:8]}",
            )
            user = User(
                email=f"staff-{uuid.uuid4()}@example.com",
                full_name="Staff User",
                hashed_password=hash_password("integration password"),
                role=UserRole.STAFF,
                department_id=department.id,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            assert user.department_id == department.id
            assert user.role == UserRole.STAFF

    run_async(scenario())


def test_create_admin_without_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = User(
                email=f"admin-{uuid.uuid4()}@example.com",
                full_name="Admin User",
                hashed_password=hash_password("integration password"),
                role=UserRole.ADMIN,
                department_id=None,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

            assert admin.department_id is None
            assert admin.is_active is True

    run_async(scenario())


def test_duplicate_department_name_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            name = f"Duplicate Name {uuid.uuid4()}"
            session.add(Department(name=name, code=f"DN-{uuid.uuid4().hex[:8]}"))
            await session.commit()

            session.add(Department(name=name, code=f"DN-{uuid.uuid4().hex[:8]}"))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

    run_async(scenario())


def test_duplicate_department_code_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            code = f"DC-{uuid.uuid4().hex[:8]}"
            session.add(Department(name=f"Department {uuid.uuid4()}", code=code))
            await session.commit()

            session.add(Department(name=f"Department {uuid.uuid4()}", code=code))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

    run_async(scenario())


def test_duplicate_user_email_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            email = f"duplicate-{uuid.uuid4()}@example.com"
            session.add(
                User(
                    email=email,
                    full_name="First User",
                    hashed_password=hash_password("integration password"),
                    role=UserRole.STAFF,
                )
            )
            await session.commit()

            session.add(
                User(
                    email=email,
                    full_name="Second User",
                    hashed_password=hash_password("integration password"),
                    role=UserRole.STAFF,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

    run_async(scenario())


def test_user_password_is_stored_as_hash(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            password = "integration password"
            user = User(
                email=f"hashed-{uuid.uuid4()}@example.com",
                full_name="Hashed User",
                hashed_password=hash_password(password),
                role=UserRole.STAFF,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            assert user.hashed_password != password
            assert verify_password(password, user.hashed_password)

    run_async(scenario())


def test_deleting_department_sets_user_department_to_null(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await _create_department(
                session,
                name=f"Delete Target {uuid.uuid4()}",
                code=f"DEL-{uuid.uuid4().hex[:8]}",
            )
            user = User(
                email=f"set-null-{uuid.uuid4()}@example.com",
                full_name="Set Null User",
                hashed_password=hash_password("integration password"),
                role=UserRole.MANAGER,
                department_id=department.id,
            )
            session.add(user)
            await session.commit()
            user_id = user.id

            await session.delete(department)
            await session.commit()

            saved_user = await session.scalar(select(User).where(User.id == user_id))
            assert saved_user is not None
            assert saved_user.department_id is None

    run_async(scenario())
