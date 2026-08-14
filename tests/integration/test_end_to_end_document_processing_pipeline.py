from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import AsyncIterator, Coroutine, Sequence
from contextlib import asynccontextmanager
from math import sqrt
from pathlib import Path
from typing import Any

import pymupdf
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.document_processing.chunking.factory import create_document_chunker
from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor
from app.document_processing.models import ExtractedPage, ExtractionResult
from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.factory import create_embedding_provider
from app.embeddings.models import EmbeddingBatch, EmbeddingVector
from app.models import Document, DocumentAccessScope, DocumentStatus, User, UserRole
from app.repositories.document_chunk_repository import (
    DocumentChunkCreate,
    DocumentChunkRepository,
)
from app.services import document_processing_pipeline as pipeline_module
from app.services.document_processing_pipeline import (
    DOCUMENT_FILE_UNAVAILABLE_REASON,
    DocumentProcessingOutcome,
    DocumentProcessingPipeline,
    TransientDocumentProcessingError,
)
from app.storage.local import LocalFileStorage
from app.workers import document_tasks

pytestmark = pytest.mark.integration

TEST_FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
VIETNAMESE_TEXT = "Nhan vien duoc huong 12 ngay nghi phep co luong moi nam."


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def one_chunk(content: bytes) -> AsyncIterator[bytes]:
    yield content


def checksum_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def checksum_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def unit_vector(position: int = 0, *, dimensions: int = 384) -> tuple[float, ...]:
    values = [0.0] * dimensions
    values[position % dimensions] = 1.0
    return tuple(values)


def make_pdf(page_texts: Sequence[str | None]) -> bytes:
    document = pymupdf.open()
    try:
        for text in page_texts:
            page = document.new_page()
            if text is None:
                continue
            page.insert_text((72, 72), text)

        return document.tobytes()
    finally:
        document.close()


def make_image_only_pdf() -> bytes:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.draw_rect(pymupdf.Rect(72, 72, 144, 144))
        return document.tobytes()
    finally:
        document.close()


def make_encrypted_pdf() -> bytes:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.insert_text((72, 72), "Encrypted content")
        return document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner-password",
            user_pw="user-password",
            permissions=0,
        )
    finally:
        document.close()


class FakeEmbeddingProvider:
    def __init__(
        self,
        *,
        dimensions: int = 384,
        model_name: str = "fake-model",
        fail_code: EmbeddingFailureCode | None = None,
    ) -> None:
        self._dimensions = dimensions
        self._model_name = model_name
        self.fail_code = fail_code
        self.seen_texts: tuple[str, ...] = ()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingBatch:
        self.seen_texts = tuple(texts)
        if self.fail_code is not None:
            raise EmbeddingError(self.fail_code)
        vectors = tuple(
            EmbeddingVector(
                values=unit_vector(index, dimensions=self._dimensions),
                dimensions=self._dimensions,
                normalized=True,
                model_name=self._model_name,
            )
            for index, _text in enumerate(texts)
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
            values=unit_vector(0, dimensions=self._dimensions),
            dimensions=self._dimensions,
            normalized=True,
            model_name=self._model_name,
        )


