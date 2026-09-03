from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from math import isfinite
from numbers import Real
from time import perf_counter
from typing import Protocol

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.constants import EMBEDDING_SCHEMA_DIMENSIONS
from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.models import EmbeddingVector
from app.models import User
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.models import RetrievalHit, RetrievalResult
from app.retrieval.query_validation import (
    validate_active_retrieval_user,
    validate_relevance_threshold,
    validate_retrieval_query,
    validate_top_k,
)
from app.retrieval.semantic_repository import RetrievalRow, SemanticRetrievalRepository

logger = logging.getLogger(__name__)

SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class SemanticSearchRepository(Protocol):
    async def search_permitted_chunks(
        self,
        session: AsyncSession,
        *,
        query_vector: Sequence[float],
        current_user: User,
        top_k: int,
        min_relevance_score: float,
    ) -> tuple[RetrievalRow, ...]: ...


class SemanticRetrievalService:
    def __init__(
        self,
        *,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
        session_provider: SessionProvider,
        repository: SemanticSearchRepository | None = None,
    ) -> None:
        self.settings = settings
        self.embedding_provider = embedding_provider
        self.session_provider = session_provider
        self.repository = repository or SemanticRetrievalRepository()

    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
        min_relevance_score: float | None = None,
    ) -> RetrievalResult:
        validate_active_retrieval_user(current_user)
        normalized_query = validate_retrieval_query(
            query,
            max_characters=self.settings.retrieval_max_query_characters,
        )
        resolved_top_k = validate_top_k(
            top_k,
            default=self.settings.retrieval_top_k,
            maximum=self.settings.retrieval_max_top_k,
        )
        resolved_threshold = validate_relevance_threshold(
            min_relevance_score,
            default=self.settings.min_relevance_score,
        )
        started = perf_counter()
        embed_started = perf_counter()
        query_vector = await self._embed_query(normalized_query)
        embed_ms = int((perf_counter() - embed_started) * 1000)

        try:
            async with self.session_provider() as session:
                vector_started = perf_counter()
                rows = await self.repository.search_permitted_chunks(
                    session,
                    query_vector=query_vector,
                    current_user=current_user,
                    top_k=resolved_top_k,
                    min_relevance_score=resolved_threshold,
                )
                vector_db_ms = int((perf_counter() - vector_started) * 1000)
        except RetrievalError:
            raise
        except Exception as exc:
            logger.warning(
                "Semantic retrieval query failed.",
                extra={"user_id": str(current_user.id), "error_type": exc.__class__.__name__},
            )
            raise RetrievalError(RetrievalFailureCode.SEMANTIC_RETRIEVAL_FAILED) from exc

        hits = tuple(_row_to_hit(row) for row in rows)
        result = RetrievalResult(
            hits=hits,
            hit_count=len(hits),
            requested_top_k=resolved_top_k,
            applied_min_relevance_score=resolved_threshold,
            embedding_dimensions=EMBEDDING_SCHEMA_DIMENSIONS,
        )
        logger.warning(
            "Semantic retrieval completed: %s",
            json.dumps(
                {
                    "user_id": str(current_user.id),
                    "hit_count": result.hit_count,
                    "requested_top_k": result.requested_top_k,
                    "applied_min_relevance_score": result.applied_min_relevance_score,
                    "embedding_dimensions": result.embedding_dimensions,
                    "embedding_ms": embed_ms,
                    "vector_db_ms": vector_db_ms,
                    "semantic_total_ms": int((perf_counter() - started) * 1000),
                },
                ensure_ascii=False,
            ),
        )
        return result

    async def _embed_query(self, query: str) -> tuple[float, ...]:
        try:
            vector = await anyio.to_thread.run_sync(self.embedding_provider.embed_query, query)
        except EmbeddingError as exc:
            if exc.code == EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH:
                raise RetrievalError(
                    RetrievalFailureCode.QUERY_EMBEDDING_DIMENSION_MISMATCH
                ) from exc
            raise RetrievalError(RetrievalFailureCode.QUERY_EMBEDDING_FAILED) from exc
        except Exception as exc:
            raise RetrievalError(RetrievalFailureCode.QUERY_EMBEDDING_FAILED) from exc
        return _coerce_query_embedding(vector)


def _coerce_query_embedding(vector: EmbeddingVector) -> tuple[float, ...]:
    if vector.dimensions != EMBEDDING_SCHEMA_DIMENSIONS:
        raise RetrievalError(RetrievalFailureCode.QUERY_EMBEDDING_DIMENSION_MISMATCH)
    if len(vector.values) != EMBEDDING_SCHEMA_DIMENSIONS:
        raise RetrievalError(RetrievalFailureCode.QUERY_EMBEDDING_DIMENSION_MISMATCH)
    values: list[float] = []
    for value in vector.values:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise RetrievalError(RetrievalFailureCode.QUERY_EMBEDDING_FAILED)
        numeric_value = float(value)
        if not isfinite(numeric_value):
            raise RetrievalError(RetrievalFailureCode.QUERY_EMBEDDING_FAILED)
        values.append(numeric_value)
    return tuple(values)


def _row_to_hit(row: RetrievalRow) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=row.chunk_id,
        document_id=row.document_id,
        document_title=row.document_title,
        chunk_index=row.chunk_index,
        text=row.text,
        page_numbers=row.page_numbers,
        start_page=row.start_page,
        end_page=row.end_page,
        token_count=row.token_count,
        relevance_score=row.relevance_score,
    )
