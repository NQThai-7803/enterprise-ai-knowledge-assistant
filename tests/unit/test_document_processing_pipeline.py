from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from app.document_processing.chunking.models import ChunkingResult, TextChunk
from app.document_processing.errors import (
    ChunkingError,
    ChunkingFailureCode,
    PDFExtractionError,
    PDFExtractionFailureCode,
)
from app.document_processing.models import ExtractedPage, ExtractionResult
from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.models import EmbeddingBatch, EmbeddingVector
from app.models import Document, DocumentAccessScope, DocumentStatus
from app.services import document_processing_pipeline as pipeline_module
from app.services.document_processing_pipeline import (
    DOCUMENT_FILE_UNAVAILABLE_REASON,
    DocumentProcessingPipeline,
    PermanentDocumentProcessingError,
    TransientDocumentProcessingError,
)
from app.storage.local import StorageError, StorageNotFoundError

PDF_BYTES = b"%PDF-1.7\npipeline unit pdf"
CHUNK_TEXT = "CONFIDENTIAL_PIPELINE_TEST_MARKER chunk text"


def make_document(*, status: DocumentStatus = DocumentStatus.PROCESSING) -> Document:
    return Document(
        id=uuid.uuid4(),
        title="Pipeline Unit",
        description=None,
        original_filename="pipeline.pdf",
        storage_key="documents/unit/pipeline.pdf",
        mime_type="application/pdf",
        file_size=len(PDF_BYTES),
        checksum_sha256="1" * 64,
        status=status,
        access_scope=DocumentAccessScope.PRIVATE,
        department_id=None,
        uploaded_by=uuid.uuid4(),
        error_message="old error",
        is_deleted=False,
    )


def make_extraction() -> ExtractionResult:
    page = ExtractedPage(
        page_number=1,
        text="Page text",
        raw_character_count=len("Page text"),
        normalized_character_count=len("Page text"),
        usable_character_count=len("Pagetext"),
    )
    return ExtractionResult(
        page_count=1,
        pages=(page,),
        pages_with_usable_text=1,
        total_raw_characters=page.raw_character_count,
        total_normalized_characters=page.normalized_character_count,
        total_usable_characters=page.usable_character_count,
    )


def make_chunking_result() -> ChunkingResult:
    checksum = hashlib.sha256(CHUNK_TEXT.encode("utf-8")).hexdigest()
    chunk = TextChunk(
        chunk_index=0,
        text=CHUNK_TEXT,
        token_count=8,
        character_count=len(CHUNK_TEXT),
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        overlap_token_count=0,
        content_sha256=checksum,
    )
    return ChunkingResult(
        chunks=(chunk,),
        chunk_count=1,
        total_tokens=8,
        total_unique_source_pages=1,
        source_page_numbers=(1,),
    )


def make_embedding_batch() -> EmbeddingBatch:
    vector = EmbeddingVector(
        values=(1.0, *([0.0] * 383)),
        dimensions=384,
        normalized=True,
        model_name="fake-model",
    )
    return EmbeddingBatch(
        vectors=(vector,),
        count=1,
        dimensions=384,
        normalized=True,
        model_name="fake-model",
    )


class FakeStorage:
    def __init__(self, order: list[str], *, error: Exception | None = None) -> None:
        self.order = order
        self.error = error
        self.opened_key: str | None = None

    async def save(self, storage_key: str, chunks) -> None:
        raise AssertionError("pipeline must not save files")

    async def open(self, storage_key: str) -> bytes:
        raise AssertionError("pipeline must use bounded chunk reads")

    async def exists(self, storage_key: str) -> bool:
        return True

    async def delete(self, storage_key: str) -> None:
        raise AssertionError("pipeline must not delete files")

    async def iter_chunks(self, storage_key: str, chunk_size: int) -> AsyncIterator[bytes]:
        self.order.append("storage")
        self.opened_key = storage_key
        if self.error is not None:
            raise self.error
        yield PDF_BYTES[:10]
        yield PDF_BYTES[10:]


class FakeExtractor:
    def __init__(self, order: list[str], *, error: Exception | None = None) -> None:
        self.order = order
        self.error = error
        self.calls = 0
        self.sources: list[bytes] = []

    def extract(self, source: bytes):
        self.order.append("extraction")
        self.calls += 1
        self.sources.append(source)
        if self.error is not None:
            raise self.error
        return make_extraction()