async def create_user(session: AsyncSession) -> User:
    user = User(
        email=f"pipeline-{uuid.uuid4()}@example.com",
        full_name="Pipeline User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_document(
    session: AsyncSession,
    storage: LocalFileStorage,
    *,
    pdf_bytes: bytes,
    status: DocumentStatus = DocumentStatus.UPLOADED,
    is_deleted: bool = False,
    save_file: bool = True,
    title: str = "Pipeline Document",
) -> Document:
    uploader = await create_user(session)
    storage_key = f"documents/pipeline/{uuid.uuid4()}.pdf"
    if save_file:
        await storage.save(storage_key, one_chunk(pdf_bytes))
    document = Document(
        title=title,
        original_filename="pipeline.pdf",
        storage_key=storage_key,
        mime_type="application/pdf",
        file_size=len(pdf_bytes),
        checksum_sha256=checksum_bytes(pdf_bytes),
        uploaded_by=uploader.id,
        access_scope=DocumentAccessScope.PRIVATE,
        status=status,
        is_deleted=is_deleted,
        error_message="previous error" if status == DocumentStatus.FAILED else None,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


@asynccontextmanager
async def db_session_provider(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def make_extractor(*, max_pages: int = 500) -> PyMuPDFTextExtractor:
    return PyMuPDFTextExtractor(max_pages=max_pages, min_usable_characters=1, sort_text=True)


def make_pipeline(
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalFileStorage,
    *,
    provider: Any | None = None,
    extractor: PyMuPDFTextExtractor | None = None,
    session_provider: Any | None = None,
) -> DocumentProcessingPipeline:
    return DocumentProcessingPipeline(
        storage=storage,
        extractor=extractor or make_extractor(),
        chunker=create_document_chunker(
            Settings(
                chunk_target_tokens=40,
                chunk_max_tokens=60,
                chunk_overlap_tokens=5,
                chunk_min_tokens=0,
            )
        ),
        embedding_provider=provider or FakeEmbeddingProvider(),
        session_provider=session_provider or (lambda: db_session_provider(session_factory)),
        max_pdf_bytes=10 * 1024 * 1024,
        read_chunk_size_bytes=128,
    )


def install_worker_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalFileStorage,
    *,
    provider: Any | None = None,
    extractor: PyMuPDFTextExtractor | None = None,
) -> None:
    monkeypatch.setattr(
        document_tasks,
        "worker_session",
        lambda: db_session_provider(session_factory),
    )

    async def execute(document_id: uuid.UUID):
        pipeline = make_pipeline(
            session_factory,
            storage,
            provider=provider,
            extractor=extractor,
        )
        return await pipeline.process(document_id)

    monkeypatch.setattr(document_tasks, "execute_document_processing", execute)


async def get_document(session: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await session.get(Document, document_id)
    assert document is not None
    return document


async def get_chunks(session: AsyncSession, document_id: uuid.UUID):
    return await DocumentChunkRepository(session).list_by_document(document_id)


async def seed_existing_chunk(session: AsyncSession, document_id: uuid.UUID, text: str) -> None:
    await DocumentChunkRepository(session).replace_for_document(
        document_id=document_id,
        chunks=(
            DocumentChunkCreate(
                chunk_index=0,
                text=text,
                token_count=4,
                character_count=len(text),
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                overlap_token_count=0,
                content_sha256=checksum_text(text),
                embedding=unit_vector(0),
                embedding_provider="sentence_transformers",
                embedding_model="old-model",
                embedding_dimensions=384,
            ),
        ),
    )
    await session.commit()


def test_successful_pipeline_sets_document_ready(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        pdf_bytes = make_pdf(["Pipeline success page one.", "Pipeline success page two."])
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=pdf_bytes,
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id

        result = await make_pipeline(async_session_factory_for_tests, storage).process(document_id)

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            assert result.outcome == DocumentProcessingOutcome.READY
            assert document.status == DocumentStatus.READY
            assert document.error_message is None

    run_async(scenario())


def test_successful_pipeline_persists_chunks_vectors_metadata_and_checksums(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        pdf_bytes = make_pdf(["First persisted page text.", "Second persisted page text."])
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=pdf_bytes,
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id

        await make_pipeline(async_session_factory_for_tests, storage).process(document_id)

        async with async_session_factory_for_tests() as session:
            rows = await get_chunks(session, document_id)
            assert rows
            assert [row.chunk_index for row in rows] == list(range(len(rows)))
            assert all(len(row.embedding) == 384 for row in rows)
            assert all(row.page_numbers for row in rows)
            assert all(row.content_sha256 == checksum_text(row.text) for row in rows)
            assert all(not row.text.startswith("passage:") for row in rows)

    run_async(scenario())


def test_successful_pipeline_task_result_is_safe(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        marker = "CONFIDENTIAL_PIPELINE_TEST_MARKER"
        pdf_bytes = make_pdf([marker])
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=pdf_bytes,
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id

        result = await make_pipeline(async_session_factory_for_tests, storage).process(document_id)
        payload = result.to_task_result()

        assert payload["outcome"] == "READY"
        assert "chunk" not in payload
        assert "embedding" not in payload
        assert marker not in repr(payload)

    run_async(scenario())


async def process_document_through_worker(
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalFileStorage,
    document_id: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: Any | None = None,
    extractor: PyMuPDFTextExtractor | None = None,
) -> dict[str, Any]:
    install_worker_pipeline(
        monkeypatch,
        session_factory,
        storage,
        provider=provider,
        extractor=extractor,
    )
    return await document_tasks.process_document_async(document_id)


def test_corrupted_pdf_pipeline_sets_failed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        pdf_bytes = b"%PDF-not-a-valid-pdf"
        async with async_session_factory_for_tests() as session:
            document = await create_document(session, storage, pdf_bytes=pdf_bytes)
            document_id = document.id

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            rows = await get_chunks(session, document_id)
            assert result["outcome"] == "FAILED"
            assert result["reason"] == "INVALID_PDF"
            assert document.status == DocumentStatus.FAILED
            assert rows == []
            assert "%PDF" not in (document.error_message or "")

    run_async(scenario())


def test_encrypted_pdf_pipeline_sets_failed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(session, storage, pdf_bytes=make_encrypted_pdf())
            document_id = document.id

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            assert result["reason"] == "ENCRYPTED_PDF"
            assert document.status == DocumentStatus.FAILED
            assert document.error_message == "Password-protected PDF files are not supported."

    run_async(scenario())


def test_blank_pdf_pipeline_sets_failed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(session, storage, pdf_bytes=make_pdf([None]))
            document_id = document.id

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            assert result["reason"] == "PDF_NO_USABLE_TEXT"
            assert document.status == DocumentStatus.FAILED

    run_async(scenario())


def test_image_only_pdf_pipeline_sets_failed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(session, storage, pdf_bytes=make_image_only_pdf())
            document_id = document.id

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            assert result["reason"] == "PDF_NO_USABLE_TEXT"
            assert document.status == DocumentStatus.FAILED

    run_async(scenario())


def test_page_limit_pipeline_sets_failed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(session, storage, pdf_bytes=make_pdf(["one", "two"]))
            document_id = document.id

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
            extractor=make_extractor(max_pages=1),
        )

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            assert result["reason"] == "PDF_PAGE_LIMIT_EXCEEDED"
            assert document.status == DocumentStatus.FAILED

    run_async(scenario())


def test_missing_file_pipeline_sets_failed_and_does_not_delete_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["missing file"]),
                save_file=False,
            )
            document_id = document.id

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            assert result["reason"] == DOCUMENT_FILE_UNAVAILABLE_REASON
            assert document.status == DocumentStatus.FAILED
            assert document.is_deleted is False

    run_async(scenario())


def test_embedding_failure_preserves_existing_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["new text should not replace old chunk"]),
                status=DocumentStatus.FAILED,
            )
            document_id = document.id
            await seed_existing_chunk(session, document_id, "old preserved chunk")

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
            provider=FakeEmbeddingProvider(
                fail_code=EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH
            ),
        )

        async with async_session_factory_for_tests() as session:
            rows = await get_chunks(session, document_id)
            document = await get_document(session, document_id)
            assert result["reason"] == "EMBEDDING_DIMENSION_MISMATCH"
            assert [row.text for row in rows] == ["old preserved chunk"]
            assert document.status == DocumentStatus.FAILED

    run_async(scenario())


