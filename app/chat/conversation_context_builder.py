from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.follow_up_resolver import (
    ResolvedConversationQuestion,
    resolve_conversation_question,
)
from app.core.config import Settings, get_settings
from app.document_processing.tokenization.base import TokenCounter
from app.models import ChatMessageRole
from app.repositories import chat_message_repository

CONVERSATION_HISTORY_START = "<conversation_history>"
CONVERSATION_HISTORY_END = "</conversation_history>"

MEMORY_ROLES = (
    ChatMessageRole.USER,
    ChatMessageRole.ASSISTANT,
    ChatMessageRole.SYSTEM,
)


@dataclass(frozen=True, slots=True)
class ConversationPromptMessage:
    id: UUID
    role: ChatMessageRole
    content: str = field(repr=False)
    created_at: datetime

    def __post_init__(self) -> None:
        if self.role not in MEMORY_ROLES:
            msg = "Conversation memory role is not supported."
            raise ValueError(msg)
        if not isinstance(self.content, str) or not self.content.strip():
            msg = "Conversation memory content must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ConversationContext:
    messages: tuple[ConversationPromptMessage, ...]
    formatted_history: str = field(repr=False)
    retrieval_query: str = field(repr=False)
    resolved_question: ResolvedConversationQuestion = field(repr=False)
    loaded_message_count: int
    selected_message_count: int
    estimated_token_count: int

    def __post_init__(self) -> None:
        messages = tuple(self.messages)
        object.__setattr__(self, "messages", messages)
        if self.selected_message_count != len(messages):
            msg = "selected_message_count must match messages length."
            raise ValueError(msg)
        if self.loaded_message_count < self.selected_message_count:
            msg = "loaded_message_count must be >= selected_message_count."
            raise ValueError(msg)
        if self.estimated_token_count < 0:
            msg = "estimated_token_count must not be negative."
            raise ValueError(msg)


class ConversationContextBuilder:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        token_counter: TokenCounter,
        message_repository=chat_message_repository,
    ) -> None:
        self.settings = settings or get_settings()
        self.token_counter = token_counter
        self.message_repository = message_repository

    async def build(
        self,
        session: AsyncSession,
        *,
        session_id: UUID,
        owner_user_id: UUID,
        current_question: str,
    ) -> ConversationContext:
        rows = await self.message_repository.list_owned_messages_for_memory(
            session,
            session_id=session_id,
            owner_user_id=owner_user_id,
        )
        return self.build_from_messages(rows, current_question=current_question)

    def build_from_messages(
        self,
        messages: Sequence[object],
        *,
        current_question: str,
    ) -> ConversationContext:
        loaded_messages = prompt_messages_from_rows(messages)
        selected_messages = self._trim_messages(loaded_messages)
        formatted_history = render_conversation_history(selected_messages)
        estimated_token_count = (
            self.token_counter.count(formatted_history) if selected_messages else 0
        )
        resolved_question = resolve_conversation_question(
            current_question,
            messages=selected_messages,
        )
        retrieval_query = self._fit_retrieval_query(
            resolved_question=resolved_question,
            question=current_question,
        )
        return ConversationContext(
            messages=selected_messages,
            formatted_history=formatted_history,
            retrieval_query=retrieval_query,
            resolved_question=resolved_question,
            loaded_message_count=len(loaded_messages),
            selected_message_count=len(selected_messages),
            estimated_token_count=estimated_token_count,
        )

    def _trim_messages(
        self,
        messages: tuple[ConversationPromptMessage, ...],
    ) -> tuple[ConversationPromptMessage, ...]:
        max_messages = self.settings.chat_history_max_messages
        max_tokens = self.settings.chat_history_max_tokens
        if max_messages <= 0 or max_tokens <= 0:
            return ()

        selected_recent_first: list[ConversationPromptMessage] = []
        for message in reversed(messages):
            if len(selected_recent_first) >= max_messages:
                break
            candidate_recent_first = [*selected_recent_first, message]
            candidate_chronological = tuple(reversed(candidate_recent_first))
            candidate_tokens = self.token_counter.count(
                render_conversation_history(candidate_chronological)
            )
            if candidate_tokens <= max_tokens:
                selected_recent_first = candidate_recent_first
            else:
                break
        return tuple(reversed(selected_recent_first))

    def _fit_retrieval_query(
        self,
        *,
        resolved_question: ResolvedConversationQuestion,
        question: str,
    ) -> str:
        normalized_question = question.strip()
        standalone_question = resolved_question.standalone_question.strip()
        if len(standalone_question) <= self.settings.retrieval_max_query_characters:
            return standalone_question
        if len(normalized_question) <= self.settings.retrieval_max_query_characters:
            return normalized_question
        return normalized_question


def prompt_messages_from_rows(rows: Sequence[object]) -> tuple[ConversationPromptMessage, ...]:
    unique_by_id: dict[UUID, ConversationPromptMessage] = {}
    for row in rows:
        message = ConversationPromptMessage(
            id=row.id,
            role=ChatMessageRole(row.role),
            content=row.content,
            created_at=row.created_at,
        )
        unique_by_id.setdefault(message.id, message)
    return tuple(
        sorted(unique_by_id.values(), key=lambda message: (message.created_at, message.id))
    )


def render_conversation_history(messages: Sequence[ConversationPromptMessage]) -> str:
    if not messages:
        return f"{CONVERSATION_HISTORY_START}\n{CONVERSATION_HISTORY_END}"
    rendered_messages = "\n\n".join(
        render_conversation_message(index, message)
        for index, message in enumerate(messages, start=1)
    )
    return f"{CONVERSATION_HISTORY_START}\n{rendered_messages}\n{CONVERSATION_HISTORY_END}"


def render_conversation_message(ordinal: int, message: ConversationPromptMessage) -> str:
    role_label = _conversation_role_label(message.role)
    return (
        f"--- CONVERSATION MESSAGE {ordinal} {role_label} START ---\n"
        f"{message.content}\n"
        f"--- CONVERSATION MESSAGE {ordinal} {role_label} END ---"
    )


def render_conversation_retrieval_query(
    messages: Sequence[ConversationPromptMessage],
    *,
    question: str,
) -> str:
    previous_user_messages = [
        message for message in messages if message.role == ChatMessageRole.USER
    ]

    if not previous_user_messages:
        return question.strip()

    recent_user_messages = previous_user_messages[-2:]

    history_lines = "\n".join(
        f"Previous user question: {message.content}" for message in recent_user_messages
    )

    return f"{history_lines}\n\nCurrent follow-up question:\n{question.strip()}"


def _conversation_role_label(role: ChatMessageRole) -> str:
    if role == ChatMessageRole.SYSTEM:
        return "INTERNAL_SYSTEM"
    return role.value
