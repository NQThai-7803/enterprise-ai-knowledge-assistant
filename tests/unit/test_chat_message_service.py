from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.exceptions import (
    ChatMessageContentInvalidError,
    ChatMessageContentTooLongError,
    ChatMessageMetricsInvalidError,
)
from app.models import ChatMessageRole
from app.services.chat_message_service import ChatMessageService


class FakeSession:
    def __init__(self) -> None:
        self.flushed = False
        self.committed = False

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True


class FakeMessageRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(
        self,
        session: FakeSession,
        *,
        chat_session,
        role,
        content,
        retrieval_query,
        response_time_ms,
        prompt_tokens,
        completion_tokens,
        created_at,
    ):
        self.calls.append(
            {
                "chat_session": chat_session,
                "role": role,
                "content": content,
                "retrieval_query": retrieval_query,
                "response_time_ms": response_time_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "created_at": created_at,
            }
        )
        return SimpleNamespace(
            id=uuid4(),
            session_id=chat_session.id,
            role=role,
            content=content,
            created_at=created_at,
        )


class FakeSessionRepository:
    def __init__(self) -> None:
        self.touches: list[datetime] = []

    async def touch_updated_at(self, chat_session, *, updated_at) -> None:
        self.touches.append(updated_at)
        chat_session.updated_at = updated_at


def chat_session():
    return SimpleNamespace(id=uuid4(), updated_at=datetime(2026, 1, 1, tzinfo=UTC))


def service(
    *,
    settings: Settings | None = None,
    message_repository: FakeMessageRepository | None = None,
    session_repository: FakeSessionRepository | None = None,
) -> ChatMessageService:
    return ChatMessageService(
        settings=settings,
        message_repository=message_repository or FakeMessageRepository(),
        session_repository=session_repository or FakeSessionRepository(),
    )


@pytest.mark.anyio
async def test_append_user_message() -> None:
    repository = FakeMessageRepository()

    message = await service(message_repository=repository).append_message(
        FakeSession(),
        chat_session=chat_session(),
        role=ChatMessageRole.USER,
        content="  Xin chào  ",
    )

    assert message.role == ChatMessageRole.USER
    assert repository.calls[0]["content"] == "Xin chào"


@pytest.mark.anyio
async def test_append_assistant_message() -> None:
    message = await service().append_message(
        FakeSession(),
        chat_session=chat_session(),
        role=ChatMessageRole.ASSISTANT,
        content="Câu trả lời",
    )

    assert message.role == ChatMessageRole.ASSISTANT


@pytest.mark.anyio
async def test_append_system_message() -> None:
    message = await service().append_message(
        FakeSession(),
        chat_session=chat_session(),
        role=ChatMessageRole.SYSTEM,
        content="Internal instruction",
    )

    assert message.role == ChatMessageRole.SYSTEM


@pytest.mark.anyio
async def test_append_message_updates_session_updated_at() -> None:
    chat = chat_session()
    session_repository = FakeSessionRepository()

    await service(session_repository=session_repository).append_message(
        FakeSession(),
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Question",
    )

    assert session_repository.touches
    assert chat.updated_at == session_repository.touches[0]


@pytest.mark.anyio
async def test_append_message_rejects_blank_content() -> None:
    with pytest.raises(ChatMessageContentInvalidError):
        await service().append_message(
            FakeSession(),
            chat_session=chat_session(),
            role=ChatMessageRole.USER,
            content="   ",
        )


@pytest.mark.anyio
async def test_append_message_rejects_content_over_limit() -> None:
    with pytest.raises(ChatMessageContentTooLongError):
        await service(settings=Settings(chat_message_max_characters=5)).append_message(
            FakeSession(),
            chat_session=chat_session(),
            role=ChatMessageRole.USER,
            content="123456",
        )


@pytest.mark.anyio
async def test_append_message_rejects_negative_response_time() -> None:
    with pytest.raises(ChatMessageMetricsInvalidError):
        await service().append_message(
            FakeSession(),
            chat_session=chat_session(),
            role=ChatMessageRole.ASSISTANT,
            content="Answer",
            response_time_ms=-1,
        )


@pytest.mark.anyio
async def test_append_message_rejects_negative_prompt_tokens() -> None:
    with pytest.raises(ChatMessageMetricsInvalidError):
        await service().append_message(
            FakeSession(),
            chat_session=chat_session(),
            role=ChatMessageRole.ASSISTANT,
            content="Answer",
            prompt_tokens=-1,
        )


@pytest.mark.anyio
async def test_append_message_rejects_negative_completion_tokens() -> None:
    with pytest.raises(ChatMessageMetricsInvalidError):
        await service().append_message(
            FakeSession(),
            chat_session=chat_session(),
            role=ChatMessageRole.ASSISTANT,
            content="Answer",
            completion_tokens=-1,
        )


@pytest.mark.anyio
async def test_append_message_does_not_commit_repository() -> None:
    session = FakeSession()

    await service().append_message(
        session,
        chat_session=chat_session(),
        role=ChatMessageRole.USER,
        content="Question",
    )

    assert session.flushed is True
    assert session.committed is False
