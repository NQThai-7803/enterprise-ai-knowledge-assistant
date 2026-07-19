from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Coroutine, Sequence
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.document_processing.chunking.models import ChunkingResult, TextChunk
from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.models import EmbeddingBatch, EmbeddingVector
from app.models import Document, DocumentAccessScope, DocumentStatus, User, UserRole
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.services import document_embedding_service
from app.services.document_embedding_service import embed_and_store_chunks

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def vector(position: int = 0, *, dimensions: int = 384) -> tuple[float, ...]:
    values = [0.0] * dimensions
    values[position] = 1.0
    return tuple(values)


class FakeEmbeddingProvider:
    def __init__(
        self,
        *,
        dimensions: int = 384,
        model_name: str = "fake-model",
        fail: bool = False,
        vector_count: int | None = None,
    ) -> None:
        self._dimensions = dimensions
        self._model_name = model_name
        self.fail = fail
        self.vector_count = vector_count
        self.seen_texts: tuple[str, ...] = ()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingBatch:
        self.seen_texts = tuple(texts)
        if self.fail:
            raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED)
        count = self.vector_count if self.vector_count is not None else len(texts)
        vectors = tuple(
            EmbeddingVector(
                values=vector(index % self._dimensions, dimensions=self._dimensions),
                dimensions=self._dimensions,
                normalized=True,
                model_name=self._model_name,
            )
            for index in range(count)
        )
        return EmbeddingBatch(
            vectors=vectors,
            count=len(vectors),
            dimensions=self._dimensions,
            normalized=True,
            model_name=self._model_name,
        )

    def embed_query(self, text: str) -> EmbeddingVector:
        return EmbeddingVector(
            values=vector(0, dimensions=self._dimensions),
            dimensions=self._dimensions,
            normalized=True,
            model_name=self._model_name,
        )


async def create_user(session: AsyncSession) -> User:
    user = User(
        email=f"service-user-{uuid.uuid4()}@example.com",
        full_name="Service User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_document(
    session: AsyncSession, *, status: DocumentStatus = DocumentStatus.UPLOADED
) -> Document:
    uploader = await create_user(session)
    document = Document(
        title="Service Document",
        original_filename="source.pdf",
        storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum_sha256=checksum(str(uuid.uuid4())),
        uploaded_by=uploader.id,
        access_scope=DocumentAccessScope.PRIVATE,
        status=status,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


def make_chunk(index: int, text: str | None = None) -> TextChunk:
    chunk_text = text or f"Chunk {index} text"
    return TextChunk(
        chunk_index=index,
        text=chunk_text,
        token_count=3,
        character_count=len(chunk_text),
        page_numbers=(index + 1,),
        start_page=index + 1,
        end_page=index + 1,
        overlap_token_count=0 if index == 0 else 1,
        content_sha256=checksum(chunk_text),
    )


def make_result(count: int = 2, *, text_prefix: str = "Chunk") -> ChunkingResult:
    chunks = tuple(make_chunk(index, f"{text_prefix} {index} text") for index in range(count))
    source_pages = tuple(sorted({page for chunk in chunks for page in chunk.page_numbers}))
    return ChunkingResult(
        chunks=chunks,
        chunk_count=len(chunks),
        total_tokens=sum(chunk.token_count for chunk in chunks),
        total_unique_source_pages=len(source_pages),
        source_page_numbers=source_pages,
    )


def test_embed_and_store_chunks_persists_all_rows(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            saved = await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(3),
                embedding_provider=FakeEmbeddingProvider(),
            )
            rows = await DocumentChunkRepository(session).list_by_document(document.id)

            assert saved == 3
            assert len(rows) == 3

    run_async(scenario())


def test_embed_and_store_chunks_stores_vectors(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(1),
                embedding_provider=FakeEmbeddingProvider(),
            )
            row = (await DocumentChunkRepository(session).list_by_document(document.id))[0]

            assert len(row.embedding) == 384

    run_async(scenario())


def test_embed_and_store_chunks_stores_original_chunk_text(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(1, text_prefix="passage should not be prefixed"),
                embedding_provider=FakeEmbeddingProvider(),
            )
            row = (await DocumentChunkRepository(session).list_by_document(document.id))[0]

            assert row.text == "passage should not be prefixed 0 text"
            assert not row.text.startswith("passage:")

    run_async(scenario())


def test_embed_and_store_chunks_stores_checksum(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            result = make_result(1)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=result,
                embedding_provider=FakeEmbeddingProvider(),
            )
            row = (await DocumentChunkRepository(session).list_by_document(document.id))[0]

            assert row.content_sha256 == result.chunks[0].content_sha256

    run_async(scenario())


def test_embed_and_store_chunks_is_atomic(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(1, text_prefix="old"),
                embedding_provider=FakeEmbeddingProvider(),
            )

            document_id = document.id
            original = document_embedding_service.DocumentChunkRepository.replace_for_document

            async def fail_after_replace(self: DocumentChunkRepository, **kwargs: Any) -> list[Any]:
                await original(self, **kwargs)
                raise RuntimeError("simulated replacement failure")

            monkeypatch.setattr(
                document_embedding_service.DocumentChunkRepository,
                "replace_for_document",
                fail_after_replace,
            )
            with pytest.raises(RuntimeError, match="simulated replacement failure"):
                await embed_and_store_chunks(
                    session,
                    document=document,
                    chunking_result=make_result(1, text_prefix="new"),
                    embedding_provider=FakeEmbeddingProvider(),
                )
            monkeypatch.undo()
            rows = await DocumentChunkRepository(session).list_by_document(document_id)

            assert [row.text for row in rows] == ["old 0 text"]

    run_async(scenario())


def test_second_processing_replaces_old_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(2, text_prefix="first"),
                embedding_provider=FakeEmbeddingProvider(),
            )
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(1, text_prefix="second"),
                embedding_provider=FakeEmbeddingProvider(),
            )
            rows = await DocumentChunkRepository(session).list_by_document(document.id)

            assert [row.text for row in rows] == ["second 0 text"]

    run_async(scenario())


