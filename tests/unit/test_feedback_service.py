from __future__ import annotations

import asyncio
import inspect
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.config import Settings
from app.core.exceptions import (
    FeedbackReportForbiddenError,
    FeedbackReportScopeUnavailableError,
    FeedbackTargetNotFoundError,
)
from app.models import AuditLog, FeedbackRating, User, UserRole
from app.repositories.feedback_repository import FeedbackReportRow, FeedbackRow
from app.services.feedback_service import FeedbackService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeRepository:
    def __init__(self, *, target_id: uuid.UUID | None = None) -> None:
        self.target_id = target_id or uuid.uuid4()
        self.get_target_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.upsert_calls: list[tuple[uuid.UUID, uuid.UUID, FeedbackRating, str | None]] = []
        self.count_user: User | None = None
        self.list_user: User | None = None

    async def get_owned_assistant_message_id(
        self,
        session: object,
        *,
        message_id: uuid.UUID,
        owner_user_id: uuid.UUID,
    ) -> uuid.UUID | None:
        self.get_target_calls.append((message_id, owner_user_id))
        return self.target_id

    async def upsert_owned_message_feedback(
        self,
        session: object,
        *,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: FeedbackRating,
        reason: str | None,
    ) -> FeedbackRow:
        self.upsert_calls.append((message_id, user_id, rating, reason))
        now = datetime.now(UTC)
        return FeedbackRow(
            id=uuid.uuid4(),
            message_id=message_id,
            user_id=user_id,
            rating=rating,
            reason=reason,
            created_at=now,
            updated_at=now,
        )

    async def count_report(self, session: object, *, current_user: User, filters: object) -> int:
        self.count_user = current_user
        return 1

    async def list_report(
        self,
        session: object,
        *,
        current_user: User,
        filters: object,
        limit: int,
        offset: int,
    ) -> tuple[FeedbackReportRow, ...]:
        self.list_user = current_user
        now = datetime.now(UTC)
        return (
            FeedbackReportRow(
                id=uuid.uuid4(),
                message_id=uuid.uuid4(),
                user_id=current_user.id,
                department_id=current_user.department_id,
                rating=FeedbackRating.HELPFUL,
                reason="Useful",
                created_at=now,
                updated_at=now,
            ),
        )


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


def make_settings() -> Settings:
    return Settings(_env_file=None, feedback_report_page_size=20, feedback_report_max_page_size=100)


def make_user(*, role: UserRole = UserRole.STAFF, department_id: uuid.UUID | None = None) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4()}@example.com",
        full_name="Test User",
        hashed_password="hash",
        role=role,
        department_id=department_id,
        is_active=True,
    )


def test_upsert_uses_current_user_id() -> None:
    async def scenario() -> None:
        session = FakeSession()
        repository = FakeRepository()
        service = FeedbackService(session, settings=make_settings(), repository=repository)
        current_user = make_user()
        message_id = uuid.uuid4()

        await service.upsert_feedback(
            message_id=message_id,
            current_user=current_user,
            rating=FeedbackRating.HELPFUL,
            reason="  good  ",
        )

        assert repository.get_target_calls == [(message_id, current_user.id)]
        assert repository.upsert_calls[0][1] == current_user.id
        assert repository.upsert_calls[0][3] == "good"
        assert session.commits == 1

    run_async(scenario())


def test_upsert_does_not_accept_user_from_request() -> None:
    signature = inspect.signature(FeedbackService.upsert_feedback)
    assert "user_id" not in signature.parameters


def test_upsert_requires_owned_assistant_message() -> None:
    async def scenario() -> None:
        session = FakeSession()
        repository = FakeRepository(target_id=None)
        repository.target_id = None
        service = FeedbackService(session, settings=make_settings(), repository=repository)

        with pytest.raises(FeedbackTargetNotFoundError):
            await service.upsert_feedback(
                message_id=uuid.uuid4(),
                current_user=make_user(),
                rating=FeedbackRating.HELPFUL,
                reason=None,
            )

        assert repository.upsert_calls == []
        assert session.rollbacks == 1

    run_async(scenario())


def test_upsert_does_not_call_llm() -> None:
    assert not hasattr(FeedbackService, "llm_provider")
    assert "llm" not in inspect.signature(FeedbackService.__init__).parameters


def test_upsert_does_not_call_retrieval() -> None:
    assert "retrieval" not in inspect.signature(FeedbackService.__init__).parameters


def test_report_admin_uses_global_scope() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        service = FeedbackService(FakeSession(), settings=make_settings(), repository=repository)
        admin = make_user(role=UserRole.ADMIN)

        result = await service.list_feedback_report(current_user=admin, page=1, page_size=None)

        assert repository.count_user is admin
        assert repository.list_user is admin
        assert result.pagination.total == 1

    run_async(scenario())


