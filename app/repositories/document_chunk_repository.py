from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.constants import EMBEDDING_SCHEMA_DIMENSIONS
from app.models import Document, DocumentChunk


@dataclass(frozen=True, slots=True)
class DocumentChunkCreate:
    chunk_index: int
    text: str
    token_count: int
    character_count: int
    page_numbers: tuple[int, ...]
    start_page: int
    end_page: int
    overlap_token_count: int
    content_sha256: str
    embedding: tuple[float, ...]
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int

    def __post_init__(self) -> None:
        page_numbers = tuple(self.page_numbers)
        embedding = tuple(_coerce_embedding_values(self.embedding))
        object.__setattr__(self, "page_numbers", page_numbers)
        object.__setattr__(self, "embedding", embedding)
        if self.chunk_index < 0:
            msg = "chunk_index must not be negative."
            raise ValueError(msg)
        if not self.text.strip():
            msg = "text must not be empty."
            raise ValueError(msg)
        if self.token_count <= 0:
            msg = "token_count must be greater than zero."
            raise ValueError(msg)
        if self.character_count <= 0:
            msg = "character_count must be greater than zero."
            raise ValueError(msg)
        if not page_numbers:
            msg = "page_numbers must not be empty."
            raise ValueError(msg)
        if any(page_number <= 0 for page_number in page_numbers):
            msg = "page_numbers must be positive."
            raise ValueError(msg)
        if self.start_page <= 0:
            msg = "start_page must be positive."
            raise ValueError(msg)
        if self.end_page < self.start_page:
            msg = "end_page must be greater than or equal to start_page."
            raise ValueError(msg)
        if self.overlap_token_count < 0:
            msg = "overlap_token_count must not be negative."
            raise ValueError(msg)
        if len(self.content_sha256) != 64:
            msg = "content_sha256 must be a SHA-256 hex digest."
            raise ValueError(msg)
        if self.embedding_dimensions != EMBEDDING_SCHEMA_DIMENSIONS:
            msg = "embedding_dimensions must match the vector schema."
            raise ValueError(msg)
        if len(embedding) != EMBEDDING_SCHEMA_DIMENSIONS:
            msg = "embedding length must match the vector schema."
            raise ValueError(msg)
        if not self.embedding_provider.strip():
            msg = "embedding_provider must not be empty."
            raise ValueError(msg)
        if not self.embedding_model.strip():
            msg = "embedding_model must not be empty."
            raise ValueError(msg)


class DocumentChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_document(self, document_id: UUID) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(await self.session.scalars(statement))

    async def count_by_document(self, document_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        return await self.session.scalar(statement) or 0

    async def delete_by_document(self, document_id: UUID) -> int:
        result = await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return result.rowcount or 0

    async def replace_for_document(
        self,
        *,
        document_id: UUID,
        chunks: Sequence[DocumentChunkCreate],
    ) -> list[DocumentChunk]:
        chunk_payload = tuple(chunks)
        _validate_replacement_payload(chunk_payload)

        document_exists = await self.session.scalar(
            select(Document.id).where(
                Document.id == document_id,
                Document.is_deleted.is_(False),
            )
        )
        if document_exists is None:
            msg = "Document is missing or deleted."
            raise ValueError(msg)

        await self.delete_by_document(document_id)
        rows = [
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                token_count=chunk.token_count,
                character_count=chunk.character_count,
                page_numbers=list(chunk.page_numbers),
                start_page=chunk.start_page,
                end_page=chunk.end_page,
                overlap_token_count=chunk.overlap_token_count,
                content_sha256=chunk.content_sha256,
                embedding=list(chunk.embedding),
                embedding_provider=chunk.embedding_provider,
                embedding_model=chunk.embedding_model,
                embedding_dimensions=chunk.embedding_dimensions,
            )
            for chunk in chunk_payload
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def find_nearest_for_verification(
        self,
        *,
        query_vector: Sequence[float],
        limit: int,
    ) -> list[tuple[DocumentChunk, float]]:
        if limit <= 0:
            msg = "limit must be greater than zero."
            raise ValueError(msg)
        vector = _coerce_embedding_values(query_vector)
        if len(vector) != EMBEDDING_SCHEMA_DIMENSIONS:
            msg = "query_vector length must match the vector schema."
            raise ValueError(msg)
        distance = DocumentChunk.embedding.cosine_distance(vector)
        statement = (
            select(DocumentChunk, distance.label("distance")).order_by(distance).limit(limit)
        )
        rows = await self.session.execute(statement)
        return [(chunk, float(distance_value)) for chunk, distance_value in rows.all()]


def _validate_replacement_payload(chunks: tuple[DocumentChunkCreate, ...]) -> None:
    if not chunks:
        msg = "chunks must not be empty."
        raise ValueError(msg)
    indexes = tuple(chunk.chunk_index for chunk in chunks)
    if indexes != tuple(range(len(chunks))):
        msg = "chunk indexes must start at zero and be contiguous."
        raise ValueError(msg)
    providers = {chunk.embedding_provider for chunk in chunks}
    models = {chunk.embedding_model for chunk in chunks}
    dimensions = {chunk.embedding_dimensions for chunk in chunks}
    if len(providers) != 1 or len(models) != 1 or dimensions != {EMBEDDING_SCHEMA_DIMENSIONS}:
        msg = "embedding metadata must be consistent."
        raise ValueError(msg)


def _coerce_embedding_values(values: Sequence[float]) -> list[float]:
    coerced: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            msg = "embedding values must be finite numbers."
            raise ValueError(msg)
        numeric_value = float(value)
        if not isfinite(numeric_value):
            msg = "embedding values must be finite numbers."
            raise ValueError(msg)
        coerced.append(numeric_value)
    return coerced
