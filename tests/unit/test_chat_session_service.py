from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import ChatSessionNotFoundError
from app.models import UserRole
from app.schemas.chat import ChatSessionCreate
from app.services.chat_session_service import ChatSessionService


class FakeSession:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.events.append("flush")

    async def commit(self) -> None:
        self.events.append("commit")

    async def refresh(self, instance: object) -> None:
        self.events.append("refresh")

    async def rollback(self) -> None:
        self.events.append("rollback")


class FakeChatSessionRepository:
    def __init__(self) -> None:
        self.create_calls: list[dict[str, object]] = []
        self.count_calls: list[dict[str, object]] = []
        self.list_calls: list[dict[str, object]] = []
        self.get_calls: list[dict[str, object]] = []
        self.detail_session = None

    async def create(self, session: FakeSession, *, user_id, title):
        self.create_calls.append({"user_id": user_id, "title": title})
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=uuid4(),
            user_id=user_id,
            title=title,
            is_archived=False,
            created_at=now,
            updated_at=now,
        )

    async def count_owned(self, session: FakeSession, *, owner_user_id, include_archived=False):
        self.count_calls.append(
            {"owner_user_id": owner_user_id, "include_archived": include_archived}
        )
        return 0

    async def list_owned(
        self,
        session: FakeSession,
        *,
        owner_user_id,
        limit,
        offset,
        include_archived=False,
    ):
        self.list_calls.append(
            {
                "owner_user_id": owner_user_id,
                "limit": limit,
                "offset": offset,
                "include_archived": include_archived,
            }
        )
        return ()

    async def get_owned_by_id(self, session: FakeSession, *, session_id, owner_user_id):
        self.get_calls.append({"session_id": session_id, "owner_user_id": owner_user_id})
        return self.detail_session


class FakeChatMessageRepository:
    def __init__(self) -> None:
        self.count_calls: list[dict[str, object]] = []
        self.list_calls: list[dict[str, object]] = []

    async def count_visible_by_session(self, session: FakeSession, *, session_id):
        self.count_calls.append({"session_id": session_id})
        return 0

    async def list_visible_by_session(self, session: FakeSession, *, session_id, limit, offset):
        self.list_calls.append({"session_id": session_id, "limit": limit, "offset": offset})
        return ()


def fake_user():
    return SimpleNamespace(id=uuid4(), role=UserRole.STAFF, is_active=True)


@pytest.mark.anyio
async def test_create_session_uses_current_user_id() -> None:
    user = fake_user()
    repository = FakeChatSessionRepository()
    session = FakeSession()

    await ChatSessionService(session, session_repository=repository).create_session(
        payload=ChatSessionCreate(title="Policy"),
        current_user=user,
    )

    assert repository.create_calls[0]["user_id"] == user.id
    assert session.events == ["flush", "commit", "refresh"]


@pytest.mark.anyio
async def test_create_session_does_not_accept_owner_from_request() -> None:
    with pytest.raises(ValidationError):
        ChatSessionCreate(title="Policy", user_id=uuid4())


@pytest.mark.anyio
async def test_create_session_defaults_to_not_archived() -> None:
    repository = FakeChatSessionRepository()
    chat_session = await ChatSessionService(
        FakeSession(),
        session_repository=repository,
    ).create_session(payload=ChatSessionCreate(), current_user=fake_user())

    assert chat_session.is_archived is False


@pytest.mark.anyio
async def test_create_session_allows_null_title() -> None:
    repository = FakeChatSessionRepository()

    await ChatSessionService(FakeSession(), session_repository=repository).create_session(
        payload=ChatSessionCreate(title="   "),
        current_user=fake_user(),
    )

    assert repository.create_calls[0]["title"] is None


@pytest.mark.anyio
async def test_list_sessions_uses_owner_filter() -> None:
    user = fake_user()
    repository = FakeChatSessionRepository()

    rows, meta = await ChatSessionService(
        FakeSession(), session_repository=repository
    ).list_sessions(
        current_user=user,
        page=1,
        page_size=None,
    )

    assert rows == ()
    assert meta.total == 0
    assert repository.count_calls[0]["owner_user_id"] == user.id
    assert repository.list_calls[0]["owner_user_id"] == user.id


@pytest.mark.anyio
async def test_get_session_detail_uses_owner_filter() -> None:
    user = fake_user()
    chat_session = SimpleNamespace(id=uuid4())
    repository = FakeChatSessionRepository()
    repository.detail_session = chat_session
    messages = FakeChatMessageRepository()
    session_id = uuid4()

    detail = await ChatSessionService(
        FakeSession(),
        session_repository=repository,
        message_repository=messages,
    ).get_session_detail(
        session_id=session_id,
        current_user=user,
        message_page=1,
    )

    assert detail.chat_session is chat_session
    assert repository.get_calls[0] == {"session_id": session_id, "owner_user_id": user.id}


@pytest.mark.anyio
async def test_session_not_found_is_sanitized() -> None:
    marker = "CONFIDENTIAL_CHAT_OWNERSHIP_MARKER"
    repository = FakeChatSessionRepository()

    with pytest.raises(ChatSessionNotFoundError) as exc_info:
        await ChatSessionService(FakeSession(), session_repository=repository).get_session_detail(
            session_id=uuid4(),
            current_user=fake_user(),
            message_page=1,
        )

    assert marker not in str(exc_info.value)


def test_chat_service_does_not_call_retrieval() -> None:
    code_names = set(ChatSessionService.create_session.__code__.co_names)
    code_names |= set(ChatSessionService.list_sessions.__code__.co_names)
    code_names |= set(ChatSessionService.get_session_detail.__code__.co_names)

    assert "retrieve" not in code_names
    assert "HybridRetrieval" not in code_names


def test_chat_service_does_not_call_llm() -> None:
    code_names = set(ChatSessionService.create_session.__code__.co_names)
    code_names |= set(ChatSessionService.list_sessions.__code__.co_names)
    code_names |= set(ChatSessionService.get_session_detail.__code__.co_names)

    assert "openai" not in code_names
    assert "generate_answer" not in code_names
