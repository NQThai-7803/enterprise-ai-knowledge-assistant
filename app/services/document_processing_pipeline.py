from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.document_processing.chunking.base import TextChunker
from app.document_processing.chunking.factory import create_document_chunker
from app.document_processing.chunking.models import ChunkingResult
from app.document_processing.errors import (
    SAFE_CHUNKING_MESSAGES,
    SAFE_PDF_EXTRACTION_MESSAGES,
    ChunkingError,
    DocumentExtractionError,
    PDFExtractionError,
)
from app.document_processing.extraction_router import create_extraction_router
from app.embeddings.base import EmbeddingProvider
from app.embeddings.constants import EMBEDDING_SCHEMA_DIMENSIONS
from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.factory import create_embedding_provider
from app.models import Document, DocumentStatus
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.services.document_embedding_service import (
    build_document_chunk_rows,
    validate_embedding_batch,
)
from app.services.document_processing_status_service import sanitize_processing_error
from app.storage.base import FileStorage
from app.storage.factory import get_file_storage
from app.storage.local import StorageError, StorageKeyError, StorageNotFoundError
from app.workers.worker_database import worker_session

logger = logging.getLogger(__name__)

DOCUMENT_FILE_UNAVAILABLE_REASON = "DOCUMENT_FILE_UNAVAILABLE"
DOCUMENT_DELETED_DURING_PROCESSING_REASON = "DOCUMENT_DELETED_DURING_PROCESSING"
DOCUMENT_PROCESSING_FAILED_REASON = "DOCUMENT_PROCESSING_FAILED"
DOCUMENT_PROCESSING_TRANSIENT_FAILED_REASON = "DOCUMENT_PROCESSING_TRANSIENT_FAILED"
DOCUMENT_NOT_PROCESSING_REASON = "DOCUMENT_NOT_PROCESSING"

DOCUMENT_FILE_UNAVAILABLE_MESSAGE = "The document file is unavailable."
DOCUMENT_DELETED_DURING_PROCESSING_MESSAGE = (
    "Document processing was cancelled because the document was deleted."
)
DOCUMENT_PROCESSING_FAILED_MESSAGE = "The document processing operation failed."
DOCUMENT_PROCESSING_TRANSIENT_FAILED_MESSAGE = "Document processing failed after retryable error."


class DocumentProcessingOutcome(StrEnum):
    READY = "READY"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    NOT_FOUND = "NOT_FOUND"
    INVALID_DOCUMENT_ID = "INVALID_DOCUMENT_ID"
    DELETED = "DELETED"
    ALREADY_PROCESSING = "ALREADY_PROCESSING"
    ALREADY_READY = "ALREADY_READY"
    ARCHIVED = "ARCHIVED"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


@dataclass(frozen=True, slots=True)
class DocumentProcessingResult:
    document_id: UUID
    outcome: DocumentProcessingOutcome
    status: DocumentStatus | None
    reason: str | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    total_tokens: int | None = None
    embedding_dimensions: int | None = None

    def to_task_result(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "document_id": str(self.document_id),
            "outcome": self.outcome.value,
            "status": self.status.value if self.status is not None else None,
        }
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.page_count is not None:
            payload["page_count"] = self.page_count
        if self.chunk_count is not None:
            payload["chunk_count"] = self.chunk_count
        if self.total_tokens is not None:
            payload["total_tokens"] = self.total_tokens
        if self.embedding_dimensions is not None:
            payload["embedding_dimensions"] = self.embedding_dimensions
        return payload


class PermanentDocumentProcessingError(Exception):
    def __init__(
        self,
        *,
        code: str,
        safe_message: str,
        outcome: DocumentProcessingOutcome = DocumentProcessingOutcome.FAILED,
        status: DocumentStatus | None = DocumentStatus.FAILED,
        mark_failed: bool = True,
    ) -> None:
        self.code = code
        self.safe_message = sanitize_processing_error(safe_message)
        self.outcome = outcome
        self.status = status
        self.mark_failed = mark_failed
        super().__init__(self.safe_message)


class TransientDocumentProcessingError(Exception):
    def __init__(
        self,
        *,
        code: str = DOCUMENT_PROCESSING_TRANSIENT_FAILED_REASON,
        safe_message: str = DOCUMENT_PROCESSING_TRANSIENT_FAILED_MESSAGE,
    ) -> None:
        self.code = code
        self.safe_message = sanitize_processing_error(safe_message)
        super().__init__(self.safe_message)


@dataclass(frozen=True, slots=True)
class DocumentProcessingMetadata:
    document_id: UUID
    storage_key: str
    file_size: int
    mime_type: str


SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class DocumentProcessingPipeline:
    def __init__(
        self,
        *,
        storage: FileStorage,
        extractor: object,
        chunker: TextChunker,
        embedding_provider: EmbeddingProvider,
        session_provider: SessionProvider,
        max_pdf_bytes: int,
        read_chunk_size_bytes: int,
    ) -> None:
        if max_pdf_bytes <= 0:
            msg = "max_pdf_bytes must be greater than zero."
            raise ValueError(msg)
        if read_chunk_size_bytes <= 0:
            msg = "read_chunk_size_bytes must be greater than zero."
            raise ValueError(msg)
        self.storage = storage
        self.extractor = extractor
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.session_provider = session_provider
        self.max_pdf_bytes = max_pdf_bytes
        self.read_chunk_size_bytes = read_chunk_size_bytes

    async def process(self, document_id: UUID) -> DocumentProcessingResult:
        metadata = await self._load_processing_metadata(document_id)
        pdf_bytes = await self._load_pdf_bytes(metadata)
        extraction = await self._extract(metadata, pdf_bytes)
        chunking_result = self._chunk(extraction)
        embedding_batch = self._embed(chunking_result)
        rows = build_document_chunk_rows(chunking_result.chunks, embedding_batch.vectors)
        return await self._persist_chunks_and_ready(
            metadata,
            page_count=extraction.page_count,
            chunking_result=chunking_result,
            chunk_rows=rows,
        )

    async def _load_processing_metadata(self, document_id: UUID) -> DocumentProcessingMetadata:
        async with self.session_provider() as session:
            document = await session.get(Document, document_id)
            if document is None:
                raise PermanentDocumentProcessingError(
                    code=DocumentProcessingOutcome.NOT_FOUND.value,
                    safe_message="Document was not found.",
                    outcome=DocumentProcessingOutcome.NOT_FOUND,
                    status=None,
                    mark_failed=False,
                )
            if document.is_deleted:
                raise PermanentDocumentProcessingError(
                    code=DocumentProcessingOutcome.DELETED.value,
                    safe_message=DOCUMENT_DELETED_DURING_PROCESSING_MESSAGE,
                    outcome=DocumentProcessingOutcome.DELETED,
                    status=document.status,
                    mark_failed=False,
                )
            if document.status != DocumentStatus.PROCESSING:
                raise PermanentDocumentProcessingError(
                    code=DOCUMENT_NOT_PROCESSING_REASON,
                    safe_message=DOCUMENT_PROCESSING_FAILED_MESSAGE,
                    outcome=DocumentProcessingOutcome.NOT_ELIGIBLE,
                    status=document.status,
                    mark_failed=False,
                )
            return DocumentProcessingMetadata(
                document_id=document.id,
                storage_key=document.storage_key,
                file_size=document.file_size,
                mime_type=document.mime_type,
            )

    async def _load_pdf_bytes(self, metadata: DocumentProcessingMetadata) -> bytes:
        chunks: list[bytes] = []
        total_size = 0
        try:
            async for chunk in self.storage.iter_chunks(
                metadata.storage_key,
                self.read_chunk_size_bytes,
            ):
                if not chunk:
                    continue
                total_size += len(chunk)
                if total_size > self.max_pdf_bytes:
                    raise PermanentDocumentProcessingError(
                        code=DOCUMENT_FILE_UNAVAILABLE_REASON,
                        safe_message=DOCUMENT_FILE_UNAVAILABLE_MESSAGE,
                    )
                chunks.append(bytes(chunk))
        except (StorageNotFoundError, StorageKeyError) as exc:
            raise PermanentDocumentProcessingError(
                code=DOCUMENT_FILE_UNAVAILABLE_REASON,
                safe_message=DOCUMENT_FILE_UNAVAILABLE_MESSAGE,
            ) from exc
        except StorageError as exc:
            raise TransientDocumentProcessingError() from exc

        if total_size <= 0 or total_size != metadata.file_size:
            raise PermanentDocumentProcessingError(
                code=DOCUMENT_FILE_UNAVAILABLE_REASON,
                safe_message=DOCUMENT_FILE_UNAVAILABLE_MESSAGE,
            )
        return b"".join(chunks)

    async def _extract(self, metadata: DocumentProcessingMetadata, pdf_bytes: bytes):
        try:
            extract_document = getattr(self.extractor, "extract_document", None)
            if extract_document is not None:
                result = extract_document(metadata, pdf_bytes)
            else:
                result = self.extractor.extract(pdf_bytes)  # type: ignore[attr-defined]
            if inspect.isawaitable(result):
                return await result
            return result
        except DocumentExtractionError as exc:
            raise PermanentDocumentProcessingError(
                code=exc.code.value,
                safe_message=exc.safe_message,
            ) from exc
        except PDFExtractionError as exc:
            raise PermanentDocumentProcessingError(
                code=exc.code.value,
                safe_message=SAFE_PDF_EXTRACTION_MESSAGES[exc.code],
            ) from exc

    def _chunk(self, extraction) -> ChunkingResult:
        try:
            return self.chunker.chunk(extraction)
        except ChunkingError as exc:
            raise PermanentDocumentProcessingError(
                code=exc.code.value,
                safe_message=SAFE_CHUNKING_MESSAGES[exc.code],
            ) from exc

    def _embed(self, chunking_result: ChunkingResult):
        try:
            batch = self.embedding_provider.embed_passages(
                tuple(chunk.text for chunk in chunking_result.chunks)
            )
            validate_embedding_batch(
                batch,
                expected_count=chunking_result.chunk_count,
                model_name=self.embedding_provider.model_name,
            )
            return batch
        except EmbeddingError as exc:
            if exc.code in {
                EmbeddingFailureCode.EMBEDDING_MODEL_LOAD_FAILED,
                EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED,
            }:
                raise TransientDocumentProcessingError(
                    code=exc.code.value,
                    safe_message=exc.safe_message,
                ) from exc
            raise PermanentDocumentProcessingError(
                code=exc.code.value,
                safe_message=exc.safe_message,
            ) from exc

    async def _persist_chunks_and_ready(
        self,
        metadata: DocumentProcessingMetadata,
        *,
        page_count: int,
        chunking_result: ChunkingResult,
        chunk_rows,
    ) -> DocumentProcessingResult:
        async with self.session_provider() as session:
            document = await session.get(Document, metadata.document_id)
            if document is None:
                raise PermanentDocumentProcessingError(
                    code=DocumentProcessingOutcome.NOT_FOUND.value,
                    safe_message="Document was not found.",
                    outcome=DocumentProcessingOutcome.NOT_FOUND,
                    status=None,
                    mark_failed=False,
                )
            if document.is_deleted:
                document.status = DocumentStatus.FAILED
                document.error_message = sanitize_processing_error(
                    DOCUMENT_DELETED_DURING_PROCESSING_MESSAGE
                )
                document.updated_at = datetime.now(UTC)
                await session.flush()
                await session.commit()
                return DocumentProcessingResult(
                    document_id=metadata.document_id,
                    outcome=DocumentProcessingOutcome.DELETED,
                    status=DocumentStatus.FAILED,
                    reason=DocumentProcessingOutcome.DELETED.value,
                )
            if document.status != DocumentStatus.PROCESSING:
                raise PermanentDocumentProcessingError(
                    code=DOCUMENT_NOT_PROCESSING_REASON,
                    safe_message=DOCUMENT_PROCESSING_FAILED_MESSAGE,
                    outcome=DocumentProcessingOutcome.NOT_ELIGIBLE,
                    status=document.status,
                    mark_failed=False,
                )

            try:
                await DocumentChunkRepository(session).replace_for_document(
                    document_id=metadata.document_id,
                    chunks=chunk_rows,
                )
                document.status = DocumentStatus.READY
                document.error_message = None
                document.updated_at = datetime.now(UTC)
                await session.flush()
                await session.commit()
            except OperationalError as exc:
                await session.rollback()
                raise TransientDocumentProcessingError() from exc
            except SQLAlchemyError as exc:
                await session.rollback()
                raise TransientDocumentProcessingError() from exc
            except Exception:
                await session.rollback()
                raise

        return DocumentProcessingResult(
            document_id=metadata.document_id,
            outcome=DocumentProcessingOutcome.READY,
            status=DocumentStatus.READY,
            page_count=page_count,
            chunk_count=chunking_result.chunk_count,
            total_tokens=chunking_result.total_tokens,
            embedding_dimensions=EMBEDDING_SCHEMA_DIMENSIONS,
        )


def create_document_processing_pipeline(
    settings: Settings | None = None,
    *,
    storage: FileStorage | None = None,
    extractor: object | None = None,
    chunker: TextChunker | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    session_provider: SessionProvider = worker_session,
) -> DocumentProcessingPipeline:
    resolved_settings = settings or get_settings()
    return DocumentProcessingPipeline(
        storage=storage or get_file_storage(),
        extractor=extractor or create_extraction_router(resolved_settings),
        chunker=chunker or create_document_chunker(resolved_settings),
        embedding_provider=embedding_provider or create_embedding_provider(resolved_settings),
        session_provider=session_provider,
        max_pdf_bytes=resolved_settings.max_upload_size_mb * 1024 * 1024,
        read_chunk_size_bytes=resolved_settings.upload_chunk_size_bytes,
    )
