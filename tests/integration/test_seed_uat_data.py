from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.models import Department, User, UserRole
from app.scripts.seed_uat_data import (
    ADMIN_EMAIL,
    KNOWLEDGE_DEPARTMENT_CODE,
    MANAGER_EMAIL,
    OPERATIONS_DEPARTMENT_CODE,
    STAFF_EMAIL,
    seed_uat_data,
)

pytestmark = pytest.mark.integration

UAT_ADMIN_PASSWORD = "LocalUatAdmin!2026"
UAT_MANAGER_PASSWORD = "LocalUatManager!2026"
UAT_STAFF_PASSWORD = "LocalUatStaff!2026"
UAT_EMAILS = (ADMIN_EMAIL, MANAGER_EMAIL, STAFF_EMAIL)


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        app_debug=True,
        secret_key="test-secret-key-for-uat-seed-123456789",
        database_url="postgresql+asyncpg://app_user:test-db-password@localhost:5432/enterprise_ai",
        redis_url="redis://localhost:6379/0",
        celery_broker_url="redis://localhost:6379/1",
        celery_result_backend="redis://localhost:6379/2",
        local_storage_path=str(tmp_path / "uploads"),
        llm_enabled=False,
    )


def set_uat_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    admin_password: str = UAT_ADMIN_PASSWORD,
    manager_password: str = UAT_MANAGER_PASSWORD,
    staff_password: str = UAT_STAFF_PASSWORD,
) -> None:
    monkeypatch.setenv("UAT_SEED_ENABLED", "true")
    monkeypatch.setenv("UAT_ADMIN_PASSWORD", admin_password)
    monkeypatch.setenv("UAT_MANAGER_PASSWORD", manager_password)
    monkeypatch.setenv("UAT_STAFF_PASSWORD", staff_password)


async def users_by_email(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, User]:
    async with session_factory() as session:
        users = (await session.scalars(select(User).where(User.email.in_(UAT_EMAILS)))).all()
        return {user.email: user for user in users}


async def department_by_code(
    session_factory: async_sessionmaker[AsyncSession], code: str
) -> Department:
    async with session_factory() as session:
        department = await session.scalar(select(Department).where(Department.code == code))
        assert department is not None
        return department