def test_database_failure_preserves_existing_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingRepository(DocumentChunkRepository):
        async def replace_for_document(self, *, document_id, chunks):
            await super().replace_for_document(document_id=document_id, chunks=chunks)
            raise OperationalError("statement", {}, RuntimeError("temporary database failure"))

    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["database failure should preserve old chunk"]),
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id
            await seed_existing_chunk(session, document_id, "old database chunk")

        monkeypatch.setattr(pipeline_module, "DocumentChunkRepository", FailingRepository)
        with pytest.raises(TransientDocumentProcessingError):
            await make_pipeline(async_session_factory_for_tests, storage).process(document_id)

        async with async_session_factory_for_tests() as session:
            rows = await get_chunks(session, document_id)
            document = await get_document(session, document_id)
            assert [row.text for row in rows] == ["old database chunk"]
            assert document.status == DocumentStatus.PROCESSING

    run_async(scenario())


def test_successful_retry_replaces_existing_chunks_atomically(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["successful retry replacement text"]),
                status=DocumentStatus.FAILED,
            )
            document_id = document.id
            await seed_existing_chunk(session, document_id, "old retry chunk")

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )

        async with async_session_factory_for_tests() as session:
            rows = await get_chunks(session, document_id)
            document = await get_document(session, document_id)
            assert result["outcome"] == "READY"
            assert document.status == DocumentStatus.READY
            assert [row.text for row in rows] != ["old retry chunk"]
            assert len(rows) == result["chunk_count"]

    run_async(scenario())


