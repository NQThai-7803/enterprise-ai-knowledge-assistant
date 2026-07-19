from __future__ import annotations

from collections.abc import Sequence
from math import sqrt

from sqlalchemy.ext.asyncio import AsyncSession

from app.document_processing.chunking.models import ChunkingResult, TextChunk
from app.embeddings.base import EmbeddingProvider
from app.embeddings.constants import (
    EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS,
    EMBEDDING_SCHEMA_DIMENSIONS,
)
from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.models import EmbeddingBatch, EmbeddingVector
from app.models import Document
from app.repositories.document_chunk_repository import DocumentChunkCreate, DocumentChunkRepository

_NORMALIZED_TOLERANCE = 1e-3


async def embed_and_store_chunks(
    session: AsyncSession,
    *,
    document: Document,
    chunking_result: ChunkingResult,
    embedding_provider: EmbeddingProvider,
) -> int:
    if document.id is None:
        msg = "Document must be persisted before chunk embeddings are stored."
        raise ValueError(msg)
    if document.is_deleted:
        msg = "Document is missing or deleted."
        raise ValueError(msg)
    chunks = tuple(chunking_result.chunks)
    if not chunks:
        raise EmbeddingError(EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT)
    if embedding_provider.dimensions != EMBEDDING_SCHEMA_DIMENSIONS:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH)

    batch = embedding_provider.embed_passages(tuple(chunk.text for chunk in chunks))
    validate_embedding_batch(
        batch, expected_count=len(chunks), model_name=embedding_provider.model_name
    )
    rows = build_document_chunk_rows(chunks, batch.vectors)

    repository = DocumentChunkRepository(session)
    try:
        await repository.replace_for_document(document_id=document.id, chunks=rows)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return len(rows)


def validate_embedding_batch(
    batch: EmbeddingBatch,
    *,
    expected_count: int,
    model_name: str,
) -> None:
    if batch.count != expected_count or len(batch.vectors) != expected_count:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_BATCH_MISMATCH)
    if batch.dimensions != EMBEDDING_SCHEMA_DIMENSIONS:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH)
    if batch.model_name != model_name:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED)
    for vector in batch.vectors:
        validate_embedding_vector(vector)


def validate_embedding_vector(vector: EmbeddingVector) -> None:
    if vector.dimensions != EMBEDDING_SCHEMA_DIMENSIONS:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH)
    if len(vector.values) != EMBEDDING_SCHEMA_DIMENSIONS:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH)
    if vector.normalized and not _is_normalized(vector.values):
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_INVALID_VECTOR)


def build_document_chunk_rows(
    chunks: Sequence[TextChunk],
    vectors: Sequence[EmbeddingVector],
) -> tuple[DocumentChunkCreate, ...]:
    rows: list[DocumentChunkCreate] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        rows.append(
            DocumentChunkCreate(
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                token_count=chunk.token_count,
                character_count=chunk.character_count,
                page_numbers=chunk.page_numbers,
                start_page=chunk.start_page,
                end_page=chunk.end_page,
                overlap_token_count=chunk.overlap_token_count,
                content_sha256=chunk.content_sha256,
                embedding=vector.values,
                embedding_provider=EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS,
                embedding_model=vector.model_name,
                embedding_dimensions=vector.dimensions,
            )
        )
    return tuple(rows)


def _is_normalized(values: tuple[float, ...]) -> bool:
    norm = sqrt(sum(value * value for value in values))
    return abs(norm - 1.0) <= _NORMALIZED_TOLERANCE
