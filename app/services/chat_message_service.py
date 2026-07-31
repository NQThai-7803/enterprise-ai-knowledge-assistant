from __future__ import annotations

from datetime import UTC, datetime
from numbers import Integral

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ChatMessageContentInvalidError,
    ChatMessageContentTooLongError,
    ChatMessageMetricsInvalidError,
)
from app.models import ChatMessage, ChatMessageRole, ChatSession
from app.repositories import chat_message_repository, chat_session_repository


class ChatMessageService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        message_repository=chat_message_repository,
        session_repository=chat_session_repository,
    ) -> None:
        self.settings = settings or get_settings()
        self.message_repository = message_repository
        self.session_repository = session_repository

    async def append_message(
        self,
        session: AsyncSession,
        *,
        chat_session: ChatSession,
        role: ChatMessageRole,
        content: str,
        retrieval_query: str | None = None,
        response_time_ms: int | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        created_at: datetime | None = None,
    ) -> ChatMessage:
        if not isinstance(role, ChatMessageRole):
            raise ChatMessageContentInvalidError()
        normalized_content = normalize_message_content(
            content,
            max_characters=self.settings.chat_message_max_characters,
        )
        validated_response_time_ms = validate_non_negative_metric(response_time_ms)
        validated_prompt_tokens = validate_non_negative_metric(prompt_tokens)
        validated_completion_tokens = validate_non_negative_metric(completion_tokens)
        created_at = created_at or datetime.now(UTC)

        message = await self.message_repository.create(
            session,
            chat_session=chat_session,
            role=role,
            content=normalized_content,
            retrieval_query=retrieval_query,
            response_time_ms=validated_response_time_ms,
            prompt_tokens=validated_prompt_tokens,
            completion_tokens=validated_completion_tokens,
            created_at=created_at,
        )
        await self.session_repository.touch_updated_at(chat_session, updated_at=created_at)
        await session.flush()
        return message


async def append_message(
    session: AsyncSession,
    *,
    chat_session: ChatSession,
    role: ChatMessageRole,
    content: str,
    retrieval_query: str | None = None,
    response_time_ms: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    created_at: datetime | None = None,
) -> ChatMessage:
    return await ChatMessageService().append_message(
        session,
        chat_session=chat_session,
        role=role,
        content=content,
        retrieval_query=retrieval_query,
        response_time_ms=response_time_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        created_at=created_at,
    )


def normalize_message_content(content: str, *, max_characters: int) -> str:
    if not isinstance(content, str):
        raise ChatMessageContentInvalidError()
    normalized = content.strip()
    if not normalized:
        raise ChatMessageContentInvalidError()
    if len(normalized) > max_characters:
        raise ChatMessageContentTooLongError()
    return normalized


def validate_non_negative_metric(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ChatMessageMetricsInvalidError()
    metric = int(value)
    if metric < 0:
        raise ChatMessageMetricsInvalidError()
    return metric
