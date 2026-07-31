from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.audit import AuditEvent, AuditEventType, AuditOutcome, AuditTargetType
from app.core.config import Settings
from app.core.exceptions import (
    AuditEventInvalidError,
    AuditMetadataInvalidError,
    AuditReportForbiddenError,
)
from app.models import UserRole
from app.services.audit_service import AuditContext, AuditService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.in_transaction_value = False

    def in_transaction(self) -> bool:
        return self.in_transaction_value

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeRepository:
    def __init__(self) -> None:
        self.created: list[AuditEvent] = []
        self.count_calls = 0
        self.list_calls = 0
        self.fail_create = False

    async def create(self, session: FakeSession, *, event: AuditEvent, **kwargs: object) -> object:
        if self.fail_create:
            raise RuntimeError("audit insert failed")
        self.created.append(event)
        return SimpleNamespace(id=uuid4(), event=event)

    async def count_report(self, session: FakeSession, *, filters: object) -> int:
        self.count_calls += 1
        return 0

    async def list_report(
        self,
        session: FakeSession,
        *,
        filters: object,
        limit: int,
        offset: int,
    ) -> tuple[object, ...]:
        self.list_calls += 1
        return ()


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        audit_report_page_size=50,
        audit_report_max_page_size=200,
        audit_metadata_max_length=2000,
    )


def make_user(role: UserRole) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), role=role, is_active=True)


def run(coro: object) -> object:
    return asyncio.run(coro)


def test_record_success_builds_success_event() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        session = FakeSession()
        actor_id = uuid4()
        target_id = uuid4()

        await AuditService(session, settings=make_settings(), repository=repository).record_success(
            actor_user_id=actor_id,
            event_type=AuditEventType.USER_CREATED,
            target_type=AuditTargetType.USER,
            target_id=target_id,
            context=AuditContext(request_id="req-1"),
            metadata={"role": "STAFF", "status_after": "ACTIVE"},
        )

        event = repository.created[0]
        assert event.event_type is AuditEventType.USER_CREATED
        assert event.outcome is AuditOutcome.SUCCESS
        assert event.actor_user_id == actor_id
        assert event.target_id == str(target_id)
        assert event.request_id == "req-1"
        assert event.metadata == {"role": "STAFF", "status_after": "ACTIVE"}

    run(scenario())


def test_record_failure_builds_failure_event() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        await AuditService(
            FakeSession(), settings=make_settings(), repository=repository
        ).record_failure(
            actor_user_id=None,
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            error_code="INVALID_CREDENTIALS",
        )

        event = repository.created[0]
        assert event.outcome is AuditOutcome.FAILURE
        assert event.error_code == "INVALID_CREDENTIALS"
        assert event.actor_user_id is None

    run(scenario())


def test_record_failure_stores_safe_error_code_only() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        await AuditService(
            FakeSession(), settings=make_settings(), repository=repository
        ).record_failure(
            actor_user_id=None,
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            error_code="raw sql password=CONFIDENTIAL_AUDIT_PASSWORD",
        )

        assert repository.created[0].error_code == "INTERNAL_ERROR"
        assert "CONFIDENTIAL_AUDIT_PASSWORD" not in repr(repository.created[0])

    run(scenario())


def test_audit_service_does_not_log_metadata(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level(logging.INFO)
        await AuditService(
            FakeSession(), settings=make_settings(), repository=FakeRepository()
        ).record_success(
            actor_user_id=uuid4(),
            event_type=AuditEventType.FEEDBACK_UPSERTED,
            target_type=AuditTargetType.FEEDBACK,
            target_id=uuid4(),
            metadata={"rating": "HELPFUL"},
        )

    run(scenario())
    assert "HELPFUL" not in caplog.text
    assert "CONFIDENTIAL_AUDIT_REASON" not in caplog.text


def test_audit_service_does_not_commit_repository() -> None:
    async def scenario() -> None:
        session = FakeSession()
        await AuditService(
            session, settings=make_settings(), repository=FakeRepository()
        ).record_success(
            actor_user_id=uuid4(),
            event_type=AuditEventType.FEEDBACK_UPSERTED,
            target_type=AuditTargetType.FEEDBACK,
            target_id=uuid4(),
            metadata={"rating": "HELPFUL"},
        )

        assert session.commits == 0

    run(scenario())


def test_audit_service_rejects_unknown_event() -> None:
    async def scenario() -> None:
        with pytest.raises(AuditEventInvalidError):
            await AuditService(
                FakeSession(), settings=make_settings(), repository=FakeRepository()
            ).record_success(
                actor_user_id=uuid4(),
                event_type="UNKNOWN_EVENT",
            )

    run(scenario())


def test_audit_service_rejects_sensitive_metadata() -> None:
    async def scenario() -> None:
        with pytest.raises(AuditMetadataInvalidError):
            await AuditService(
                FakeSession(), settings=make_settings(), repository=FakeRepository()
            ).record_success(
                actor_user_id=uuid4(),
                event_type=AuditEventType.FEEDBACK_UPSERTED,
                target_type=AuditTargetType.FEEDBACK,
                target_id=uuid4(),
                metadata={"reason": "CONFIDENTIAL_AUDIT_REASON"},
            )

    run(scenario())


def test_audit_service_accepts_null_actor_for_system_event() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        await AuditService(
            FakeSession(), settings=make_settings(), repository=repository
        ).record_success(
            actor_user_id=None,
            event_type=AuditEventType.DOCUMENT_PROCESSING_READY
            if hasattr(AuditEventType, "DOCUMENT_PROCESSING_READY")
            else AuditEventType.DOCUMENT_UPLOADED,
            target_type=AuditTargetType.DOCUMENT,
            target_id=uuid4(),
            metadata={"actor_type": "SYSTEM"},
        )

        assert repository.created[0].actor_user_id is None
        assert repository.created[0].metadata == {"actor_type": "SYSTEM"}

    run(scenario())


def test_audit_service_does_not_create_audit_for_audit_report_read() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        result = await AuditService(
            FakeSession(), settings=make_settings(), repository=repository
        ).list_audit_report(
            current_user=make_user(UserRole.ADMIN),
            page=1,
            page_size=None,
        )

        assert result.pagination.total == 0
        assert repository.created == []
        assert repository.count_calls == 1
        assert repository.list_calls == 1

    run(scenario())


def test_audit_report_forbidden_for_non_admin() -> None:
    async def scenario() -> None:
        with pytest.raises(AuditReportForbiddenError):
            await AuditService(
                FakeSession(), settings=make_settings(), repository=FakeRepository()
            ).list_audit_report(
                current_user=make_user(UserRole.MANAGER),
                page=1,
                page_size=None,
            )

    run(scenario())
