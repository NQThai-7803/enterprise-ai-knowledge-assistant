from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import build_accessible_document_filter
from app.models import Document, DocumentChunk, DocumentStatus, User
from app.retrieval.authority import current_authority_order_expression


@dataclass(frozen=True, slots=True)
class RetrievalRow:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    text: str = field(repr=False)
    page_numbers: tuple[int, ...]
    start_page: int
    end_page: int
    token_count: int
    relevance_score: float


class SemanticRetrievalRepository:
    async def search_permitted_chunks(
        self,
        session: AsyncSession,
        *,
        query_vector: Sequence[float],
        current_user: User,
        top_k: int,
        min_relevance_score: float,
    ) -> tuple[RetrievalRow, ...]:
        return await search_permitted_chunks(
            session,
            query_vector=query_vector,
            current_user=current_user,
            top_k=top_k,
            min_relevance_score=min_relevance_score,
        )


async def search_permitted_chunks(
    session: AsyncSession,
    *,
    query_vector: Sequence[float],
    current_user: User,
    top_k: int,
    min_relevance_score: float,
) -> tuple[RetrievalRow, ...]:
    vector = list(query_vector)
    cosine_distance = DocumentChunk.embedding.cosine_distance(vector)
    relevance_score = (1.0 - cosine_distance).label("relevance_score")
    max_cosine_distance = 1.0 - min_relevance_score

    statement = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id.label("document_id"),
            Document.title.label("document_title"),
            DocumentChunk.chunk_index.label("chunk_index"),
            DocumentChunk.text.label("text"),
            DocumentChunk.page_numbers.label("page_numbers"),
            DocumentChunk.start_page.label("start_page"),
            DocumentChunk.end_page.label("end_page"),
            DocumentChunk.token_count.label("token_count"),
            relevance_score,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            Document.status == DocumentStatus.READY,
            build_accessible_document_filter(current_user),
            cosine_distance <= max_cosine_distance,
        )
        .order_by(
            cosine_distance.asc(),
            current_authority_order_expression().desc(),
            Document.id.asc(),
            DocumentChunk.chunk_index.asc(),
            DocumentChunk.id.asc(),
        )
        .limit(top_k)
    )
    rows = await session.execute(statement)
    return tuple(
        RetrievalRow(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            chunk_index=row.chunk_index,
            text=row.text,
            page_numbers=tuple(row.page_numbers),
            start_page=row.start_page,
            end_page=row.end_page,
            token_count=row.token_count,
            relevance_score=float(row.relevance_score),
        )
        for row in rows.all()
    )
