from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    Feedback,
    FeedbackRating,
    User,
    UserRole,
)

pytestmark = pytest.mark.integration

CONFIDENTIAL_FEEDBACK_REASON = "CONFIDENTIAL_FEEDBACK_REASON"
CONFIDENTIAL_ASSISTANT_ANSWER = "CONFIDENTIAL_ASSISTANT_ANSWER"
CONFIDENTIAL_USER_QUESTION = "CONFIDENTIAL_USER_QUESTION"
CONFIDENTIAL_CITATION_EXCERPT = "CONFIDENTIAL_CITATION_EXCERPT"
CONFIDENTIAL_RETRIEVAL_QUERY = "CONFIDENTIAL_RETRIEVAL_QUERY"


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def create_chat_session_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner: User,
) -> ChatSession:
    async with session_factory() as session:
        now = datetime.now(UTC)
        chat = ChatSession(
            user_id=owner.id, title="Feedback session", created_at=now, updated_at=now
        )
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
        return chat


async def create_chat_message_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner: User,
    role: ChatMessageRole = ChatMessageRole.ASSISTANT,
    content: str = CONFIDENTIAL_ASSISTANT_ANSWER,
    retrieval_query: str | None = None,
) -> ChatMessage:
    async with session_factory() as session:
        now = datetime.now(UTC)
        chat = ChatSession(
            user_id=owner.id, title="Feedback session", created_at=now, updated_at=now
        )
        session.add(chat)
        await session.flush()
        message = ChatMessage(
            session_id=chat.id,
            role=role,
            content=content,
            retrieval_query=retrieval_query,
            created_at=now,
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message


async def create_feedback_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner: User,
    rating: FeedbackRating = FeedbackRating.HELPFUL,
    reason: str | None = "report reason",
    updated_at: datetime | None = None,
) -> Feedback:
    async with session_factory() as session:
        now = updated_at or datetime.now(UTC)
        chat = ChatSession(user_id=owner.id, title="Hidden title", created_at=now, updated_at=now)
        session.add(chat)
        await session.flush()
        message = ChatMessage(
            session_id=chat.id,
            role=ChatMessageRole.ASSISTANT,
            content=CONFIDENTIAL_ASSISTANT_ANSWER,
            retrieval_query=CONFIDENTIAL_RETRIEVAL_QUERY,
            created_at=now,
        )
        session.add(message)
        await session.flush()
        feedback = Feedback(
            message_id=message.id,
            user_id=owner.id,
            rating=rating,
            reason=reason,
            created_at=now,
            updated_at=now,
        )
        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)
        return feedback


async def count_feedback(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(Feedback)) or 0


def put_feedback(
    api_client: TestClient,
    headers: dict[str, str],
    message_id: uuid.UUID,
    payload: dict[str, object] | None = None,
):
    return api_client.put(
        f"/api/v1/messages/{message_id}/feedback",
        headers=headers,
        json=payload or {"rating": "HELPFUL", "reason": "Useful"},
    )