def test_seed_uat_first_and_second_run_are_idempotent(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        set_uat_env(monkeypatch)
        settings = make_settings(tmp_path)

        first = await seed_uat_data(
            settings=settings,
            session_factory=async_session_factory_for_tests,
        )
        second = await seed_uat_data(
            settings=settings,
            session_factory=async_session_factory_for_tests,
        )

        users = await users_by_email(async_session_factory_for_tests)
        knowledge_department = await department_by_code(
            async_session_factory_for_tests, KNOWLEDGE_DEPARTMENT_CODE
        )

        assert first.users == second.users
        assert set(users) == set(UAT_EMAILS)
        assert users[ADMIN_EMAIL].full_name == "UAT Admin"
        assert users[ADMIN_EMAIL].role == UserRole.ADMIN
        assert users[ADMIN_EMAIL].department_id is None
        assert users[ADMIN_EMAIL].is_active is True
        assert verify_password(UAT_ADMIN_PASSWORD, users[ADMIN_EMAIL].hashed_password)
        assert users[MANAGER_EMAIL].full_name == "UAT Manager"
        assert users[MANAGER_EMAIL].role == UserRole.MANAGER
        assert users[MANAGER_EMAIL].department_id == knowledge_department.id
        assert users[MANAGER_EMAIL].is_active is True
        assert verify_password(UAT_MANAGER_PASSWORD, users[MANAGER_EMAIL].hashed_password)
        assert users[STAFF_EMAIL].full_name == "UAT Staff"
        assert users[STAFF_EMAIL].role == UserRole.STAFF
        assert users[STAFF_EMAIL].department_id == knowledge_department.id
        assert users[STAFF_EMAIL].is_active is True
        assert verify_password(UAT_STAFF_PASSWORD, users[STAFF_EMAIL].hashed_password)

    run_async(scenario())


def test_seed_uat_second_run_updates_changed_password_hashes(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        set_uat_env(monkeypatch)
        settings = make_settings(tmp_path)
        await seed_uat_data(settings=settings, session_factory=async_session_factory_for_tests)
        first_users = await users_by_email(async_session_factory_for_tests)
        first_hashes = {email: user.hashed_password for email, user in first_users.items()}
        first_ids = {email: user.id for email, user in first_users.items()}

        new_admin_password = "ChangedUatAdmin!2026"
        new_manager_password = "ChangedUatManager!2026"
        new_staff_password = "ChangedUatStaff!2026"
        set_uat_env(
            monkeypatch,
            admin_password=new_admin_password,
            manager_password=new_manager_password,
            staff_password=new_staff_password,
        )
        await seed_uat_data(settings=settings, session_factory=async_session_factory_for_tests)

        second_users = await users_by_email(async_session_factory_for_tests)
        assert {email: user.id for email, user in second_users.items()} == first_ids
        assert second_users[ADMIN_EMAIL].hashed_password != first_hashes[ADMIN_EMAIL]
        assert second_users[MANAGER_EMAIL].hashed_password != first_hashes[MANAGER_EMAIL]
        assert second_users[STAFF_EMAIL].hashed_password != first_hashes[STAFF_EMAIL]
        assert verify_password(new_admin_password, second_users[ADMIN_EMAIL].hashed_password)
        assert verify_password(new_manager_password, second_users[MANAGER_EMAIL].hashed_password)
        assert verify_password(new_staff_password, second_users[STAFF_EMAIL].hashed_password)
        assert not verify_password(UAT_ADMIN_PASSWORD, second_users[ADMIN_EMAIL].hashed_password)
        assert not verify_password(
            UAT_MANAGER_PASSWORD, second_users[MANAGER_EMAIL].hashed_password
        )
        assert not verify_password(UAT_STAFF_PASSWORD, second_users[STAFF_EMAIL].hashed_password)

    run_async(scenario())


def test_seed_uat_repairs_existing_known_users_and_preserves_unrelated_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        wrong_password_hash = hash_password("WrongUatPassword!2026")
        unrelated_password_hash = hash_password("UnrelatedPassword!2026")
        async with async_session_factory_for_tests() as session:
            legacy_department = Department(
                code="LEGACY-UAT",
                name="Legacy UAT",
                description="Wrong old department.",
            )
            unrelated_department = Department(
                code="UNRELATED",
                name="Unrelated",
                description="Must stay unchanged.",
            )
            operations_department = Department(
                code=OPERATIONS_DEPARTMENT_CODE,
                name="Old Operations",
                description="Will be corrected by seed.",
            )
            session.add_all([legacy_department, unrelated_department, operations_department])
            await session.flush()

            admin = User(
                email=ADMIN_EMAIL.upper(),
                full_name="Wrong Admin",
                hashed_password=wrong_password_hash,
                role=UserRole.STAFF,
                department_id=legacy_department.id,
                is_active=False,
            )
            manager = User(
                email=MANAGER_EMAIL,
                full_name="Wrong Manager",
                hashed_password=wrong_password_hash,
                role=UserRole.ADMIN,
                department_id=legacy_department.id,
                is_active=False,
            )
            staff = User(
                email=STAFF_EMAIL,
                full_name="Wrong Staff",
                hashed_password=wrong_password_hash,
                role=UserRole.MANAGER,
                department_id=operations_department.id,
                is_active=False,
            )
            unrelated = User(
                email="unrelated@example.test",
                full_name="Unrelated User",
                hashed_password=unrelated_password_hash,
                role=UserRole.MANAGER,
                department_id=unrelated_department.id,
                is_active=False,
            )
            session.add_all([admin, manager, staff, unrelated])
            await session.commit()
            admin_id = admin.id
            manager_id = manager.id
            staff_id = staff.id
            unrelated_id = unrelated.id
            unrelated_department_id = unrelated_department.id

        set_uat_env(monkeypatch)
        await seed_uat_data(
            settings=make_settings(tmp_path),
            session_factory=async_session_factory_for_tests,
        )

        users = await users_by_email(async_session_factory_for_tests)
        knowledge_department = await department_by_code(
            async_session_factory_for_tests, KNOWLEDGE_DEPARTMENT_CODE
        )

        assert users[ADMIN_EMAIL].id == admin_id
        assert users[ADMIN_EMAIL].email == ADMIN_EMAIL
        assert users[ADMIN_EMAIL].full_name == "UAT Admin"
        assert users[ADMIN_EMAIL].role == UserRole.ADMIN
        assert users[ADMIN_EMAIL].department_id is None
        assert users[ADMIN_EMAIL].is_active is True
        assert verify_password(UAT_ADMIN_PASSWORD, users[ADMIN_EMAIL].hashed_password)

        assert users[MANAGER_EMAIL].id == manager_id
        assert users[MANAGER_EMAIL].full_name == "UAT Manager"
        assert users[MANAGER_EMAIL].role == UserRole.MANAGER
        assert users[MANAGER_EMAIL].department_id == knowledge_department.id
        assert users[MANAGER_EMAIL].is_active is True
        assert verify_password(UAT_MANAGER_PASSWORD, users[MANAGER_EMAIL].hashed_password)

        assert users[STAFF_EMAIL].id == staff_id
        assert users[STAFF_EMAIL].full_name == "UAT Staff"
        assert users[STAFF_EMAIL].role == UserRole.STAFF
        assert users[STAFF_EMAIL].department_id == knowledge_department.id
        assert users[STAFF_EMAIL].is_active is True
        assert verify_password(UAT_STAFF_PASSWORD, users[STAFF_EMAIL].hashed_password)

        async with async_session_factory_for_tests() as session:
            unrelated = await session.get(User, unrelated_id)
            assert unrelated is not None
            assert unrelated.email == "unrelated@example.test"
            assert unrelated.full_name == "Unrelated User"
            assert unrelated.hashed_password == unrelated_password_hash
            assert unrelated.role == UserRole.MANAGER
            assert unrelated.department_id == unrelated_department_id
            assert unrelated.is_active is False

    run_async(scenario())
