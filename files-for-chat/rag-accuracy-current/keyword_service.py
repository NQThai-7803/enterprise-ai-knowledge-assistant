from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import User
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.keyword_repository import KeywordRetrievalRepository, KeywordRetrievalRow
from app.retrieval.models import KeywordRetrievalHit, KeywordRetrievalResult
from app.retrieval.query_validation import (
    validate_active_retrieval_user,
    validate_min_keyword_rank,
    validate_retrieval_query,
    validate_top_k,
)

logger = logging.getLogger(__name__)

SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class KeywordSearchRepository(Protocol):
    async def search_permitted_chunks_by_keyword(
        self,
        session: AsyncSession,
        *,
        query: str,
        current_user: User,
        top_k: int,
        min_keyword_rank: float,
    ) -> tuple[KeywordRetrievalRow, ...]: ...


class KeywordRetrievalService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_provider: SessionProvider,
        repository: KeywordSearchRepository | None = None,
    ) -> None:
        self.settings = settings
        self.session_provider = session_provider
        self.repository = repository or KeywordRetrievalRepository()

    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
        min_keyword_rank: float | None = None,
    ) -> KeywordRetrievalResult:
        validate_active_retrieval_user(current_user)
        normalized_query = validate_retrieval_query(
            query,
            max_characters=self.settings.retrieval_max_query_characters,
        )
        resolved_top_k = validate_top_k(
            top_k,
            default=self.settings.keyword_retrieval_top_k,
            maximum=self.settings.keyword_retrieval_max_top_k,
        )
        resolved_min_rank = validate_min_keyword_rank(
            min_keyword_rank,
            default=self.settings.keyword_min_rank,
        )

        try:
            async with self.session_provider() as session:
                rows = await self.repository.search_permitted_chunks_by_keyword(
                    session,
                    query=normalized_query,
                    current_user=current_user,
                    top_k=resolved_top_k,
                    min_keyword_rank=resolved_min_rank,
                )
        except RetrievalError:
            raise
        except Exception as exc:
            logger.warning(
                "Keyword retrieval query failed.",
                extra={"user_id": str(current_user.id), "error_type": exc.__class__.__name__},
            )
            raise RetrievalError(RetrievalFailureCode.KEYWORD_RETRIEVAL_FAILED) from exc

        hits = tuple(_row_to_hit(row) for row in rows)
        result = KeywordRetrievalResult(
            hits=hits,
            hit_count=len(hits),
            requested_top_k=resolved_top_k,
            applied_min_keyword_rank=resolved_min_rank,
        )
        logger.info(
            "Keyword retrieval completed.",
            extra={
                "user_id": str(current_user.id),
                "hit_count": result.hit_count,
                "requested_top_k": result.requested_top_k,
                "applied_min_keyword_rank": result.applied_min_keyword_rank,
            },
        )
        return result


def _row_to_hit(row: KeywordRetrievalRow) -> KeywordRetrievalHit:
    return KeywordRetrievalHit(
        chunk_id=row.chunk_id,
        document_id=row.document_id,
        document_title=row.document_title,
        chunk_index=row.chunk_index,
        text=row.text,
        page_numbers=row.page_numbers,
        start_page=row.start_page,
        end_page=row.end_page,
        token_count=row.token_count,
        keyword_rank=row.keyword_rank,
    )
