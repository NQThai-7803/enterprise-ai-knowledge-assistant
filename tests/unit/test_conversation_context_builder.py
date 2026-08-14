from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.chat.conversation_context_builder import (
    ConversationContextBuilder,
    render_conversation_history,
)
from app.core.config import Settings
from app.models import ChatMessageRole


class FakeCounter:
    def count(self, text: str) -> int:
        if "OVER_BUDGET" in text:
            return 10_000
        return text.count("TOKEN")

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens) -> str:  # noqa: ANN001
        return " ".join("x" for _ in tokens)


def settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "chat_history_max_messages": 20,
        "chat_history_max_tokens": 20,
        "retrieval_max_query_characters": 4000,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def row(index: int, role: ChatMessageRole, content: str):  # noqa: ANN201
    return SimpleNamespace(
        id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
        role=role,
        content=content,
        created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index),
    )


def builder(**overrides: object) -> ConversationContextBuilder:
    return ConversationContextBuilder(settings=settings(**overrides), token_counter=FakeCounter())


def test_builder_formats_user_assistant_and_internal_system_history() -> None:
    context = builder().build_from_messages(
        (
            row(1, ChatMessageRole.USER, "Question TOKEN"),
            row(2, ChatMessageRole.ASSISTANT, "Answer TOKEN"),
            row(3, ChatMessageRole.SYSTEM, "Internal note TOKEN"),
        ),
        current_question="Follow up?",
    )

    assert [message.role for message in context.messages] == [
        ChatMessageRole.USER,
        ChatMessageRole.ASSISTANT,
        ChatMessageRole.SYSTEM,
    ]
    assert "<conversation_history>" in context.formatted_history
    assert "INTERNAL_SYSTEM" in context.formatted_history
    assert "Follow up?" in context.retrieval_query


def test_builder_deduplicates_messages_and_preserves_chronological_order() -> None:
    first = row(1, ChatMessageRole.USER, "First TOKEN")
    duplicate = SimpleNamespace(
        id=first.id,
        role=ChatMessageRole.USER,
        content="Duplicate TOKEN",
        created_at=first.created_at,
    )

    context = builder().build_from_messages(
        (first, duplicate, row(2, ChatMessageRole.ASSISTANT, "Second TOKEN")),
        current_question="Current",
    )

    assert [message.content for message in context.messages] == ["First TOKEN", "Second TOKEN"]
    assert context.loaded_message_count == 2


def test_builder_orders_messages_by_created_at_then_id() -> None:
    context = builder().build_from_messages(
        (
            row(3, ChatMessageRole.USER, "Third TOKEN"),
            row(1, ChatMessageRole.USER, "First TOKEN"),
            row(2, ChatMessageRole.ASSISTANT, "Second TOKEN"),
        ),
        current_question="Current",
    )

    assert [message.content for message in context.messages] == [
        "First TOKEN",
        "Second TOKEN",
        "Third TOKEN",
    ]


def test_builder_applies_recent_message_limit() -> None:
    context = builder(chat_history_max_messages=2).build_from_messages(
        (
            row(1, ChatMessageRole.USER, "Old TOKEN"),
            row(2, ChatMessageRole.ASSISTANT, "Middle TOKEN"),
            row(3, ChatMessageRole.USER, "New TOKEN"),
        ),
        current_question="Current",
    )

    assert [message.content for message in context.messages] == ["Middle TOKEN", "New TOKEN"]
    assert context.selected_message_count == 2


def test_builder_applies_history_token_budget_recent_first() -> None:
    context = builder(chat_history_max_tokens=2).build_from_messages(
        (
            row(1, ChatMessageRole.USER, "Old TOKEN"),
            row(2, ChatMessageRole.ASSISTANT, "Middle TOKEN"),
            row(3, ChatMessageRole.USER, "New TOKEN"),
        ),
        current_question="Current",
    )

    assert [message.content for message in context.messages] == ["Middle TOKEN", "New TOKEN"]
    assert context.estimated_token_count == 2


def test_builder_does_not_skip_oversized_recent_message_for_older_history() -> None:
    context = builder(chat_history_max_tokens=1).build_from_messages(
        (
            row(1, ChatMessageRole.USER, "Old TOKEN"),
            row(2, ChatMessageRole.ASSISTANT, "Latest OVER_BUDGET"),
        ),
        current_question="Current",
    )

    assert context.messages == ()
    assert context.retrieval_query == "Current"


def test_builder_returns_empty_history_when_limits_are_zero() -> None:
    context = builder(chat_history_max_messages=0).build_from_messages(
        (row(1, ChatMessageRole.USER, "Old TOKEN"),),
        current_question="Current",
    )

    assert context.messages == ()
    assert context.estimated_token_count == 0
    assert context.retrieval_query == "Current"


def test_builder_falls_back_to_current_question_when_resolved_query_is_too_long() -> None:
    context = builder(retrieval_max_query_characters=20).build_from_messages(
        (row(1, ChatMessageRole.USER, "Very long previous topic TOKEN " + "x" * 80),),
        current_question="What about it?",
    )

    assert context.resolved_question.context_dependent is True
    assert context.retrieval_query == "What about it?"


def test_render_empty_history_uses_delimiters() -> None:
    assert render_conversation_history(()) == "<conversation_history>\n</conversation_history>"


def test_context_repr_does_not_expose_message_content() -> None:
    context = builder().build_from_messages(
        (row(1, ChatMessageRole.USER, "SECRET_HISTORY_TOKEN TOKEN"),),
        current_question="Current",
    )

    assert "SECRET_HISTORY_TOKEN" not in repr(context)
    assert "SECRET_HISTORY_TOKEN" not in repr(context.messages[0])


@pytest.mark.anyio
async def test_builder_loads_memory_through_repository_with_session_and_owner() -> None:
    session = object()
    session_id = UUID("00000000-0000-0000-0000-000000000111")
    owner_user_id = UUID("00000000-0000-0000-0000-000000000222")

    class FakeRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def list_owned_messages_for_memory(self, session_arg, **kwargs):  # noqa: ANN001
            self.calls.append({"session": session_arg, **kwargs})
            return (row(1, ChatMessageRole.USER, "Question TOKEN"),)

    repository = FakeRepository()
    context = ConversationContextBuilder(
        settings=settings(),
        token_counter=FakeCounter(),
        message_repository=repository,
    )

    result = await context.build(
        session,  # type: ignore[arg-type]
        session_id=session_id,
        owner_user_id=owner_user_id,
        current_question="Current",
    )

    assert result.selected_message_count == 1
    assert repository.calls == [
        {
            "session": session,
            "session_id": session_id,
            "owner_user_id": owner_user_id,
        }
    ]
