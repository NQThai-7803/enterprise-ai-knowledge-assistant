from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import Settings
from app.models import User
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.fusion import fuse_retrieval_hits
from app.retrieval.models import HybridRetrievalResult, KeywordRetrievalResult, RetrievalResult
from app.retrieval.query_validation import (
    validate_active_retrieval_user,
    validate_retrieval_query,
    validate_top_k,
)

logger = logging.getLogger(__name__)


class SemanticRetrievalBranch(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
        min_relevance_score: float | None = None,
    ) -> RetrievalResult: ...


class KeywordRetrievalBranch(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
        min_keyword_rank: float | None = None,
    ) -> KeywordRetrievalResult: ...


class HybridRetrievalService:
    def __init__(
        self,
        *,
        settings: Settings,
        semantic_retrieval_service: SemanticRetrievalBranch,
        keyword_retrieval_service: KeywordRetrievalBranch,
    ) -> None:
        self.settings = settings
        self.semantic_retrieval_service = semantic_retrieval_service
        self.keyword_retrieval_service = keyword_retrieval_service

    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
    ) -> HybridRetrievalResult:
        validate_active_retrieval_user(current_user)
        normalized_query = validate_retrieval_query(
            query,
            max_characters=self.settings.retrieval_max_query_characters,
        )
        resolved_top_k = validate_top_k(
            top_k,
            default=self.settings.hybrid_retrieval_top_k,
            maximum=self.settings.hybrid_retrieval_max_top_k,
        )
        semantic_candidate_top_k = min(
            resolved_top_k * self.settings.hybrid_candidate_multiplier,
            self.settings.retrieval_max_top_k,
        )
        keyword_candidate_top_k = min(
            resolved_top_k * self.settings.hybrid_candidate_multiplier,
            self.settings.keyword_retrieval_max_top_k,
        )

        try:
            semantic_result = await self.semantic_retrieval_service.retrieve(
                query=normalized_query,
                current_user=current_user,
                top_k=semantic_candidate_top_k,
                min_relevance_score=self.settings.hybrid_semantic_min_relevance_score,
            )
            keyword_result = await self.keyword_retrieval_service.retrieve(
                query=normalized_query,
                current_user=current_user,
                top_k=keyword_candidate_top_k,
                min_keyword_rank=self.settings.keyword_min_rank,
            )
            fused = fuse_retrieval_hits(
                semantic_hits=semantic_result.hits,
                keyword_hits=keyword_result.hits,
                top_k=resolved_top_k,
                rrf_k=self.settings.hybrid_rrf_k,
                semantic_weight=self.settings.hybrid_semantic_weight,
                keyword_weight=self.settings.hybrid_keyword_weight,
            )
        except RetrievalError:
            raise
        except Exception as exc:
            logger.warning(
                "Hybrid retrieval failed.",
                extra={"user_id": str(current_user.id), "error_type": exc.__class__.__name__},
            )
            raise RetrievalError(RetrievalFailureCode.HYBRID_RETRIEVAL_FAILED) from exc

        result = HybridRetrievalResult(
            hits=fused.hits,
            hit_count=len(fused.hits),
            requested_top_k=resolved_top_k,
            semantic_candidate_count=semantic_result.hit_count,
            keyword_candidate_count=keyword_result.hit_count,
            fused_candidate_count=fused.fused_candidate_count,
            rrf_k=self.settings.hybrid_rrf_k,
            semantic_weight=self.settings.hybrid_semantic_weight,
            keyword_weight=self.settings.hybrid_keyword_weight,
        )
        logger.info(
            "Hybrid retrieval completed.",
            extra={
                "user_id": str(current_user.id),
                "hit_count": result.hit_count,
                "requested_top_k": result.requested_top_k,
                "semantic_candidate_count": result.semantic_candidate_count,
                "keyword_candidate_count": result.keyword_candidate_count,
                "fused_candidate_count": result.fused_candidate_count,
                "rrf_k": result.rrf_k,
                "semantic_weight": result.semantic_weight,
                "keyword_weight": result.keyword_weight,
            },
        )
        return result