def test_report_manager_uses_department_scope() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        service = FeedbackService(FakeSession(), settings=make_settings(), repository=repository)
        department_id = uuid.uuid4()
        manager = make_user(role=UserRole.MANAGER, department_id=department_id)

        await service.list_feedback_report(current_user=manager, page=1, page_size=None)

        assert repository.count_user is manager
        assert repository.list_user is manager

    run_async(scenario())


def test_report_staff_is_forbidden() -> None:
    async def scenario() -> None:
        service = FeedbackService(
            FakeSession(), settings=make_settings(), repository=FakeRepository()
        )

        with pytest.raises(FeedbackReportForbiddenError):
            await service.list_feedback_report(
                current_user=make_user(role=UserRole.STAFF),
                page=1,
                page_size=None,
            )

    run_async(scenario())


def test_manager_without_department_is_forbidden() -> None:
    async def scenario() -> None:
        service = FeedbackService(
            FakeSession(), settings=make_settings(), repository=FakeRepository()
        )

        with pytest.raises(FeedbackReportScopeUnavailableError):
            await service.list_feedback_report(
                current_user=make_user(role=UserRole.MANAGER, department_id=None),
                page=1,
                page_size=None,
            )

    run_async(scenario())


def audit_logs_from(session: FakeSession) -> list[AuditLog]:
    return [item for item in session.added if isinstance(item, AuditLog)]


def test_feedback_upsert_creates_audit() -> None:
    async def scenario() -> None:
        session = FakeSession()
        service = FeedbackService(session, settings=make_settings(), repository=FakeRepository())

        await service.upsert_feedback(
            message_id=uuid.uuid4(),
            current_user=make_user(),
            rating=FeedbackRating.HELPFUL,
            reason=None,
        )

        audit_logs = audit_logs_from(session)
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "FEEDBACK_UPSERTED"
        assert audit_logs[0].outcome == "SUCCESS"
        assert audit_logs[0].entity_type == "FEEDBACK"

    run_async(scenario())


def test_feedback_update_creates_audit() -> None:
    async def scenario() -> None:
        session = FakeSession()
        service = FeedbackService(session, settings=make_settings(), repository=FakeRepository())

        await service.upsert_feedback(
            message_id=uuid.uuid4(),
            current_user=make_user(),
            rating=FeedbackRating.NOT_HELPFUL,
            reason="second vote",
        )

        assert audit_logs_from(session)[0].action == "FEEDBACK_UPSERTED"

    run_async(scenario())


def test_feedback_audit_records_rating() -> None:
    async def scenario() -> None:
        session = FakeSession()
        service = FeedbackService(session, settings=make_settings(), repository=FakeRepository())

        await service.upsert_feedback(
            message_id=uuid.uuid4(),
            current_user=make_user(),
            rating=FeedbackRating.NOT_HELPFUL,
            reason="CONFIDENTIAL_AUDIT_REASON",
        )

        assert audit_logs_from(session)[0].metadata_json == {"rating": "NOT_HELPFUL"}

    run_async(scenario())


def test_feedback_audit_has_no_reason() -> None:
    async def scenario() -> None:
        marker = "CONFIDENTIAL_AUDIT_REASON"
        session = FakeSession()
        service = FeedbackService(session, settings=make_settings(), repository=FakeRepository())

        await service.upsert_feedback(
            message_id=uuid.uuid4(),
            current_user=make_user(),
            rating=FeedbackRating.HELPFUL,
            reason=marker,
        )

        assert marker not in str(audit_logs_from(session)[0].metadata_json)

    run_async(scenario())


def test_feedback_audit_has_no_message_content() -> None:
    async def scenario() -> None:
        marker = "CONFIDENTIAL_AUDIT_ANSWER"
        session = FakeSession()
        service = FeedbackService(session, settings=make_settings(), repository=FakeRepository())

        await service.upsert_feedback(
            message_id=uuid.uuid4(),
            current_user=make_user(),
            rating=FeedbackRating.HELPFUL,
            reason=marker,
        )

        assert marker not in str(audit_logs_from(session)[0].metadata_json)

    run_async(scenario())


def test_feedback_failure_does_not_create_success_audit() -> None:
    async def scenario() -> None:
        session = FakeSession()
        repository = FakeRepository(target_id=None)
        repository.target_id = None
        service = FeedbackService(session, settings=make_settings(), repository=repository)

        with pytest.raises(FeedbackTargetNotFoundError):
            await service.upsert_feedback(
                message_id=uuid.uuid4(),
                current_user=make_user(),
                rating=FeedbackRating.HELPFUL,
                reason=None,
            )

        assert audit_logs_from(session) == []
        assert session.rollbacks == 1

    run_async(scenario())
