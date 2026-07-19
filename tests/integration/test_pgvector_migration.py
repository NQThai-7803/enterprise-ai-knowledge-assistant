from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Document, DocumentAccessScope, DocumentChunk, User, UserRole

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def vector(position: int = 0) -> list[float]:
    values = [0.0] * 384
    values[position] = 1.0
    return values


async def create_user(session: AsyncSession) -> User:
    user = User(
        email=f"chunk-user-{uuid.uuid4()}@example.com",
        full_name="Chunk User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_document(session: AsyncSession) -> Document:
    uploader = await create_user(session)
    document = Document(
        title="Chunk Source",
        original_filename="source.pdf",
        storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum_sha256=checksum(str(uuid.uuid4())),
        uploaded_by=uploader.id,
        access_scope=DocumentAccessScope.PRIVATE,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


def make_chunk(
    document_id: uuid.UUID, *, index: int = 0, embedding: list[float] | None = None
) -> DocumentChunk:
    text_value = f"Chunk {index} text"
    return DocumentChunk(
        document_id=document_id,
        chunk_index=index,
        text=text_value,
        token_count=3,
        character_count=len(text_value),
        page_numbers=[1],
        start_page=1,
        end_page=1,
        overlap_token_count=0,
        content_sha256=checksum(text_value),
        embedding=embedding or vector(index),
        embedding_provider="sentence_transformers",
        embedding_model="fake-model",
        embedding_dimensions=384,
    )


async def expect_integrity_error(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


def test_vector_extension_is_available(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            result = await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )

            assert result.scalar_one() == "vector"

    run_async(scenario())


def test_document_chunks_table_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            result = await session.execute(text("SELECT to_regclass('public.document_chunks')"))

            assert result.scalar_one() == "document_chunks"

    run_async(scenario())


def test_embedding_column_is_vector_384(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            result = await session.execute(
                text(
                    "SELECT format_type(atttypid, atttypmod) "
                    "FROM pg_attribute "
                    "WHERE attrelid = 'document_chunks'::regclass "
                    "AND attname = 'embedding'"
                )
            )

            assert result.scalar_one() == "vector(384)"

    run_async(scenario())


def test_hnsw_cosine_index_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            result = await session.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename = 'document_chunks' "
                    "AND indexname = 'ix_document_chunks_embedding_hnsw_cosine'"
                )
            )
            indexdef = result.scalar_one()

            assert "USING hnsw" in indexdef
            assert "vector_cosine_ops" in indexdef

    run_async(scenario())


def test_insert_valid_document_chunk(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            chunk = make_chunk(document.id)
            session.add(chunk)
            await session.commit()
            await session.refresh(chunk)

            assert chunk.chunk_index == 0

    run_async(scenario())


def test_reject_wrong_vector_dimension(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            session.add(make_chunk(document.id, embedding=[1.0, 0.0]))

            with pytest.raises(SQLAlchemyError):
                await session.commit()
            await session.rollback()

    run_async(scenario())


def test_reject_duplicate_chunk_index_for_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            session.add(make_chunk(document.id, index=0))
            await session.commit()
            session.add(make_chunk(document.id, index=0))
            await expect_integrity_error(session)

    run_async(scenario())


def test_reject_invalid_token_count(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            chunk = make_chunk(document.id)
            chunk.token_count = 0
            session.add(chunk)
            await expect_integrity_error(session)

    run_async(scenario())


def test_reject_invalid_page_range(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            chunk = make_chunk(document.id)
            chunk.start_page = 2
            chunk.end_page = 1
            session.add(chunk)
            await expect_integrity_error(session)

    run_async(scenario())


def test_delete_document_cascades_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            session.add(make_chunk(document.id))
            await session.commit()
            document_id = document.id

            await session.delete(document)
            await session.commit()

            saved_chunk = await session.scalar(
                text("SELECT id FROM document_chunks WHERE document_id = :document_id"),
                {"document_id": document_id},
            )
            assert saved_chunk is None

    run_async(scenario())