def test_owner_submits_helpful_feedback(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(api_client, make_auth_headers(owner), message.id)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["message_id"] == str(message.id)
    assert data["rating"] == "HELPFUL"
    assert data["reason"] == "Useful"
    assert "user_id" not in data
    assert "content" not in data
    assert "citations" not in data


def test_owner_submits_not_helpful_feedback(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(
        api_client,
        make_auth_headers(owner),
        message.id,
        {"rating": "NOT_HELPFUL", "reason": "Missing source"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["rating"] == "NOT_HELPFUL"


def test_blank_reason_becomes_null(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(
        api_client,
        make_auth_headers(owner),
        message.id,
        {"rating": "HELPFUL", "reason": "   "},
    )

    assert response.status_code == 200
    assert response.json()["data"]["reason"] is None


def test_feedback_update_keeps_id_created_at_and_one_row(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))
    headers = make_auth_headers(owner)

    first = put_feedback(api_client, headers, message.id, {"rating": "HELPFUL", "reason": "A"})
    second = put_feedback(
        api_client, headers, message.id, {"rating": "NOT_HELPFUL", "reason": None}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert second_data["id"] == first_data["id"]
    assert second_data["created_at"] == first_data["created_at"]
    assert second_data["rating"] == "NOT_HELPFUL"
    assert second_data["reason"] is None
    assert run_async(count_feedback(async_session_factory_for_tests)) == 1


def test_feedback_on_no_answer_message_is_allowed(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(
        create_chat_message_record(
            async_session_factory_for_tests,
            owner=owner,
            content="Khong tim thay du thong tin.",
        )
    )

    response = put_feedback(api_client, make_auth_headers(owner), message.id)

    assert response.status_code == 200


@pytest.mark.parametrize("role", [UserRole.STAFF, UserRole.ADMIN, UserRole.MANAGER])
def test_non_owner_cannot_feedback_message(
    role: UserRole,
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    actor = make_user(role=role)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(api_client, make_auth_headers(actor), message.id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEEDBACK_TARGET_NOT_FOUND"


@pytest.mark.parametrize("message_role", [ChatMessageRole.USER, ChatMessageRole.SYSTEM])
def test_wrong_role_message_cannot_receive_feedback(
    message_role: ChatMessageRole,
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    content = (
        CONFIDENTIAL_USER_QUESTION if message_role == ChatMessageRole.USER else "System hidden"
    )
    message = run_async(
        create_chat_message_record(
            async_session_factory_for_tests,
            owner=owner,
            role=message_role,
            content=content,
        )
    )

    response = put_feedback(api_client, make_auth_headers(owner), message.id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEEDBACK_TARGET_NOT_FOUND"
    assert content not in response.text


def test_missing_message_has_same_404(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)

    response = put_feedback(api_client, make_auth_headers(owner), uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEEDBACK_TARGET_NOT_FOUND"


def test_feedback_request_rejects_client_user_id(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(
        api_client,
        make_auth_headers(owner),
        message.id,
        {"rating": "HELPFUL", "reason": None, "user_id": str(uuid.uuid4())},
    )

    assert response.status_code == 422


def test_unauthenticated_user_is_rejected(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(api_client, {}, message.id)

    assert response.status_code == 401


def test_inactive_user_is_rejected(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    inactive = make_user(role=UserRole.STAFF, is_active=False)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=inactive))

    response = put_feedback(api_client, make_auth_headers(inactive), message.id)

    assert response.status_code == 403


def test_admin_lists_all_feedback(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    staff_a = make_user(role=UserRole.STAFF)
    staff_b = make_user(role=UserRole.STAFF)
    run_async(create_feedback_record(async_session_factory_for_tests, owner=staff_a))
    run_async(create_feedback_record(async_session_factory_for_tests, owner=staff_b))

    response = api_client.get("/api/v1/feedback", headers=make_auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 2
    assert len(response.json()["data"]) == 2


def test_admin_report_filters_and_privacy(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., object],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    dept = make_department()
    staff = make_user(role=UserRole.STAFF, department_id=dept.id)
    other = make_user(role=UserRole.STAFF)
    now = datetime.now(UTC)
    expected = run_async(
        create_feedback_record(
            async_session_factory_for_tests,
            owner=staff,
            rating=FeedbackRating.NOT_HELPFUL,
            reason=CONFIDENTIAL_FEEDBACK_REASON,
            updated_at=now,
        )
    )
    run_async(
        create_feedback_record(
            async_session_factory_for_tests,
            owner=other,
            rating=FeedbackRating.HELPFUL,
            updated_at=now - timedelta(days=2),
        )
    )

    response = api_client.get(
        "/api/v1/feedback",
        headers=make_auth_headers(admin),
        params={
            "rating": "NOT_HELPFUL",
            "department_id": str(dept.id),
            "user_id": str(staff.id),
            "date_from": (now - timedelta(hours=1)).isoformat(),
            "date_to": (now + timedelta(hours=1)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["id"] == str(expected.id)
    assert CONFIDENTIAL_FEEDBACK_REASON in response.text
    assert CONFIDENTIAL_ASSISTANT_ANSWER not in response.text
    assert CONFIDENTIAL_USER_QUESTION not in response.text
    assert CONFIDENTIAL_CITATION_EXCERPT not in response.text
    assert CONFIDENTIAL_RETRIEVAL_QUERY not in response.text
    assert "citations" not in body["data"][0]


def test_manager_lists_feedback_from_own_department_before_limit(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., object],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    dept_a = make_department()
    dept_b = make_department()
    manager = make_user(role=UserRole.MANAGER, department_id=dept_a.id)
    staff_a = make_user(role=UserRole.STAFF, department_id=dept_a.id)
    staff_b = make_user(role=UserRole.STAFF, department_id=dept_b.id)
    now = datetime.now(UTC)
    expected = run_async(
        create_feedback_record(
            async_session_factory_for_tests,
            owner=staff_a,
            reason="Dept A reason",
            updated_at=now - timedelta(days=1),
        )
    )
    for index in range(20):
        run_async(
            create_feedback_record(
                async_session_factory_for_tests,
                owner=staff_b,
                reason=f"Dept B reason {index}",
                updated_at=now - timedelta(minutes=index),
            )
        )

    response = api_client.get(
        "/api/v1/feedback",
        headers=make_auth_headers(manager),
        params={"page_size": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == str(expected.id)
    assert body["data"][0]["department_id"] == str(dept_a.id)
    assert "Dept B reason" not in response.text


def test_manager_cannot_override_department_scope(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., object],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    dept_a = make_department()
    dept_b = make_department()
    manager = make_user(role=UserRole.MANAGER, department_id=dept_a.id)
    staff_b = make_user(role=UserRole.STAFF, department_id=dept_b.id)
    run_async(
        create_feedback_record(async_session_factory_for_tests, owner=staff_b, reason="Other dept")
    )

    response = api_client.get(
        "/api/v1/feedback",
        headers=make_auth_headers(manager),
        params={"department_id": str(dept_b.id)},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0
    assert response.json()["data"] == []
    assert "Other dept" not in response.text


def test_manager_without_department_is_forbidden(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER, department_id=None)

    response = api_client.get("/api/v1/feedback", headers=make_auth_headers(manager))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FEEDBACK_REPORT_SCOPE_UNAVAILABLE"


def test_staff_cannot_access_feedback_report(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)

    response = api_client.get("/api/v1/feedback", headers=make_auth_headers(staff))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FEEDBACK_REPORT_FORBIDDEN"


def test_staff_feedback_submission_still_works(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=staff))

    submit = put_feedback(api_client, make_auth_headers(staff), message.id)
    report = api_client.get("/api/v1/feedback", headers=make_auth_headers(staff))

    assert submit.status_code == 200
    assert report.status_code == 403


def test_feedback_date_range_invalid(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    now = datetime.now(UTC)

    response = api_client.get(
        "/api/v1/feedback",
        headers=make_auth_headers(admin),
        params={"date_from": now.isoformat(), "date_to": (now - timedelta(days=1)).isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FEEDBACK_DATE_RANGE_INVALID"


def test_feedback_invalid_rating_returns_feedback_code(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(
        api_client,
        make_auth_headers(owner),
        message.id,
        {"rating": "NEUTRAL", "reason": None},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FEEDBACK_RATING_INVALID"


def test_feedback_long_reason_returns_feedback_code(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    message = run_async(create_chat_message_record(async_session_factory_for_tests, owner=owner))

    response = put_feedback(
        api_client,
        make_auth_headers(owner),
        message.id,
        {"rating": "HELPFUL", "reason": "x" * 1001},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FEEDBACK_REASON_TOO_LONG"


def test_feedback_report_invalid_rating_returns_feedback_code(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get(
        "/api/v1/feedback",
        headers=make_auth_headers(admin),
        params={"rating": "NEUTRAL"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FEEDBACK_RATING_INVALID"
