from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Coroutine
from math import isfinite, sqrt
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Document, DocumentAccessScope, User, UserRole
from app.repositories.document_chunk_repository import (
    DocumentChunkCreate,
    DocumentChunkRepository,
    _validate_replacement_payload,
)

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalized(values: list[float]) -> tuple[float, ...]:
    norm = sqrt(sum(value * value for value in values))
    return tuple(value / norm for value in values)


def unit_vector(position: int = 0) -> tuple[float, ...]:
    values = [0.0] * 384
    values[position] = 1.0
    return tuple(values)


async def create_user(session: AsyncSession) -> User:
    user = User(
        email=f"repo-user-{uuid.uuid4()}@example.com",
        full_name="Repository User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_document(session: AsyncSession, *, is_deleted: bool = False) -> Document:
    uploader = await create_user(session)
    document = Document(
        title="Repository Document",
        original_filename="source.pdf",
        storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum_sha256=checksum(str(uuid.uuid4())),
        uploaded_by=uploader.id,
        access_scope=DocumentAccessScope.PRIVATE,
        is_deleted=is_deleted,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


def make_chunk(
    index: int, *, text: str | None = None, embedding: tuple[float, ...] | None = None
) -> DocumentChunkCreate:
    chunk_text = text or f"Chunk {index} text"
    return DocumentChunkCreate(
        chunk_index=index,
        text=chunk_text,
        token_count=3,
        character_count=len(chunk_text),
        page_numbers=(index + 1,),
        start_page=index + 1,
        end_page=index + 1,
        overlap_token_count=0 if index == 0 else 1,
        content_sha256=checksum(chunk_text),
        embedding=embedding or unit_vector(index),
        embedding_provider="sentence_transformers",
        embedding_model="fake-model",
        embedding_dimensions=384,
    )


def make_chunks(count: int) -> tuple[DocumentChunkCreate, ...]:
    return tuple(make_chunk(index) for index in range(count))


def test_replace_document_chunks_inserts_all_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)

            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(3))
            await session.commit()

            assert await repository.count_by_document(document.id) == 3

    run_async(scenario())


def test_replace_document_chunks_preserves_chunk_order(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(3))
            await session.commit()

            rows = await repository.list_by_document(document.id)

            assert [row.chunk_index for row in rows] == [0, 1, 2]

    run_async(scenario())


def test_replace_document_chunks_stores_page_metadata(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(2))
            await session.commit()

            rows = await repository.list_by_document(document.id)

            assert rows[0].page_numbers == [1]
            assert rows[1].start_page == 2
            assert rows[1].end_page == 2

    run_async(scenario())


def test_replace_document_chunks_stores_model_metadata(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(1))
            await session.commit()

            row = (await repository.list_by_document(document.id))[0]

            assert row.embedding_provider == "sentence_transformers"
            assert row.embedding_model == "fake-model"
            assert row.embedding_dimensions == 384

    run_async(scenario())


def test_replace_document_chunks_replaces_existing_rows(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(2))
            await session.commit()

            await repository.replace_for_document(
                document_id=document.id,
                chunks=(make_chunk(0, text="Replacement chunk"),),
            )
            await session.commit()
            rows = await repository.list_by_document(document.id)

            assert len(rows) == 1
            assert rows[0].text == "Replacement chunk"

    run_async(scenario())


def test_failed_replacement_preserves_existing_rows(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(1))
            await session.commit()
            document_id = document.id

            async def fail_flush() -> None:
                raise RuntimeError("simulated flush failure")

            monkeypatch.setattr(session, "flush", fail_flush)
            with pytest.raises(RuntimeError, match="simulated flush failure"):
                await repository.replace_for_document(
                    document_id=document.id,
                    chunks=(make_chunk(0, text="new text"),),
                )
            await session.rollback()
            monkeypatch.undo()

            rows = await repository.list_by_document(document_id)
            assert [row.text for row in rows] == ["Chunk 0 text"]

    run_async(scenario())


def test_replacement_rejects_deleted_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session, is_deleted=True)
            repository = DocumentChunkRepository(session)

            with pytest.raises(ValueError, match="missing or deleted"):
                await repository.replace_for_document(
                    document_id=document.id, chunks=make_chunks(1)
                )

    run_async(scenario())


def test_replacement_rejects_batch_count_mismatch() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        _validate_replacement_payload((make_chunk(0), make_chunk(2)))


def test_replacement_rejects_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="vector schema"):
        make_chunk(0, embedding=(1.0, 0.0))


def test_list_by_document_orders_by_chunk_index(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(4))
            await session.commit()

            rows = await repository.list_by_document(document.id)

            assert [row.chunk_index for row in rows] == [0, 1, 2, 3]

    run_async(scenario())


def test_count_by_document_returns_correct_count(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(4))
            await session.commit()

            assert await repository.count_by_document(document.id) == 4

    run_async(scenario())


def test_cosine_distance_orders_nearest_vector_first(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            chunks = (
                make_chunk(0, text="leave policy", embedding=unit_vector(0)),
                make_chunk(
                    1, text="near leave policy", embedding=normalized([0.98, 0.2] + [0.0] * 382)
                ),
                make_chunk(2, text="database backup", embedding=unit_vector(1)),
            )
            await repository.replace_for_document(document_id=document.id, chunks=chunks)
            await session.commit()

            results = await repository.find_nearest_for_verification(
                query_vector=unit_vector(0),
                limit=3,
            )

            assert [chunk.chunk_index for chunk, _distance in results][:2] == [0, 1]

    run_async(scenario())


def test_cosine_distance_returns_finite_value(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(1))
            await session.commit()

            results = await repository.find_nearest_for_verification(
                query_vector=unit_vector(0),
                limit=1,
            )

            assert isfinite(results[0][1])

    run_async(scenario())


def test_hnsw_query_returns_expected_candidates(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(3))
            await session.commit()

            results = await repository.find_nearest_for_verification(
                query_vector=unit_vector(1),
                limit=2,
            )

            assert len(results) == 2
            assert results[0][0].chunk_index == 1

    run_async(scenario())


def test_vector_query_rejects_wrong_dimensions(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            repository = DocumentChunkRepository(session)

            with pytest.raises(ValueError, match="vector schema"):
                await repository.find_nearest_for_verification(query_vector=[1.0, 0.0], limit=1)

    run_async(scenario())


def test_normal_query_orders_distances_ascending(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            repository = DocumentChunkRepository(session)
            await repository.replace_for_document(document_id=document.id, chunks=make_chunks(3))
            await session.commit()

            results = await repository.find_nearest_for_verification(
                query_vector=unit_vector(0),
                limit=3,
            )
            distances = [distance for _chunk, distance in results]

            assert distances == sorted(distances)

    run_async(scenario())
