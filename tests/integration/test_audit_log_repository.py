from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit import AuditEventType, AuditTargetType
from app.core.exceptions import InvalidCredentialsError
from app.models import AuditLog, Department, User, UserRole
from app.repositories import audit_log_repository
from app.repositories.audit_log_repository import AuditReportFilters
from app.schemas.department import DepartmentCreate
from app.services.audit_service import AuditContext, AuditService
from app.services.auth_service import AuthService
from app.services.department_service import DepartmentService

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def create_admin(session: AsyncSession) -> User:
    admin = User(
        email=f"admin-{uuid.uuid4()}@example.com",
        full_name="Admin User",
        hashed_password="not-used",
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def insert_audit_log(
    session: AsyncSession,
    *,
    action: str = "USER_CREATED",
    outcome: str = "SUCCESS",
    user_id: uuid.UUID | None = None,
    entity_type: str | None = "USER",
    entity_id: uuid.UUID | None = None,
    request_id: str | None = None,
    error_code: str | None = None,
    metadata: dict[str, object] | None = None,
    created_at: datetime | None = None,
) -> AuditLog:
    values: dict[str, object] = {
        "user_id": user_id,
        "action": action,
        "outcome": outcome,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "request_id": request_id,
        "error_code": error_code,
        "metadata_json": metadata or {},
    }
    if created_at is not None:
        values["created_at"] = created_at
    audit_log = AuditLog(**values)
    session.add(audit_log)
    await session.flush()
    return audit_log


def test_audit_log_can_be_inserted(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            target_id = uuid.uuid4()
            await AuditService(session).record_success(
                actor_user_id=None,
                event_type=AuditEventType.DOCUMENT_UPLOADED,
                target_type=AuditTargetType.DOCUMENT,
                target_id=target_id,
                context=AuditContext(request_id="audit-it-1"),
                metadata={"actor_type": "SYSTEM", "document_status": "UPLOADED"},
            )
            await session.commit()

            audit_log = await session.scalar(select(AuditLog))
            assert audit_log is not None
            assert audit_log.action == "DOCUMENT_UPLOADED"
            assert audit_log.outcome == "SUCCESS"
            assert audit_log.entity_id == target_id
            assert audit_log.request_id == "audit-it-1"
            assert audit_log.metadata_json == {
                "actor_type": "SYSTEM",
                "document_status": "UPLOADED",
            }

    run_async(scenario())


def test_audit_log_has_server_generated_id(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            audit_log = AuditLog(action="AUTH_LOGIN_FAILED", outcome="FAILURE")
            session.add(audit_log)
            await session.flush()

            assert isinstance(audit_log.id, uuid.UUID)

    run_async(scenario())


def test_audit_log_created_at_is_timezone_aware(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            audit_log = AuditLog(action="AUTH_LOGIN_FAILED", outcome="FAILURE")
            session.add(audit_log)
            await session.flush()

            assert audit_log.created_at.tzinfo is not None
            assert audit_log.created_at.tzinfo.utcoffset(audit_log.created_at) is not None

    run_async(scenario())


def test_audit_repository_has_no_update_operation() -> None:
    assert not hasattr(audit_log_repository, "update")
    assert not hasattr(audit_log_repository, "update_audit")


def test_audit_repository_has_no_delete_operation() -> None:
    assert not hasattr(audit_log_repository, "delete")
    assert not hasattr(audit_log_repository, "delete_audit")


def test_audit_api_has_no_update_route() -> None:
    from app.main import app

    audit_methods = set(app.openapi()["paths"]["/api/v1/audit-logs"])
    assert audit_methods == {"get"}


def test_audit_api_has_no_delete_route() -> None:
    from app.main import app

    audit_methods = set(app.openapi()["paths"]["/api/v1/audit-logs"])
    assert "delete" not in audit_methods
    assert "patch" not in audit_methods
    assert "put" not in audit_methods
    assert "post" not in audit_methods


def test_audit_rows_remain_unchanged_after_report_read(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            await insert_audit_log(session, user_id=admin.id, entity_id=uuid.uuid4())
            await session.commit()
            before_count = await session.scalar(select(func.count()).select_from(AuditLog))

            await AuditService(session).list_audit_report(
                current_user=admin,
                page=1,
                page_size=50,
            )
            await session.commit()
            after_count = await session.scalar(select(func.count()).select_from(AuditLog))

            assert before_count == after_count == 1

    run_async(scenario())


def test_business_change_and_success_audit_commit_together(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_admin(session)
            department = await DepartmentService(session).create_department(
                payload=DepartmentCreate(name="Audit Dept", code="AUD", description=None),
                current_user=admin,
                audit_context=AuditContext(),
            )

            assert await session.get(Department, department.id) is not None
            assert await session.scalar(select(func.count()).select_from(AuditLog)) == 1

    run_async(scenario())


def test_failure_audit_uses_separate_transaction(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            with pytest.raises(InvalidCredentialsError):
                await AuthService(session).login(
                    email="missing@example.com",
                    password="wrong-password",
                    audit_context=AuditContext(),
                )

            audit_log = await session.scalar(select(AuditLog))
            assert audit_log is not None
            assert audit_log.action == "AUTH_LOGIN_FAILED"
            assert audit_log.outcome == "FAILURE"
            assert audit_log.user_id is None
            assert audit_log.error_code == "INVALID_CREDENTIALS"
            assert "missing@example.com" not in str(audit_log.metadata_json)

    run_async(scenario())


def test_failure_audit_failure_does_not_replace_original_error(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_create(*args: object, **kwargs: object) -> AuditLog:
        raise RuntimeError("audit insert failed")

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            monkeypatch.setattr(audit_log_repository, "create", failing_create)

            with pytest.raises(Exception) as exc_info:
                await AuthService(session).login(
                    email="missing@example.com",
                    password="wrong-password",
                    audit_context=AuditContext(),
                )

            assert exc_info.value.__class__.__name__ == "InvalidCredentialsError"

    run_async(scenario())


def test_audit_count_uses_same_filters(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            await insert_audit_log(
                session,
                action="USER_CREATED",
                outcome="SUCCESS",
                entity_id=uuid.uuid4(),
                metadata={"role": "STAFF"},
            )
            await insert_audit_log(
                session,
                action="AUTH_LOGIN_FAILED",
                outcome="FAILURE",
                entity_type=None,
                error_code="INVALID_CREDENTIALS",
            )
            await session.commit()

            filters = AuditReportFilters(event_type=AuditEventType.USER_CREATED)
            rows = await audit_log_repository.list_report(
                session,
                filters=filters,
                limit=10,
                offset=0,
            )
            total = await audit_log_repository.count_report(session, filters=filters)

            assert [row.action for row in rows] == ["USER_CREATED"]
            assert total == 1

    run_async(scenario())


def test_audit_filters_are_applied_before_limit(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            base = datetime.now(UTC)
            for index in range(3):
                await insert_audit_log(
                    session,
                    action="AUTH_LOGIN_FAILED",
                    outcome="FAILURE",
                    entity_type=None,
                    created_at=base + timedelta(seconds=index),
                )
            await insert_audit_log(
                session,
                action="USER_CREATED",
                outcome="SUCCESS",
                entity_id=uuid.uuid4(),
                created_at=base + timedelta(seconds=10),
            )
            await session.commit()

            rows = await audit_log_repository.list_report(
                session,
                filters=AuditReportFilters(event_type=AuditEventType.AUTH_LOGIN_FAILED),
                limit=2,
                offset=0,
            )

            assert len(rows) == 2
            assert all(row.action == "AUTH_LOGIN_FAILED" for row in rows)

    run_async(scenario())
