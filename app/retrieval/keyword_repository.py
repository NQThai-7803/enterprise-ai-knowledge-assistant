from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import build_accessible_document_filter
from app.models import Document, DocumentChunk, DocumentStatus, User

_TEXT_SEARCH_CONFIG = literal_column("'simple'::regconfig")
_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+\b")


@dataclass(frozen=True, slots=True)
class KeywordRetrievalRow:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    text: str = field(repr=False)
    page_numbers: tuple[int, ...]
    start_page: int
    end_page: int
    token_count: int
    keyword_rank: float


class KeywordRetrievalRepository:
    async def search_permitted_chunks_by_keyword(
        self,
        session: AsyncSession,
        *,
        query: str,
        current_user: User,
        top_k: int,
        min_keyword_rank: float,
    ) -> tuple[KeywordRetrievalRow, ...]:
        return await search_permitted_chunks_by_keyword(
            session,
            query=query,
            current_user=current_user,
            top_k=top_k,
            min_keyword_rank=min_keyword_rank,
        )


async def search_permitted_chunks_by_keyword(
    session: AsyncSession,
    *,
    query: str,
    current_user: User,
    top_k: int,
    min_keyword_rank: float,
) -> tuple[KeywordRetrievalRow, ...]:
    text_vector = func.to_tsvector(_TEXT_SEARCH_CONFIG, DocumentChunk.text)
    text_query = func.websearch_to_tsquery(_TEXT_SEARCH_CONFIG, query)
    match_expression = text_vector.bool_op("@@")(text_query)
    keyword_rank = func.ts_rank_cd(text_vector, text_query)

    for identifier_query_text in _identifier_query_texts(query):
        identifier_query = func.websearch_to_tsquery(_TEXT_SEARCH_CONFIG, identifier_query_text)
        match_expression = or_(match_expression, text_vector.bool_op("@@")(identifier_query))
        keyword_rank = func.greatest(keyword_rank, func.ts_rank_cd(text_vector, identifier_query))

    keyword_rank_label = keyword_rank.label("keyword_rank")

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
            keyword_rank_label,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            Document.status == DocumentStatus.READY,
            build_accessible_document_filter(current_user),
            match_expression,
            keyword_rank >= min_keyword_rank,
        )
        .order_by(
            keyword_rank.desc(),
            Document.id.asc(),
            DocumentChunk.chunk_index.asc(),
            DocumentChunk.id.asc(),
        )
        .limit(top_k)
    )
    rows = await session.execute(statement)
    return tuple(
        KeywordRetrievalRow(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            chunk_index=row.chunk_index,
            text=row.text,
            page_numbers=tuple(row.page_numbers),
            start_page=row.start_page,
            end_page=row.end_page,
            token_count=row.token_count,
            keyword_rank=float(row.keyword_rank),
        )
        for row in rows.all()
    )


def _identifier_query_texts(query: str) -> tuple[str, ...]:
    variants: list[str] = []
    for identifier in _IDENTIFIER_PATTERN.findall(query):
        variants.append(identifier)
        normalized_identifier = re.sub(r"[-/]+", " ", identifier)
        if normalized_identifier != identifier:
            variants.append(normalized_identifier)
    return tuple(dict.fromkeys(variants))
