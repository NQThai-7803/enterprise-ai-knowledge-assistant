from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ChatMessage, ChatMessageRole, ChatSession, MessageCitation, UserRole
from tests.integration.retrieval_helpers import create_chunk, create_document, create_user

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def create_assistant_message(session: AsyncSession):
    owner = await create_user(session, "citation-migration-owner", role=UserRole.STAFF)
    document = await create_document(session, "citation-migration-doc", uploader=owner)
    chunk = await create_chunk(session, "citation-migration-chunk", document=document)
    chat = ChatSession(
        user_id=owner.id,
        title="Citation migration",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(chat)
    await session.flush()
    message = ChatMessage(
        session_id=chat.id,
        role=ChatMessageRole.ASSISTANT,
        content="Answer [1].",
        created_at=datetime.now(UTC),
    )
    session.add(message)
    await session.flush()
    return document, chunk, message


async def add_citation(session: AsyncSession, message: ChatMessage, document, chunk):
    citation = MessageCitation(
        message_id=message.id,
        document_id=document.id,
        chunk_id=chunk.id,
        page_number=1,
        excerpt="Server excerpt",
        relevance_score=0.9,
        citation_order=1,
    )
    session.add(citation)
    await session.flush()
    return citation


def test_message_citations_table_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            exists = await session.scalar(
                text("select to_regclass('public.message_citations') is not null")
            )
            assert exists is True

    run_async(scenario())


def test_message_citation_indexes_exist(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            indexes = set(
                await session.scalars(
                    text(
                        "select indexname from pg_indexes "
                        "where schemaname = 'public' and tablename = 'message_citations'"
                    )
                )
            )
            assert "ix_message_citations_message_order" in indexes
            assert "ix_message_citations_document" in indexes

    run_async(scenario())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("citation_order", 0),
        ("page_number", 0),
        ("excerpt", "   "),
        ("relevance_score", 1.1),
    ],
)
def test_message_citation_constraints(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    field: str,
    value: object,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document, chunk, message = await create_assistant_message(session)
            kwargs = {
                "message_id": message.id,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "page_number": 1,
                "excerpt": "Server excerpt",
                "relevance_score": 0.9,
                "citation_order": 1,
            }
            kwargs[field] = value
            session.add(MessageCitation(**kwargs))
            with pytest.raises(IntegrityError):
                await session.commit()

    run_async(scenario())


def test_message_citation_unique_order(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document, chunk, message = await create_assistant_message(session)
            await add_citation(session, message, document, chunk)
            session.add(
                MessageCitation(
                    message_id=message.id,
                    document_id=document.id,
                    chunk_id=chunk.id,
                    page_number=1,
                    excerpt="Another excerpt",
                    relevance_score=None,
                    citation_order=1,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    run_async(scenario())


def test_message_citation_message_fk_cascades(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document, chunk, message = await create_assistant_message(session)
            await add_citation(session, message, document, chunk)
            await session.commit()
            await session.execute(delete(ChatMessage).where(ChatMessage.id == message.id))
            await session.commit()
            count = await session.scalar(select(func.count()).select_from(MessageCitation))
            assert count == 0

    run_async(scenario())


def test_message_citation_chunk_fk_sets_null(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document, chunk, message = await create_assistant_message(session)
            citation = await add_citation(session, message, document, chunk)
            citation_id = citation.id
            await session.commit()
            await session.execute(delete(type(chunk)).where(type(chunk).id == chunk.id))
            await session.commit()
            refreshed = await session.get(MessageCitation, citation_id)
            assert refreshed is not None
            await session.refresh(refreshed)
            assert refreshed.chunk_id is None

    run_async(scenario())
