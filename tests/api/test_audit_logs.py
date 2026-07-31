from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AuditLog, User, UserRole

pytestmark = pytest.mark.integration


CONFIDENTIAL_AUDIT_PASSWORD = "CONFIDENTIAL_AUDIT_PASSWORD"
CONFIDENTIAL_AUDIT_TOKEN = "CONFIDENTIAL_AUDIT_TOKEN"
CONFIDENTIAL_AUDIT_QUESTION = "CONFIDENTIAL_AUDIT_QUESTION"
CONFIDENTIAL_AUDIT_ANSWER = "CONFIDENTIAL_AUDIT_ANSWER"
CONFIDENTIAL_AUDIT_REASON = "CONFIDENTIAL_AUDIT_REASON"
CONFIDENTIAL_AUDIT_EXCERPT = "CONFIDENTIAL_AUDIT_EXCERPT"
CONFIDENTIAL_AUDIT_FILENAME = "CONFIDENTIAL_AUDIT_FILENAME"
CONFIDENTIAL_AUDIT_STORAGE_KEY = "CONFIDENTIAL_AUDIT_STORAGE_KEY"


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def create_audit_log(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    actor: User | None = None,
    action: str = "USER_CREATED",
    outcome: str = "SUCCESS",
    entity_type: str | None = "USER",
    entity_id: uuid.UUID | None = None,
    request_id: str | None = None,
    error_code: str | None = None,
    metadata: dict[str, object] | None = None,
    created_at: datetime | None = None,
    id: uuid.UUID | None = None,
) -> AuditLog:
    async with session_factory() as session:
        values: dict[str, object] = {
            "user_id": actor.id if actor is not None else None,
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
        if id is not None:
            values["id"] = id
        audit_log = AuditLog(**values)
        session.add(audit_log)
        await session.commit()
        await session.refresh(audit_log)
        return audit_log


def get_audit_logs(api_client: TestClient, headers: dict[str, str], **params: object):
    return api_client.get("/api/v1/audit-logs", headers=headers, params=params)


def test_admin_lists_audit_logs(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    audit_log = run_async(create_audit_log(async_session_factory_for_tests, actor=admin))

    response = get_audit_logs(api_client, make_auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(audit_log.id)


def test_admin_report_returns_200(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = get_audit_logs(api_client, make_auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_admin_report_pagination(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    for _ in range(3):
        run_async(create_audit_log(async_session_factory_for_tests, actor=admin))

    response = get_audit_logs(api_client, make_auth_headers(admin), page=1, page_size=2)

    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] == 3
    assert body["total_pages"] == 2


def test_admin_report_stable_order(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    created_at = datetime.now(UTC)
    first_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    second_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    run_async(
        create_audit_log(
            async_session_factory_for_tests, actor=admin, created_at=created_at, id=first_id
        )
    )
    run_async(
        create_audit_log(
            async_session_factory_for_tests, actor=admin, created_at=created_at, id=second_id
        )
    )

    response = get_audit_logs(api_client, make_auth_headers(admin))

    assert [item["id"] for item in response.json()["items"]] == [str(second_id), str(first_id)]


@pytest.mark.parametrize(
    ("param", "value", "expected"),
    [
        ("event_type", "AUTH_LOGIN_FAILED", "AUTH_LOGIN_FAILED"),
        ("outcome", "FAILURE", "AUTH_LOGIN_FAILED"),
        ("target_type", "DEPARTMENT", "DEPARTMENT_UPDATED"),
        ("error_code", "INVALID_CREDENTIALS", "AUTH_LOGIN_FAILED"),
        ("request_id", "req-filter", "AUTH_LOGIN_FAILED"),
    ],
)
def test_admin_filters_by_simple_fields(
    param: str,
    value: str,
    expected: str,
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    run_async(create_audit_log(async_session_factory_for_tests, actor=admin))
    run_async(
        create_audit_log(
            async_session_factory_for_tests,
            actor=None,
            action="AUTH_LOGIN_FAILED",
            outcome="FAILURE",
            entity_type=None,
            request_id="req-filter",
            error_code="INVALID_CREDENTIALS",
        )
    )
    run_async(
        create_audit_log(
            async_session_factory_for_tests,
            actor=admin,
            action="DEPARTMENT_UPDATED",
            entity_type="DEPARTMENT",
            entity_id=uuid.uuid4(),
        )
    )

    response = get_audit_logs(api_client, make_auth_headers(admin), **{param: value})

    assert response.status_code == 200
    assert {item["event_type"] for item in response.json()["items"]} == {expected}


def test_admin_filters_by_actor(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    other_admin = make_user(role=UserRole.ADMIN)
    run_async(create_audit_log(async_session_factory_for_tests, actor=admin))
    run_async(create_audit_log(async_session_factory_for_tests, actor=other_admin))

    response = get_audit_logs(
        api_client, make_auth_headers(admin), actor_user_id=str(other_admin.id)
    )

    assert [item["actor_user_id"] for item in response.json()["items"]] == [str(other_admin.id)]


def test_admin_filters_by_target_id(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    target_id = uuid.uuid4()
    run_async(create_audit_log(async_session_factory_for_tests, actor=admin, entity_id=target_id))
    run_async(
        create_audit_log(async_session_factory_for_tests, actor=admin, entity_id=uuid.uuid4())
    )

    response = get_audit_logs(api_client, make_auth_headers(admin), target_id=str(target_id))

    assert [item["target_id"] for item in response.json()["items"]] == [str(target_id)]


def test_admin_filters_by_date_range(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    now = datetime.now(UTC)
    run_async(create_audit_log(async_session_factory_for_tests, actor=admin, created_at=now))
    run_async(
        create_audit_log(
            async_session_factory_for_tests,
            actor=admin,
            action="DEPARTMENT_UPDATED",
            entity_type="DEPARTMENT",
            entity_id=uuid.uuid4(),
            created_at=now - timedelta(days=2),
        )
    )

    response = get_audit_logs(
        api_client,
        make_auth_headers(admin),
        date_from=(now - timedelta(hours=1)).isoformat(),
        date_to=(now + timedelta(hours=1)).isoformat(),
    )

    assert {item["event_type"] for item in response.json()["items"]} == {"USER_CREATED"}


def test_admin_combines_filters(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    target_id = uuid.uuid4()
    run_async(
        create_audit_log(
            async_session_factory_for_tests,
            actor=admin,
            action="DEPARTMENT_UPDATED",
            entity_type="DEPARTMENT",
            entity_id=target_id,
        )
    )
    run_async(
        create_audit_log(
            async_session_factory_for_tests,
            actor=admin,
            action="DEPARTMENT_UPDATED",
            entity_type="DEPARTMENT",
            entity_id=uuid.uuid4(),
        )
    )

    response = get_audit_logs(
        api_client,
        make_auth_headers(admin),
        event_type="DEPARTMENT_UPDATED",
        target_type="DEPARTMENT",
        target_id=str(target_id),
    )

    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["target_id"] == str(target_id)


def test_admin_empty_result_returns_empty_items(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    run_async(create_audit_log(async_session_factory_for_tests, actor=admin))

    response = get_audit_logs(api_client, make_auth_headers(admin), event_type="AUTH_LOGIN_FAILED")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_invalid_date_range_returns_audit_error(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    now = datetime.now(UTC)

    response = get_audit_logs(
        api_client,
        make_auth_headers(admin),
        date_from=now.isoformat(),
        date_to=(now - timedelta(days=1)).isoformat(),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AUDIT_DATE_RANGE_INVALID"


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.STAFF])
def test_non_admin_cannot_access_audit_report(
    role: UserRole,
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=role)

    response = get_audit_logs(api_client, make_auth_headers(user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUDIT_REPORT_FORBIDDEN"


def test_unauthenticated_user_cannot_access_audit_report(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/audit-logs")

    assert response.status_code == 401


def test_inactive_admin_cannot_access_audit_report(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    inactive_admin = make_user(role=UserRole.ADMIN, is_active=False)

    response = get_audit_logs(api_client, make_auth_headers(inactive_admin))

    assert response.status_code in {401, 403, 404}


def test_non_admin_filters_do_not_bypass_role_guard(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)

    response = get_audit_logs(
        api_client,
        make_auth_headers(manager),
        event_type="USER_CREATED",
        page_size=1,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUDIT_REPORT_FORBIDDEN"


def test_audit_report_response_is_sanitized(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(
        role=UserRole.ADMIN, email="hidden-admin@example.com", full_name="Hidden Admin"
    )
    run_async(
        create_audit_log(
            async_session_factory_for_tests,
            actor=admin,
            metadata={
                "role": "ADMIN",
                "password": CONFIDENTIAL_AUDIT_PASSWORD,
                "token": CONFIDENTIAL_AUDIT_TOKEN,
                "question": CONFIDENTIAL_AUDIT_QUESTION,
                "answer": CONFIDENTIAL_AUDIT_ANSWER,
                "reason": CONFIDENTIAL_AUDIT_REASON,
                "excerpt": CONFIDENTIAL_AUDIT_EXCERPT,
                "filename": CONFIDENTIAL_AUDIT_FILENAME,
                "storage_key": CONFIDENTIAL_AUDIT_STORAGE_KEY,
            },
        )
    )

    response = get_audit_logs(api_client, make_auth_headers(admin))

    serialized = response.text
    assert response.status_code == 200
    assert response.json()["items"][0]["metadata"] == {"role": "ADMIN"}
    assert "hidden-admin@example.com" not in serialized
    assert "Hidden Admin" not in serialized
    for marker in [
        CONFIDENTIAL_AUDIT_PASSWORD,
        CONFIDENTIAL_AUDIT_TOKEN,
        CONFIDENTIAL_AUDIT_QUESTION,
        CONFIDENTIAL_AUDIT_ANSWER,
        CONFIDENTIAL_AUDIT_REASON,
        CONFIDENTIAL_AUDIT_EXCERPT,
        CONFIDENTIAL_AUDIT_FILENAME,
        CONFIDENTIAL_AUDIT_STORAGE_KEY,
    ]:
        assert marker not in serialized


def test_audit_report_read_does_not_create_audit_event(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    run_async(create_audit_log(async_session_factory_for_tests, actor=admin))

    before = run_async(count_audit_logs(async_session_factory_for_tests))
    response = get_audit_logs(api_client, make_auth_headers(admin))
    after = run_async(count_audit_logs(async_session_factory_for_tests))

    assert response.status_code == 200
    assert before == after == 1


async def count_audit_logs(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as session:
        return len((await session.scalars(select(AuditLog))).all())