def test_embedding_failure_preserves_old_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(1, text_prefix="old"),
                embedding_provider=FakeEmbeddingProvider(),
            )

            document_id = document.id
            with pytest.raises(EmbeddingError):
                await embed_and_store_chunks(
                    session,
                    document=document,
                    chunking_result=make_result(1, text_prefix="new"),
                    embedding_provider=FakeEmbeddingProvider(fail=True),
                )
            rows = await DocumentChunkRepository(session).list_by_document(document_id)

            assert [row.text for row in rows] == ["old 0 text"]

    run_async(scenario())


def test_database_failure_rolls_back_replacement(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(1, text_prefix="old"),
                embedding_provider=FakeEmbeddingProvider(),
            )

            document_id = document.id

            async def fail_commit() -> None:
                raise RuntimeError("simulated commit failure")

            monkeypatch.setattr(session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="simulated commit failure"):
                await embed_and_store_chunks(
                    session,
                    document=document,
                    chunking_result=make_result(1, text_prefix="new"),
                    embedding_provider=FakeEmbeddingProvider(),
                )
            monkeypatch.undo()
            rows = await DocumentChunkRepository(session).list_by_document(document_id)

            assert [row.text for row in rows] == ["old 0 text"]

    run_async(scenario())


def test_document_status_is_not_changed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session, status=DocumentStatus.PROCESSING)
            await embed_and_store_chunks(
                session,
                document=document,
                chunking_result=make_result(1),
                embedding_provider=FakeEmbeddingProvider(),
            )
            await session.refresh(document)

            assert document.status == DocumentStatus.PROCESSING

    run_async(scenario())


def test_embedding_count_matches_chunk_count_validation(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)

            with pytest.raises(EmbeddingError) as exc_info:
                await embed_and_store_chunks(
                    session,
                    document=document,
                    chunking_result=make_result(2),
                    embedding_provider=FakeEmbeddingProvider(vector_count=1),
                )

            assert exc_info.value.code == EmbeddingFailureCode.EMBEDDING_BATCH_MISMATCH

    run_async(scenario())


def test_embedding_dimension_validation(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = await create_document(session)

            with pytest.raises(EmbeddingError) as exc_info:
                await embed_and_store_chunks(
                    session,
                    document=document,
                    chunking_result=make_result(1),
                    embedding_provider=FakeEmbeddingProvider(dimensions=3),
                )

            assert exc_info.value.code == EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH

    run_async(scenario())
