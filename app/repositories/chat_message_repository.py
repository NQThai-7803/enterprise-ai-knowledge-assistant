from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, ChatMessageRole, ChatSession

VISIBLE_MESSAGE_ROLES = (ChatMessageRole.USER, ChatMessageRole.ASSISTANT)
MEMORY_MESSAGE_ROLES = (
    ChatMessageRole.USER,
    ChatMessageRole.ASSISTANT,
    ChatMessageRole.SYSTEM,
)


@dataclass(frozen=True, slots=True)
class VisibleChatMessageRow:
    id: UUID
    role: ChatMessageRole
    content: str
    response_time_ms: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationMemoryMessageRow:
    id: UUID
    role: ChatMessageRole
    content: str
    created_at: datetime


async def create(
    session: AsyncSession,
    *,
    chat_session: ChatSession,
    role: ChatMessageRole,
    content: str,
    retrieval_query: str | None,
    response_time_ms: int | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    created_at: datetime | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=chat_session.id,
        role=role,
        content=content,
        retrieval_query=retrieval_query,
        response_time_ms=response_time_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        created_at=created_at,
    )
    session.add(message)
    return message


async def list_visible_by_session(
    session: AsyncSession,
    *,
    session_id: UUID,
    limit: int,
    offset: int,
) -> tuple[VisibleChatMessageRow, ...]:
    statement = (
        select(
            ChatMessage.id,
            ChatMessage.role,
            ChatMessage.content,
            ChatMessage.response_time_ms,
            ChatMessage.created_at,
        )
        .where(
            ChatMessage.session_id == session_id,
            ChatMessage.role.in_(VISIBLE_MESSAGE_ROLES),
        )
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(statement)).all()
    return tuple(
        VisibleChatMessageRow(
            id=message_id,
            role=role,
            content=content,
            response_time_ms=response_time_ms,
            created_at=created_at,
        )
        for message_id, role, content, response_time_ms, created_at in rows
    )


async def list_recent_visible_owned_messages(
    session: AsyncSession,
    *,
    session_id: UUID,
    owner_user_id: UUID,
    limit: int,
) -> tuple[VisibleChatMessageRow, ...]:
    if limit <= 0:
        return ()
    recent_subquery = (
        select(
            ChatMessage.id,
            ChatMessage.role,
            ChatMessage.content,
            ChatMessage.response_time_ms,
            ChatMessage.created_at,
        )
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == owner_user_id,
            ChatMessage.role.in_(VISIBLE_MESSAGE_ROLES),
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .subquery()
    )
    statement = select(recent_subquery).order_by(
        recent_subquery.c.created_at.asc(),
        recent_subquery.c.id.asc(),
    )
    rows = (await session.execute(statement)).all()
    return tuple(
        VisibleChatMessageRow(
            id=message_id,
            role=role,
            content=content,
            response_time_ms=response_time_ms,
            created_at=created_at,
        )
        for message_id, role, content, response_time_ms, created_at in rows
    )


async def list_owned_messages_for_memory(
    session: AsyncSession,
    *,
    session_id: UUID,
    owner_user_id: UUID,
) -> tuple[ConversationMemoryMessageRow, ...]:
    statement = (
        select(
            ChatMessage.id,
            ChatMessage.role,
            ChatMessage.content,
            ChatMessage.created_at,
        )
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == owner_user_id,
            ChatMessage.role.in_(MEMORY_MESSAGE_ROLES),
        )
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    rows = (await session.execute(statement)).all()
    return tuple(
        ConversationMemoryMessageRow(
            id=message_id,
            role=role,
            content=content,
            created_at=created_at,
        )
        for message_id, role, content, created_at in rows
    )


async def count_visible_by_session(
    session: AsyncSession,
    *,
    session_id: UUID,
) -> int:
    statement = (
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.session_id == session_id,
            ChatMessage.role.in_(VISIBLE_MESSAGE_ROLES),
        )
    )
    return await session.scalar(statement) or 0
