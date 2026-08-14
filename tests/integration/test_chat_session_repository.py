from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ChatMessage, ChatMessageRole, ChatSession, User, UserRole
from app.repositories import chat_message_repository, chat_session_repository
from app.services.chat_message_service import ChatMessageService

pytestmark = pytest.mark.integration


def run_async(coro):
    return asyncio.run(coro)


async def create_user(session: AsyncSession, *, role: UserRole = UserRole.STAFF) -> User:
    user = User(
        email=f"chat-{uuid.uuid4()}@example.com",
        full_name="Chat User",
        hashed_password="not-used",
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_chat_session(
    session: AsyncSession,
    *,
    user: User,
    title: str | None = "Session",
    is_archived: bool = False,
    updated_at: datetime | None = None,
    session_id: uuid.UUID | None = None,
) -> ChatSession:
    now = updated_at or datetime.now(UTC)
    chat = ChatSession(
        id=session_id,
        user_id=user.id,
        title=title,
        is_archived=is_archived,
        created_at=now,
        updated_at=now,
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def create_message(
    session: AsyncSession,
    *,
    chat_session: ChatSession,
    role: ChatMessageRole,
    content: str,
    created_at: datetime | None = None,
    retrieval_query: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=chat_session.id,
        role=role,
        content=content,
        retrieval_query=retrieval_query,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        created_at=created_at or datetime.now(UTC),
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


def test_create_repository_sets_owner_and_default_archived(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            user = await create_user(session)
            chat = await chat_session_repository.create(session, user_id=user.id, title=None)
            await session.commit()
            await session.refresh(chat)

            assert chat.user_id == user.id
            assert chat.is_archived is False

    run_async(scenario())


def test_list_owned_filters_in_sql(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session)
            other = await create_user(session)
            owned = await create_chat_session(session, user=owner, title="Owned")
            await create_chat_session(session, user=other, title="Other")

            rows = await chat_session_repository.list_owned(
                session,
                owner_user_id=owner.id,
                limit=20,
                offset=0,
            )

            assert [row.chat_session.id for row in rows] == [owned.id]

    run_async(scenario())


def test_get_owned_by_id_returns_none_for_non_owner(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session)
            other = await create_user(session)
            owned = await create_chat_session(session, user=owner)

            result = await chat_session_repository.get_owned_by_id(
                session,
                session_id=owned.id,
                owner_user_id=other.id,
            )

            assert result is None

    run_async(scenario())


def test_visible_messages_hide_system_and_internal_fields(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session)
            chat = await create_chat_session(session, user=owner)
            await create_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.SYSTEM,
                content="CONFIDENTIAL_CHAT_OWNERSHIP_MARKER",
                retrieval_query="hidden retrieval query",
                prompt_tokens=10,
                completion_tokens=5,
            )
            visible = await create_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.USER,
                content="Visible question",
                retrieval_query="internal query",
                prompt_tokens=11,
                completion_tokens=6,
            )

            rows = await chat_message_repository.list_visible_by_session(
                session,
                session_id=chat.id,
                limit=20,
                offset=0,
            )

            assert len(rows) == 1
            assert rows[0].id == visible.id
            assert rows[0].content == "Visible question"
            assert not hasattr(rows[0], "retrieval_query")
            assert not hasattr(rows[0], "prompt_tokens")
            assert not hasattr(rows[0], "completion_tokens")

    run_async(scenario())


def test_memory_messages_include_internal_system_and_filter_owned_session(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session)
            other = await create_user(session)
            chat = await create_chat_session(session, user=owner)
            other_owned_chat = await create_chat_session(session, user=owner)
            other_user_chat = await create_chat_session(session, user=other)
            base = datetime(2026, 1, 1, tzinfo=UTC)
            system_message = await create_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.SYSTEM,
                content="Internal system memory",
                created_at=base,
            )
            user_message = await create_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.USER,
                content="User memory",
                created_at=base + timedelta(seconds=1),
            )
            assistant_message = await create_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.ASSISTANT,
                content="Assistant memory",
                created_at=base + timedelta(seconds=2),
            )
            await create_message(
                session,
                chat_session=other_owned_chat,
                role=ChatMessageRole.USER,
                content="Other owned session memory",
                created_at=base + timedelta(seconds=3),
            )
            await create_message(
                session,
                chat_session=other_user_chat,
                role=ChatMessageRole.USER,
                content="Other user memory",
                created_at=base + timedelta(seconds=4),
            )

            rows = await chat_message_repository.list_owned_messages_for_memory(
                session,
                session_id=chat.id,
                owner_user_id=owner.id,
            )

            assert [row.id for row in rows] == [
                system_message.id,
                user_message.id,
                assistant_message.id,
            ]
            assert [row.role for row in rows] == [
                ChatMessageRole.SYSTEM,
                ChatMessageRole.USER,
                ChatMessageRole.ASSISTANT,
            ]
            assert [row.content for row in rows] == [
                "Internal system memory",
                "User memory",
                "Assistant memory",
            ]

    run_async(scenario())


def test_append_message_updates_session_updated_at_same_transaction(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session)
            old_time = datetime(2026, 1, 1, tzinfo=UTC)
            chat = await create_chat_session(session, user=owner, updated_at=old_time)

            await ChatMessageService().append_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.USER,
                content="Question",
            )
            assert chat.updated_at > old_time
            await session.commit()
            await session.refresh(chat)

            assert chat.updated_at > old_time

    run_async(scenario())


def test_message_history_pagination(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session)
            chat = await create_chat_session(session, user=owner)
            base = datetime(2026, 1, 1, tzinfo=UTC)
            for index in range(3):
                await create_message(
                    session,
                    chat_session=chat,
                    role=ChatMessageRole.USER,
                    content=f"Message {index}",
                    created_at=base + timedelta(seconds=index),
                )

            rows = await chat_message_repository.list_visible_by_session(
                session,
                session_id=chat.id,
                limit=1,
                offset=1,
            )

            assert [row.content for row in rows] == ["Message 1"]

    run_async(scenario())


def test_message_history_total_excludes_system_messages(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session)
            chat = await create_chat_session(session, user=owner)
            await create_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.SYSTEM,
                content="System",
            )
            await create_message(
                session,
                chat_session=chat,
                role=ChatMessageRole.ASSISTANT,
                content="Answer",
            )

            total = await chat_message_repository.count_visible_by_session(
                session, session_id=chat.id
            )

            assert total == 1

    run_async(scenario())
