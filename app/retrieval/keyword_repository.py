from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import ColumnElement, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import build_accessible_document_filter
from app.models import Document, DocumentChunk, DocumentStatus, User
from app.retrieval.authority import current_authority_order_expression, is_historical_query
from app.retrieval.question_analysis import fold_text

_TEXT_SEARCH_CONFIG = literal_column("'simple'::regconfig")
_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+\b")
_FALLBACK_TOKEN_PATTERN = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)
_FALLBACK_MAX_TERMS = 12
_FALLBACK_MAX_PHRASES = 8
_TITLE_RANK_WEIGHT = 0.2
_VIETNAMESE_DIACRITIC_SOURCE = "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
_VIETNAMESE_DIACRITIC_TARGET = "a" * 17 + "e" * 11 + "i" * 5 + "o" * 17 + "u" * 11 + "y" * 5 + "d"
_VIETNAMESE_ASCII_QUERY_CUES = frozenset(
    {
        "bao",
        "cap",
        "chinh",
        "dieu",
        "duoc",
        "gio",
        "han",
        "khong",
        "luong",
        "muc",
        "nam",
        "ngay",
        "nghi",
        "nhan",
        "phu",
        "sach",
        "thang",
        "tham",
        "trua",
        "tuan",
        "vien",
    }
)
_VIETNAMESE_QUERY_STOPWORDS = frozenset(
    {
        "ai",
        "and",
        "bao",
        "bao nhiêu",
        "bị",
        "bởi",
        "cái",
        "các",
        "cần",
        "cho",
        "có",
        "của",
        "đã",
        "đang",
        "đây",
        "để",
        "đến",
        "đó",
        "được",
        "gì",
        "hay",
        "khi",
        "không",
        "là",
        "mà",
        "mức",
        "một",
        "nào",
        "này",
        "nếu",
        "như",
        "những",
        "nhiêu",
        "ở",
        "not",
        "or",
        "ra",
        "sao",
        "sẽ",
        "thì",
        "theo",
        "trong",
        "và",
        "về",
        "với",
        "v.v",
        "vv",
    }
)


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

    folded_text_vector = None
    folded_query_text = fold_text(query)
    if _should_use_diacritic_insensitive_vector(query):
        folded_text = func.translate(
            func.lower(DocumentChunk.text),
            _VIETNAMESE_DIACRITIC_SOURCE,
            _VIETNAMESE_DIACRITIC_TARGET,
        )
        folded_text_vector = func.to_tsvector(_TEXT_SEARCH_CONFIG, folded_text)
        folded_query = func.websearch_to_tsquery(_TEXT_SEARCH_CONFIG, folded_query_text)
        match_expression = or_(
            match_expression,
            folded_text_vector.bool_op("@@")(folded_query),
        )
        keyword_rank = func.greatest(
            keyword_rank,
            func.ts_rank_cd(folded_text_vector, folded_query),
        )

    for identifier_query_text in _identifier_query_texts(query):
        identifier_query = func.websearch_to_tsquery(_TEXT_SEARCH_CONFIG, identifier_query_text)
        match_expression = or_(match_expression, text_vector.bool_op("@@")(identifier_query))
        keyword_rank = func.greatest(keyword_rank, func.ts_rank_cd(text_vector, identifier_query))

    primary_rows = await _execute_keyword_search(
        session,
        current_user=current_user,
        top_k=top_k,
        min_keyword_rank=min_keyword_rank,
        match_expression=match_expression,
        keyword_rank=keyword_rank,
        prefer_current_authority=not is_historical_query(query),
    )
    if len(primary_rows) >= top_k:
        return primary_rows

    fallback_query_text = _fallback_tsquery_text(query)
    if not fallback_query_text:
        return primary_rows

    fallback_query = func.to_tsquery(_TEXT_SEARCH_CONFIG, fallback_query_text)
    fallback_match_expression = text_vector.bool_op("@@")(fallback_query)
    title_vector = func.to_tsvector(_TEXT_SEARCH_CONFIG, Document.title)
    fallback_rank = func.ts_rank_cd(text_vector, fallback_query) + (
        func.ts_rank_cd(title_vector, fallback_query) * _TITLE_RANK_WEIGHT
    )
    if folded_text_vector is not None:
        folded_fallback_query_text = _fallback_tsquery_text(folded_query_text)
        folded_fallback_query = func.to_tsquery(
            _TEXT_SEARCH_CONFIG,
            folded_fallback_query_text,
        )
        folded_title = func.translate(
            func.lower(Document.title),
            _VIETNAMESE_DIACRITIC_SOURCE,
            _VIETNAMESE_DIACRITIC_TARGET,
        )
        folded_title_vector = func.to_tsvector(_TEXT_SEARCH_CONFIG, folded_title)
        fallback_match_expression = or_(
            fallback_match_expression,
            folded_text_vector.bool_op("@@")(folded_fallback_query),
        )
        fallback_rank = func.greatest(
            fallback_rank,
            func.ts_rank_cd(folded_text_vector, folded_fallback_query)
            + (func.ts_rank_cd(folded_title_vector, folded_fallback_query) * _TITLE_RANK_WEIGHT),
        )
    fallback_rows = await _execute_keyword_search(
        session,
        current_user=current_user,
        top_k=top_k,
        min_keyword_rank=min_keyword_rank,
        match_expression=fallback_match_expression,
        keyword_rank=fallback_rank,
        prefer_current_authority=not is_historical_query(query),
    )
    return _merge_keyword_rows(primary_rows, fallback_rows, top_k=top_k)