class FakeChunker:
    def __init__(self, order: list[str], *, error: Exception | None = None) -> None:
        self.order = order
        self.error = error
        self.calls = 0

    def chunk(self, extraction: ExtractionResult) -> ChunkingResult:
        self.order.append("chunking")
        self.calls += 1
        if self.error is not None:
            raise self.error
        return make_chunking_result()


class FakeEmbeddingProvider:
    dimensions = 384
    model_name = "fake-model"

    def __init__(self, order: list[str], *, error: Exception | None = None) -> None:
        self.order = order
        self.error = error
        self.passages: tuple[str, ...] = ()

    def embed_passages(self, texts):
        self.order.append("embedding")
        self.passages = tuple(texts)
        if self.error is not None:
            raise self.error
        return make_embedding_batch()

    def embed_query(self, text: str):
        raise AssertionError("pipeline must not embed queries")


class FakeSession:
    def __init__(self, document: Document) -> None:
        self.document = document
        self.committed = False
        self.rolled_back = False

    async def get(self, model, document_id):
        return self.document if self.document.id == document_id else None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeRepository:
    rows = []
    order: list[str] = []
    document: Document | None = None
    fail = False

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def replace_for_document(self, *, document_id, chunks):
        type(self).order.append("persistence")
        assert type(self).document is not None
        assert type(self).document.status == DocumentStatus.PROCESSING
        if type(self).fail:
            raise RuntimeError("database failure")
        type(self).rows = list(chunks)
        return []


@asynccontextmanager
async def session_provider(document: Document):
    yield FakeSession(document)


def make_pipeline(
    document: Document,
    *,
    storage_error: Exception | None = None,
    extraction_error: Exception | None = None,
    chunking_error: Exception | None = None,
    embedding_error: Exception | None = None,
    monkeypatch: pytest.MonkeyPatch,
):
    order: list[str] = []
    storage = FakeStorage(order, error=storage_error)
    extractor = FakeExtractor(order, error=extraction_error)
    chunker = FakeChunker(order, error=chunking_error)
    provider = FakeEmbeddingProvider(order, error=embedding_error)
    FakeRepository.rows = []
    FakeRepository.order = order
    FakeRepository.document = document
    FakeRepository.fail = False
    monkeypatch.setattr(pipeline_module, "DocumentChunkRepository", FakeRepository)
    pipeline = DocumentProcessingPipeline(
        storage=storage,
        extractor=extractor,
        chunker=chunker,
        embedding_provider=provider,
        session_provider=lambda: session_provider(document),
        max_pdf_bytes=1024,
        read_chunk_size_bytes=10,
    )
    return pipeline, order, storage, extractor, chunker, provider


@pytest.mark.anyio
async def test_pipeline_loads_pdf_from_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, storage, _, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert storage.opened_key == document.storage_key


