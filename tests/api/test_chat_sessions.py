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
    DocumentAccessScope,
    MessageCitation,
    User,
    UserRole,
)
from tests.integration.retrieval_helpers import create_chunk, create_document, create_permission

pytestmark = pytest.mark.integration
CONFIDENTIAL_MARKER = "CONFIDENTIAL_CHAT_OWNERSHIP_MARKER"


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def create_chat_session_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner: User,
    title: str | None = "Session",
    is_archived: bool = False,
    updated_at: datetime | None = None,
    session_id: uuid.UUID | None = None,
) -> ChatSession:
    async with session_factory() as session:
        now = updated_at or datetime.now(UTC)
        values: dict[str, object] = {
            "user_id": owner.id,
            "title": title,
            "is_archived": is_archived,
            "created_at": now,
            "updated_at": now,
        }
        if session_id is not None:
            values["id"] = session_id
        chat_session = ChatSession(**values)
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)
        return chat_session


async def create_chat_message_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    chat_session: ChatSession,
    role: ChatMessageRole,
    content: str,
    created_at: datetime | None = None,
    retrieval_query: str | None = None,
    response_time_ms: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> ChatMessage:
    async with session_factory() as session:
        message = ChatMessage(
            session_id=chat_session.id,
            role=role,
            content=content,
            retrieval_query=retrieval_query,
            response_time_ms=response_time_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            created_at=created_at or datetime.now(UTC),
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message


async def count_chat_sessions(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner: User | None = None,
) -> int:
    async with session_factory() as session:
        statement = select(func.count()).select_from(ChatSession)
        if owner is not None:
            statement = statement.where(ChatSession.user_id == owner.id)
        return await session.scalar(statement) or 0


def create_session(
    session_factory: async_sessionmaker[AsyncSession],
    **kwargs: object,
) -> ChatSession:
    return run_async(create_chat_session_record(session_factory, **kwargs))


def create_message(
    session_factory: async_sessionmaker[AsyncSession],
    **kwargs: object,
) -> ChatMessage:
    return run_async(create_chat_message_record(session_factory, **kwargs))


def test_authenticated_user_creates_chat_session(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.post(
        "/api/v1/chat/sessions",
        headers=make_auth_headers(user),
        json={"title": "Quy định nghỉ phép"},
    )
    assert response.status_code == 201
    assert response.json()["data"]["title"] == "Quy định nghỉ phép"


def test_staff_can_create_chat_session(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)
    response = api_client.post("/api/v1/chat/sessions", headers=make_auth_headers(staff), json={})
    assert response.status_code == 201


def test_manager_can_create_chat_session(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)
    response = api_client.post("/api/v1/chat/sessions", headers=make_auth_headers(manager), json={})
    assert response.status_code == 201


def test_admin_can_create_chat_session(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    response = api_client.post("/api/v1/chat/sessions", headers=make_auth_headers(admin), json={})
    assert response.status_code == 201


def test_create_session_returns_201(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.post("/api/v1/chat/sessions", headers=make_auth_headers(user), json={})
    assert response.status_code == 201


def test_create_session_without_title(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.post("/api/v1/chat/sessions", headers=make_auth_headers(user), json={})
    assert response.status_code == 201
    assert response.json()["data"]["title"] is None


def test_create_session_with_title(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.post(
        "/api/v1/chat/sessions",
        headers=make_auth_headers(user),
        json={"title": "  Chính sách IT  "},
    )
    assert response.status_code == 201
    assert response.json()["data"]["title"] == "Chính sách IT"


def test_create_session_stores_current_user_as_owner(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.post("/api/v1/chat/sessions", headers=make_auth_headers(user), json={})
    session_id = uuid.UUID(response.json()["data"]["id"])

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            chat = await session.get(ChatSession, session_id)
            assert chat is not None
            assert chat.user_id == user.id

    run_async(scenario())


def test_create_session_cannot_set_different_owner(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    response = api_client.post(
        "/api/v1/chat/sessions",
        headers=make_auth_headers(user),
        json={"user_id": str(other.id)},
    )
    assert response.status_code == 422
    assert run_async(count_chat_sessions(async_session_factory_for_tests, owner=other)) == 0


def test_create_session_cannot_set_archived(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.post(
        "/api/v1/chat/sessions",
        headers=make_auth_headers(user),
        json={"is_archived": True},
    )
    assert response.status_code == 422


def test_inactive_user_cannot_create_session(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    inactive = make_user(role=UserRole.STAFF, is_active=False)
    response = api_client.post(
        "/api/v1/chat/sessions", headers=make_auth_headers(inactive), json={}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_INACTIVE"


def test_unauthenticated_user_cannot_create_session(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/chat/sessions", json={})
    assert response.status_code == 401


def test_list_returns_only_current_user_sessions(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    owned = create_session(async_session_factory_for_tests, owner=user, title="Owned")
    create_session(async_session_factory_for_tests, owner=other, title="Other")
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    ids = {item["id"] for item in response.json()["data"]}
    assert response.status_code == 200
    assert ids == {str(owned.id)}


def test_list_excludes_other_user_sessions(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    create_session(async_session_factory_for_tests, owner=other, title="Other")
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_admin_list_does_not_include_other_user_sessions(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    other = make_user(role=UserRole.STAFF)
    create_session(async_session_factory_for_tests, owner=other, title="Other")
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_manager_list_does_not_include_staff_sessions(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)
    staff = make_user(role=UserRole.STAFF)
    create_session(async_session_factory_for_tests, owner=staff, title="Staff session")
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(manager))
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_default_excludes_archived_sessions(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    active = create_session(async_session_factory_for_tests, owner=user, title="Active")
    create_session(async_session_factory_for_tests, owner=user, title="Archived", is_archived=True)
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    assert [item["id"] for item in response.json()["data"]] == [str(active.id)]


def test_list_is_ordered_by_updated_at_desc(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    older = create_session(
        async_session_factory_for_tests,
        owner=user,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = create_session(
        async_session_factory_for_tests,
        owner=user,
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    assert [item["id"] for item in response.json()["data"]] == [str(newer.id), str(older.id)]


def test_list_has_stable_tie_break(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    same_time = datetime(2026, 1, 1, tzinfo=UTC)
    low_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    high_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    create_session(
        async_session_factory_for_tests, owner=user, updated_at=same_time, session_id=low_id
    )
    create_session(
        async_session_factory_for_tests, owner=user, updated_at=same_time, session_id=high_id
    )
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    assert [item["id"] for item in response.json()["data"]] == [str(high_id), str(low_id)]


def test_list_pagination(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    for index in range(3):
        create_session(
            async_session_factory_for_tests,
            owner=user,
            title=f"Session {index}",
            updated_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index),
        )
    response = api_client.get(
        "/api/v1/chat/sessions?page=2&page_size=2",
        headers=make_auth_headers(user),
    )
    assert response.json()["meta"] == {"page": 2, "page_size": 2, "total": 3, "total_pages": 2}
    assert len(response.json()["data"]) == 1


def test_list_total_counts_only_owned_sessions(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    create_session(async_session_factory_for_tests, owner=user)
    for _ in range(20):
        create_session(async_session_factory_for_tests, owner=other)
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    assert response.json()["meta"]["total"] == 1
    assert len(response.json()["data"]) == 1


def test_list_message_count_excludes_system_messages(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.SYSTEM,
        content="System",
    )
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
    )
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="Answer",
    )
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    assert response.json()["data"][0]["message_count"] == 2


def test_empty_session_list_returns_empty_items(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.get("/api/v1/chat/sessions", headers=make_auth_headers(user))
    assert response.json()["data"] == []
    assert response.json()["meta"]["total"] == 0


def test_owner_reads_session(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user, title="Owned")
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(chat.id)


def test_owner_reads_visible_message_history(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.SYSTEM,
        content="System",
        created_at=base,
    )
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
        created_at=base + timedelta(seconds=1),
    )
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="Answer",
        created_at=base + timedelta(seconds=2),
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    messages = response.json()["data"]["messages"]
    assert [message["role"] for message in messages] == ["USER", "ASSISTANT"]
    assert [message["content"] for message in messages] == ["Question", "Answer"]


def test_session_history_returns_assistant_citations(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
        created_at=base,
    )
    assistant = create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="Answer [1]",
        created_at=base + timedelta(seconds=1),
    )

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                "history-citation-doc",
                uploader=user,
                title="Quy ch? nh?n s?",
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            chunk = await create_chunk(
                session,
                "history-citation-chunk",
                document=document,
                text="Nh?n vi?n ???c h??ng 12 ng?y ngh? ph?p.",
                page_numbers=(14,),
            )
            session.add(
                MessageCitation(
                    message_id=assistant.id,
                    document_id=document.id,
                    chunk_id=chunk.id,
                    page_number=14,
                    excerpt="Nh?n vi?n ???c h??ng 12 ng?y ngh? ph?p.",
                    relevance_score=0.87,
                    citation_order=1,
                )
            )
            await session.commit()

    run_async(scenario())

    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    messages = response.json()["data"]["messages"]

    assert response.status_code == 200
    assert messages[0]["role"] == "USER"
    assert messages[0]["citations"] == []
    assert messages[1]["role"] == "ASSISTANT"
    assert messages[1]["citations"] == [
        {
            "document_id": str(messages[1]["citations"][0]["document_id"]),
            "document_title": "Quy ch? nh?n s?",
            "chunk_id": str(messages[1]["citations"][0]["chunk_id"]),
            "page_number": 14,
            "excerpt": "Nh?n vi?n ???c h??ng 12 ng?y ngh? ph?p.",
            "relevance_score": 0.87,
            "citation_order": 1,
        }
    ]
    assert "retrieval_query" not in response.text
    assert "prompt_tokens" not in response.text


def test_revoked_historical_source_omits_citation_metadata(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    uploader = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    assistant = create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="Historical answer [1]",
    )

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                "revoked-history-citation-doc",
                uploader=uploader,
                title="Private Policy",
                access_scope=DocumentAccessScope.PRIVATE,
            )
            grant = await create_permission(
                session,
                "revoked-history-citation-grant",
                document=document,
                creator=uploader,
                user_id=user.id,
            )
            chunk = await create_chunk(
                session,
                "revoked-history-citation-chunk",
                document=document,
                text="CONFIDENTIAL_UNAUTHORIZED_CITATION private excerpt.",
                page_numbers=(3,),
            )
            session.add(
                MessageCitation(
                    message_id=assistant.id,
                    document_id=document.id,
                    chunk_id=chunk.id,
                    page_number=3,
                    excerpt="CONFIDENTIAL_UNAUTHORIZED_CITATION private excerpt.",
                    relevance_score=0.8,
                    citation_order=1,
                )
            )
            await session.delete(grant)
            await session.commit()

    run_async(scenario())

    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))

    assert response.status_code == 200
    messages = response.json()["data"]["messages"]
    assert messages[0]["content"] == "Historical answer [1]"
    assert messages[0]["citations"] == []
    assert "Private Policy" not in response.text
    assert "CONFIDENTIAL_UNAUTHORIZED_CITATION" not in response.text


def test_non_owner_receives_404(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(other))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"


def test_admin_non_owner_receives_404(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    admin = make_user(role=UserRole.ADMIN)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(admin))
    assert response.status_code == 404


def test_manager_non_owner_receives_404(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    manager = make_user(role=UserRole.MANAGER)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    response = api_client.get(
        f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(manager)
    )
    assert response.status_code == 404


def test_missing_session_receives_same_404_contract(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    non_owner_response = api_client.get(
        f"/api/v1/chat/sessions/{chat.id}",
        headers=make_auth_headers(other),
    )
    missing_response = api_client.get(
        f"/api/v1/chat/sessions/{uuid.uuid4()}",
        headers=make_auth_headers(other),
    )
    assert non_owner_response.status_code == missing_response.status_code == 404
    assert non_owner_response.json()["error"]["code"] == missing_response.json()["error"]["code"]
    assert (
        non_owner_response.json()["error"]["message"] == missing_response.json()["error"]["message"]
    )


def test_direct_uuid_guess_does_not_bypass_ownership(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    guessed = create_session(async_session_factory_for_tests, owner=owner)
    response = api_client.get(
        f"/api/v1/chat/sessions/{guessed.id}", headers=make_auth_headers(other)
    )
    assert response.status_code == 404


def test_archived_session_can_be_read_by_owner(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    archived = create_session(async_session_factory_for_tests, owner=user, is_archived=True)
    response = api_client.get(
        f"/api/v1/chat/sessions/{archived.id}",
        headers=make_auth_headers(user),
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_archived"] is True


def test_session_detail_does_not_include_owner_email(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF, email="private-owner@example.com")
    chat = create_session(async_session_factory_for_tests, owner=user)
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert "private-owner@example.com" not in response.text
    assert "user_id" not in response.text


def test_session_detail_does_not_include_retrieval_query(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
        retrieval_query=f"{CONFIDENTIAL_MARKER} retrieval",
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert "retrieval_query" not in response.text
    assert f"{CONFIDENTIAL_MARKER} retrieval" not in response.text


def test_session_detail_does_not_include_token_usage(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="Answer",
        prompt_tokens=123,
        completion_tokens=456,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert "prompt_tokens" not in response.text
    assert "completion_tokens" not in response.text


def test_system_messages_are_hidden(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.SYSTEM,
        content=CONFIDENTIAL_MARKER,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert response.json()["data"]["messages"] == []
    assert CONFIDENTIAL_MARKER not in response.text


def test_visible_messages_order_oldest_first(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Second",
        created_at=base + timedelta(seconds=2),
    )
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="First",
        created_at=base + timedelta(seconds=1),
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert [message["content"] for message in response.json()["data"]["messages"]] == [
        "First",
        "Second",
    ]


def test_message_history_pagination(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(3):
        create_message(
            async_session_factory_for_tests,
            chat_session=chat,
            role=ChatMessageRole.USER,
            content=f"Message {index}",
            created_at=base + timedelta(seconds=index),
        )
    response = api_client.get(
        f"/api/v1/chat/sessions/{chat.id}?message_page=2&message_page_size=2",
        headers=make_auth_headers(user),
    )
    body = response.json()["data"]
    assert body["message_pagination"] == {"page": 2, "page_size": 2, "total": 3, "total_pages": 2}
    assert [message["content"] for message in body["messages"]] == ["Message 2"]


def test_message_history_total_excludes_system_messages(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.SYSTEM,
        content="System",
    )
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert response.json()["data"]["message_pagination"]["total"] == 1


def test_message_history_stable_tie_break(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    same_time = datetime(2026, 1, 1, tzinfo=UTC)
    first = create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="A",
        created_at=same_time,
    )
    second = create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="B",
        created_at=same_time,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert [message["id"] for message in response.json()["data"]["messages"]] == sorted(
        [str(first.id), str(second.id)]
    )


def test_retrieval_query_is_internal(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
        retrieval_query=CONFIDENTIAL_MARKER,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert CONFIDENTIAL_MARKER not in response.text


def test_prompt_tokens_are_internal(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="Answer",
        prompt_tokens=999,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert "prompt_tokens" not in response.text


def test_completion_tokens_are_internal(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="Answer",
        completion_tokens=999,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert "completion_tokens" not in response.text


def test_message_content_is_returned_only_to_owner(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content=CONFIDENTIAL_MARKER,
    )
    owner_response = api_client.get(
        f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(owner)
    )
    other_response = api_client.get(
        f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(other)
    )
    assert CONFIDENTIAL_MARKER in owner_response.text
    assert CONFIDENTIAL_MARKER not in other_response.text


def test_non_owner_error_does_not_include_session_title(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner, title=CONFIDENTIAL_MARKER)
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(other))
    assert response.status_code == 404
    assert CONFIDENTIAL_MARKER not in response.text


def test_non_owner_error_does_not_include_message_content(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content=CONFIDENTIAL_MARKER,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(other))
    assert response.status_code == 404
    assert CONFIDENTIAL_MARKER not in response.text


def test_non_owner_logs_do_not_include_private_content(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner, title=CONFIDENTIAL_MARKER)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content=CONFIDENTIAL_MARKER,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(other))
    assert response.status_code == 404
    assert CONFIDENTIAL_MARKER not in caplog.text


def test_system_message_content_not_exposed(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.SYSTEM,
        content=CONFIDENTIAL_MARKER,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert CONFIDENTIAL_MARKER not in response.text


def test_retrieval_query_not_exposed(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=user)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
        retrieval_query=CONFIDENTIAL_MARKER,
    )
    response = api_client.get(f"/api/v1/chat/sessions/{chat.id}", headers=make_auth_headers(user))
    assert CONFIDENTIAL_MARKER not in response.text
    assert "retrieval_query" not in response.text


def test_create_session_does_not_create_messages(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    response = api_client.post("/api/v1/chat/sessions", headers=make_auth_headers(user), json={})
    session_id = uuid.UUID(response.json()["data"]["id"])

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            total = await session.scalar(
                select(func.count())
                .select_from(ChatMessage)
                .where(ChatMessage.session_id == session_id)
            )
            assert total == 0

    run_async(scenario())