async def _execute_keyword_search(
    session: AsyncSession,
    *,
    current_user: User,
    top_k: int,
    min_keyword_rank: float,
    match_expression: ColumnElement[bool],
    keyword_rank: ColumnElement[float],
    prefer_current_authority: bool,
) -> tuple[KeywordRetrievalRow, ...]:
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
            *(
                ()
                if not prefer_current_authority
                else (current_authority_order_expression().desc(),)
            ),
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


def _fallback_tsquery_text(query: str) -> str:
    terms = _meaningful_fallback_terms(query)
    if not terms:
        return ""

    query_parts: list[str] = []
    query_parts.extend(_phrase_query_parts(terms))
    query_parts.extend(terms)
    return " | ".join(dict.fromkeys(query_parts))


def _should_use_diacritic_insensitive_vector(query: str) -> bool:
    folded_query = fold_text(query)
    if query.casefold() != folded_query:
        return False
    terms = {
        term.strip("_") for term in _FALLBACK_TOKEN_PATTERN.findall(folded_query) if term.strip("_")
    }
    return bool(terms.intersection(_VIETNAMESE_ASCII_QUERY_CUES))


def _meaningful_fallback_terms(query: str) -> tuple[str, ...]:
    normalized_query = query.casefold()
    terms: list[str] = []
    for raw_term in _FALLBACK_TOKEN_PATTERN.findall(normalized_query):
        term = raw_term.strip("_")
        if not _is_meaningful_fallback_term(term):
            continue
        terms.append(term)
        if len(terms) >= _FALLBACK_MAX_TERMS:
            break
    return tuple(dict.fromkeys(terms))


def _is_meaningful_fallback_term(term: str) -> bool:
    if not term or term in _VIETNAMESE_QUERY_STOPWORDS:
        return False
    if term.isdecimal():
        return True
    return len(term) >= 2


def _phrase_query_parts(terms: Iterable[str]) -> tuple[str, ...]:
    phrase_parts: list[str] = []
    previous_term: str | None = None
    for term in terms:
        if previous_term is not None:
            phrase_parts.append(f"{previous_term} <-> {term}")
            if len(phrase_parts) >= _FALLBACK_MAX_PHRASES:
                break
        previous_term = term
    return tuple(phrase_parts)


def _merge_keyword_rows(
    primary_rows: tuple[KeywordRetrievalRow, ...],
    fallback_rows: tuple[KeywordRetrievalRow, ...],
    *,
    top_k: int,
) -> tuple[KeywordRetrievalRow, ...]:
    merged_rows: list[KeywordRetrievalRow] = []
    seen_chunk_ids: set[UUID] = set()
    for row in (*primary_rows, *fallback_rows):
        if row.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(row.chunk_id)
        merged_rows.append(row)
        if len(merged_rows) >= top_k:
            break
    return tuple(merged_rows)