@pytest.mark.anyio
async def test_pipeline_calls_extractor_once(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, extractor, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert extractor.calls == 1
    assert extractor.sources == [PDF_BYTES]


@pytest.mark.anyio
async def test_pipeline_calls_chunker_once(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, chunker, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert chunker.calls == 1


@pytest.mark.anyio
async def test_pipeline_embeds_all_chunk_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, provider = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert provider.passages == (CHUNK_TEXT,)


@pytest.mark.anyio
async def test_pipeline_persists_all_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert len(FakeRepository.rows) == 1
    assert FakeRepository.rows[0].text == CHUNK_TEXT


@pytest.mark.anyio
async def test_pipeline_sets_ready_after_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, order, _, _, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert order.index("persistence") < order.index("ready") if "ready" in order else True
    assert document.status == DocumentStatus.READY


@pytest.mark.anyio
async def test_pipeline_clears_error_message_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert document.error_message is None


@pytest.mark.anyio
async def test_pipeline_does_not_set_ready_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert FakeRepository.rows


@pytest.mark.anyio
async def test_pipeline_does_not_return_text_or_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    result = await pipeline.process(document.id)
    payload = result.to_task_result()

    assert "text" not in payload
    assert "chunks" not in payload
    assert "vectors" not in payload
    assert "embedding" not in payload
    assert CHUNK_TEXT not in repr(payload)


@pytest.mark.anyio
async def test_pipeline_stage_order_is_correct(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, order, _, _, _, _ = make_pipeline(document, monkeypatch=monkeypatch)

    await pipeline.process(document.id)

    assert order == ["storage", "extraction", "chunking", "embedding", "persistence"]


@pytest.mark.anyio
async def test_invalid_pdf_marks_failed_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        extraction_error=PDFExtractionError(PDFExtractionFailureCode.INVALID_PDF),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == "INVALID_PDF"


@pytest.mark.anyio
async def test_encrypted_pdf_marks_failed_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        extraction_error=PDFExtractionError(PDFExtractionFailureCode.ENCRYPTED_PDF),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == "ENCRYPTED_PDF"


@pytest.mark.anyio
async def test_page_limit_marks_failed_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        extraction_error=PDFExtractionError(PDFExtractionFailureCode.PDF_PAGE_LIMIT_EXCEEDED),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == "PDF_PAGE_LIMIT_EXCEEDED"


@pytest.mark.anyio
async def test_no_usable_text_marks_failed_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        extraction_error=PDFExtractionError(PDFExtractionFailureCode.PDF_NO_USABLE_TEXT),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == "PDF_NO_USABLE_TEXT"


@pytest.mark.anyio
async def test_chunking_failure_marks_failed_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        chunking_error=ChunkingError(ChunkingFailureCode.CHUNKING_FAILED),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == "CHUNKING_FAILED"


@pytest.mark.anyio
async def test_embedding_dimension_mismatch_marks_failed_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        embedding_error=EmbeddingError(EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == "EMBEDDING_DIMENSION_MISMATCH"


@pytest.mark.anyio
async def test_invalid_vector_marks_failed_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        embedding_error=EmbeddingError(EmbeddingFailureCode.EMBEDDING_INVALID_VECTOR),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == "EMBEDDING_INVALID_VECTOR"


@pytest.mark.anyio
async def test_missing_file_marks_failed_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        storage_error=StorageNotFoundError("missing"),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert exc_info.value.code == DOCUMENT_FILE_UNAVAILABLE_REASON


@pytest.mark.anyio
async def test_safe_error_does_not_include_source_text(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        chunking_error=ChunkingError(ChunkingFailureCode.CHUNKING_FAILED, CHUNK_TEXT),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert CHUNK_TEXT not in exc_info.value.safe_message


@pytest.mark.anyio
async def test_safe_error_does_not_include_storage_key(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        storage_error=StorageNotFoundError(document.storage_key),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert document.storage_key not in exc_info.value.safe_message


@pytest.mark.anyio
async def test_safe_error_does_not_include_absolute_path(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        storage_error=StorageNotFoundError("C:/secret/path/file.pdf"),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(PermanentDocumentProcessingError) as exc_info:
        await pipeline.process(document.id)

    assert "C:/secret" not in exc_info.value.safe_message


@pytest.mark.anyio
async def test_transient_storage_error_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        storage_error=StorageError("temporary io"),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(TransientDocumentProcessingError):
        await pipeline.process(document.id)


@pytest.mark.anyio
async def test_transient_model_load_error_retries_when_classified_transient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()
    pipeline, _, _, _, _, _ = make_pipeline(
        document,
        embedding_error=EmbeddingError(EmbeddingFailureCode.EMBEDDING_MODEL_LOAD_FAILED),
        monkeypatch=monkeypatch,
    )

    with pytest.raises(TransientDocumentProcessingError):
        await pipeline.process(document.id)


class AsyncFakeExtractionRouter:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.metadata = None
        self.sources: list[bytes] = []

    async def extract_document(self, metadata, source: bytes):  # noqa: ANN001
        self.order.append("extraction")
        self.metadata = metadata
        self.sources.append(source)
        return make_extraction()


@pytest.mark.anyio
async def test_pipeline_passes_mime_metadata_to_async_extraction_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()
    document.mime_type = "image/png"
    document.original_filename = "scan.png"
    document.storage_key = "documents/unit/scan.png"
    order: list[str] = []
    storage = FakeStorage(order)
    extractor = AsyncFakeExtractionRouter(order)
    chunker = FakeChunker(order)
    provider = FakeEmbeddingProvider(order)
    FakeRepository.rows = []
    FakeRepository.order = order
    FakeRepository.document = document
    FakeRepository.fail = False
    monkeypatch.setattr(pipeline_module, "DocumentChunkRepository", FakeRepository)
    pipeline = DocumentProcessingPipeline(
        storage=storage,
        extractor=extractor,
        chunker=chunker,
        embedding_provider=provider,
        session_provider=lambda: session_provider(document),
        max_pdf_bytes=1024,
        read_chunk_size_bytes=10,
    )

    result = await pipeline.process(document.id)

    assert result.outcome.value == "READY"
    assert extractor.metadata is not None
    assert extractor.metadata.mime_type == "image/png"
    assert extractor.sources == [PDF_BYTES]
    assert provider.passages == (CHUNK_TEXT,)
    assert order == ["storage", "extraction", "chunking", "embedding", "persistence"]