def test_duplicate_task_delivery_creates_no_duplicate_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["idempotent text"]),
            )
            document_id = document.id

        first = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )
        second = await document_tasks.process_document_async(document_id)

        async with async_session_factory_for_tests() as session:
            count = await DocumentChunkRepository(session).count_by_document(document_id)
            assert first["outcome"] == "READY"
            assert second["outcome"] == "ALREADY_READY"
            assert count == first["chunk_count"]

    run_async(scenario())


def test_processing_document_is_skipped(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["already processing"]),
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id

        install_worker_pipeline(monkeypatch, async_session_factory_for_tests, storage)
        result = await document_tasks.process_document_async(document_id)

        assert result["outcome"] == "ALREADY_PROCESSING"

    run_async(scenario())


@pytest.mark.parametrize(
    ("status", "expected_outcome"),
    [
        (DocumentStatus.READY, "ALREADY_READY"),
        (DocumentStatus.ARCHIVED, "ARCHIVED"),
    ],
)
def test_terminal_documents_are_skipped(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: DocumentStatus,
    expected_outcome: str,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["terminal"]),
                status=status,
            )
            document_id = document.id

        install_worker_pipeline(monkeypatch, async_session_factory_for_tests, storage)
        result = await document_tasks.process_document_async(document_id)

        assert result["outcome"] == expected_outcome

    run_async(scenario())


def test_deleted_document_is_skipped(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["deleted"]),
                is_deleted=True,
            )
            document_id = document.id

        install_worker_pipeline(monkeypatch, async_session_factory_for_tests, storage)
        result = await document_tasks.process_document_async(document_id)

        assert result["outcome"] == "DELETED"

    run_async(scenario())


def test_document_deleted_during_processing_is_not_marked_ready(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["delete while processing"]),
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id

        calls = 0

        @asynccontextmanager
        async def deleting_session_provider() -> AsyncIterator[AsyncSession]:
            nonlocal calls
            calls += 1
            if calls == 2:
                async with async_session_factory_for_tests() as delete_session:
                    document = await get_document(delete_session, document_id)
                    document.is_deleted = True
                    await delete_session.commit()
            async with async_session_factory_for_tests() as session:
                yield session

        result = await make_pipeline(
            async_session_factory_for_tests,
            storage,
            session_provider=deleting_session_provider,
        ).process(document_id)

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            rows = await get_chunks(session, document_id)
            assert result.outcome == DocumentProcessingOutcome.DELETED
            assert document.status == DocumentStatus.FAILED
            assert document.is_deleted is True
            assert rows == []

    run_async(scenario())


