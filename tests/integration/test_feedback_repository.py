from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
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
from app.repositories import feedback_repository
from app.repositories.feedback_repository import FeedbackReportFilters
from app.services.feedback_service import FeedbackService
from tests.integration.retrieval_helpers import create_department, create_user

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def create_chat_message(
    session: AsyncSession,
    *,
    owner: User,
    role: ChatMessageRole = ChatMessageRole.ASSISTANT,
    content: str = "Assistant answer",
    created_at: datetime | None = None,
) -> ChatMessage:
    now = created_at or datetime.now(UTC)
    chat = ChatSession(user_id=owner.id, title="Feedback", created_at=now, updated_at=now)
    session.add(chat)
    await session.flush()
    message = ChatMessage(
        session_id=chat.id,
        role=role,
        content=content,
        created_at=now,
    )
    session.add(message)
    await session.flush()
    return message


async def add_feedback(
    session: AsyncSession,
    *,
    owner: User,
    rating: FeedbackRating = FeedbackRating.HELPFUL,
    updated_at: datetime | None = None,
) -> Feedback:
    message = await create_chat_message(session, owner=owner)
    now = updated_at or datetime.now(UTC)
    feedback = Feedback(
        message_id=message.id,
        user_id=owner.id,
        rating=rating,
        reason="Report reason",
        created_at=now,
        updated_at=now,
    )
    session.add(feedback)
    await session.flush()
    return feedback


def test_owned_assistant_message_query_filters_in_sql(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "feedback-owner", role=UserRole.STAFF)
            other = await create_user(session, "feedback-other", role=UserRole.STAFF)
            assistant = await create_chat_message(session, owner=owner)
            user_message = await create_chat_message(
                session,
                owner=owner,
                role=ChatMessageRole.USER,
                content="User question",
            )
            await session.commit()

            assert (
                await feedback_repository.get_owned_assistant_message_id(
                    session,
                    message_id=assistant.id,
                    owner_user_id=owner.id,
                )
            ) == assistant.id
            assert (
                await feedback_repository.get_owned_assistant_message_id(
                    session,
                    message_id=assistant.id,
                    owner_user_id=other.id,
                )
            ) is None
            assert (
                await feedback_repository.get_owned_assistant_message_id(
                    session,
                    message_id=user_message.id,
                    owner_user_id=owner.id,
                )
            ) is None

    run_async(scenario())


def test_upsert_updates_existing_feedback_without_duplicate(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "feedback-upsert-owner", role=UserRole.STAFF)
            message = await create_chat_message(session, owner=owner)
            await session.commit()
            first = await feedback_repository.upsert_owned_message_feedback(
                session,
                message_id=message.id,
                user_id=owner.id,
                rating=FeedbackRating.HELPFUL,
                reason="Helpful",
            )
            await session.commit()
            second = await feedback_repository.upsert_owned_message_feedback(
                session,
                message_id=message.id,
                user_id=owner.id,
                rating=FeedbackRating.NOT_HELPFUL,
                reason=None,
            )
            await session.commit()
            count = await session.scalar(select(func.count()).select_from(Feedback))
            assert second.id == first.id
            assert second.created_at == first.created_at
            assert second.rating == FeedbackRating.NOT_HELPFUL
            assert second.reason is None
            assert count == 1

    run_async(scenario())


def test_concurrent_feedback_upserts_create_one_row(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "feedback-concurrent-owner", role=UserRole.STAFF)
            message = await create_chat_message(session, owner=owner)
            await session.commit()

        barrier = asyncio.Event()

        async def upsert(rating: FeedbackRating, reason: str):
            async with async_session_factory_for_tests() as session:
                service = FeedbackService(session)
                await barrier.wait()
                return await service.upsert_feedback(
                    message_id=message.id,
                    current_user=owner,
                    rating=rating,
                    reason=reason,
                )

        first = asyncio.create_task(upsert(FeedbackRating.HELPFUL, "A"))
        second = asyncio.create_task(upsert(FeedbackRating.NOT_HELPFUL, "B"))
        barrier.set()
        results = await asyncio.gather(first, second)

        async with async_session_factory_for_tests() as session:
            rows = (await session.scalars(select(Feedback))).all()
            assert len(rows) == 1
            assert {result.id for result in results} == {rows[0].id}
            assert rows[0].rating in {FeedbackRating.HELPFUL, FeedbackRating.NOT_HELPFUL}
            assert rows[0].reason in {"A", "B"}

    run_async(scenario())


def test_manager_scope_is_applied_before_limit(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept_a = await create_department(session, "feedback-scope-a")
            dept_b = await create_department(session, "feedback-scope-b")
            manager = await create_user(
                session,
                "feedback-scope-manager",
                role=UserRole.MANAGER,
                department_id=dept_a.id,
            )
            user_a = await create_user(
                session,
                "feedback-scope-user-a",
                role=UserRole.STAFF,
                department_id=dept_a.id,
            )
            user_b = await create_user(
                session,
                "feedback-scope-user-b",
                role=UserRole.STAFF,
                department_id=dept_b.id,
            )
            now = datetime.now(UTC)
            await add_feedback(session, owner=user_b, updated_at=now)
            await add_feedback(session, owner=user_b, updated_at=now - timedelta(minutes=1))
            expected = await add_feedback(session, owner=user_a, updated_at=now - timedelta(days=1))
            await session.commit()

            filters = FeedbackReportFilters()
            total = await feedback_repository.count_report(
                session,
                current_user=manager,
                filters=filters,
            )
            rows = await feedback_repository.list_report(
                session,
                current_user=manager,
                filters=filters,
                limit=1,
                offset=0,
            )
            assert total == 1
            assert tuple(row.id for row in rows) == (expected.id,)
            assert rows[0].department_id == dept_a.id

    run_async(scenario())