def test_direct_permissions_do_not_affect_worker_processing(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=make_pdf(["worker ignores API permissions"]),
            )
            document_id = document.id

        result = await process_document_through_worker(
            async_session_factory_for_tests,
            storage,
            document_id,
            monkeypatch,
        )

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            assert result["outcome"] == "READY"
            assert document.status == DocumentStatus.READY

    run_async(scenario())


@pytest.mark.processing_pipeline_model_integration
def test_real_pipeline_embeds_and_persists_vietnamese_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        provider = create_embedding_provider(Settings())
        pdf_bytes = make_pdf([VIETNAMESE_TEXT])
        async with async_session_factory_for_tests() as session:
            document = await create_document(
                session,
                storage,
                pdf_bytes=pdf_bytes,
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id

        result = await make_pipeline(
            async_session_factory_for_tests,
            storage,
            provider=provider,
        ).process(document_id)

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            rows = await get_chunks(session, document_id)
            norms = [sqrt(sum(value * value for value in row.embedding)) for row in rows]
            assert result.outcome == DocumentProcessingOutcome.READY
            assert document.status == DocumentStatus.READY
            assert len(rows) == result.chunk_count
            assert all(len(row.embedding) == 384 for row in rows)
            assert all(abs(norm - 1.0) <= 1e-3 for norm in norms)

    run_async(scenario())


class FakeImageExtractionRouter:
    def __init__(self, expected_mime_type: str, expected_content: bytes) -> None:
        self.expected_mime_type = expected_mime_type
        self.expected_content = expected_content
        self.calls = 0

    async def extract_document(self, metadata, source: bytes):  # noqa: ANN001
        self.calls += 1
        assert metadata.mime_type == self.expected_mime_type
        assert source == self.expected_content
        text = "OCR image policy text page one."
        page = ExtractedPage(
            page_number=1,
            text=text,
            raw_character_count=len(text),
            normalized_character_count=len(text),
            usable_character_count=len(text.replace(" ", "")),
            extraction_method="ocr_fake",
            source_type="png",
            width=120,
            height=80,
        )
        return ExtractionResult(
            page_count=1,
            pages=(page,),
            pages_with_usable_text=1,
            total_raw_characters=page.raw_character_count,
            total_normalized_characters=page.normalized_character_count,
            total_usable_characters=page.usable_character_count,
        )


def test_pipeline_processes_image_document_with_ocr_text_and_page_metadata(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        image_bytes = b"\x89PNG\r\n\x1a\nvalid-enough-uploaded-image"
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            storage_key = f"documents/pipeline/{uuid.uuid4()}.png"
            await storage.save(storage_key, one_chunk(image_bytes))
            document = Document(
                title="Pipeline Image Document",
                original_filename="scan.png",
                storage_key=storage_key,
                mime_type="image/png",
                file_size=len(image_bytes),
                checksum_sha256=checksum_bytes(image_bytes),
                uploaded_by=uploader.id,
                access_scope=DocumentAccessScope.PRIVATE,
                status=DocumentStatus.PROCESSING,
            )
            session.add(document)
            await session.commit()
            await session.refresh(document)
            document_id = document.id

        extractor = FakeImageExtractionRouter("image/png", image_bytes)
        result = await make_pipeline(
            async_session_factory_for_tests,
            storage,
            extractor=extractor,  # type: ignore[arg-type]
        ).process(document_id)

        async with async_session_factory_for_tests() as session:
            document = await get_document(session, document_id)
            rows = await get_chunks(session, document_id)
            assert result.outcome == DocumentProcessingOutcome.READY
            assert document.status == DocumentStatus.READY
            assert extractor.calls == 1
            assert len(rows) == result.chunk_count
            assert rows[0].page_numbers == [1]
            assert rows[0].start_page == 1
            assert rows[0].end_page == 1
            assert "OCR image policy text" in rows[0].text

    run_async(scenario())
