from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from time import perf_counter
from typing import Protocol

from app.core.config import Settings
from app.models import User
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.fusion import fuse_retrieval_hits
from app.retrieval.models import (
    HybridRetrievalResult,
    KeywordRetrievalResult,
    RetrievalResult,
)
from app.retrieval.query_validation import (
    validate_active_retrieval_user,
    validate_retrieval_query,
    validate_top_k,
)
from app.retrieval.question_analysis import retrieval_query_variants

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _MergedFusion:
    hits: tuple
    fused_candidate_count: int
    semantic_candidate_count: int
    keyword_candidate_count: int


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
            retrieval_started = perf_counter()
            variants = retrieval_query_variants(normalized_query)
            queries = tuple(
                dict.fromkeys(
                    form
                    for form in (
                        variants.original,
                        variants.normalized,
                        variants.diacritic_insensitive,
                    )
                    if form
                )
            )
            semantic_queries = tuple(dict.fromkeys((variants.original, variants.normalized)))
            semantic_results = {}
            for semantic_query in semantic_queries:
                semantic_results[semantic_query] = await self.semantic_retrieval_service.retrieve(
                    query=semantic_query,
                    current_user=current_user,
                    top_k=semantic_candidate_top_k,
                    min_relevance_score=self.settings.hybrid_semantic_min_relevance_score,
                )
            results = []
            for variant in queries:
                variant_started = perf_counter()
                semantic_result = semantic_results.get(variant)
                keyword_result = await self.keyword_retrieval_service.retrieve(
                    query=variant,
                    current_user=current_user,
                    top_k=keyword_candidate_top_k,
                    min_keyword_rank=self.settings.keyword_min_rank,
                )
                results.append(
                    (
                        fuse_retrieval_hits(
                            semantic_hits=semantic_result.hits if semantic_result else (),
                            keyword_hits=keyword_result.hits,
                            top_k=resolved_top_k,
                            rrf_k=self.settings.hybrid_rrf_k,
                            semantic_weight=self.settings.hybrid_semantic_weight,
                            keyword_weight=self.settings.hybrid_keyword_weight,
                        ),
                        semantic_result.hit_count if semantic_result else 0,
                        keyword_result.hit_count,
                    )
                )
                logger.warning(
                    "Hybrid retrieval variant timing: %s",
                    json.dumps(
                        {
                            "query_length": len(variant),
                            "semantic_hit_count": (
                                semantic_result.hit_count if semantic_result else 0
                            ),
                            "keyword_hit_count": keyword_result.hit_count,
                            "variant_ms": int((perf_counter() - variant_started) * 1000),
                        },
                        ensure_ascii=False,
                    ),
                )
            fused = _merge_variant_fusions(results, top_k=resolved_top_k)
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
            semantic_candidate_count=fused.semantic_candidate_count,
            keyword_candidate_count=fused.keyword_candidate_count,
            fused_candidate_count=fused.fused_candidate_count,
            rrf_k=self.settings.hybrid_rrf_k,
            semantic_weight=self.settings.hybrid_semantic_weight,
            keyword_weight=self.settings.hybrid_keyword_weight,
        )
        logger.warning(
            "Hybrid retrieval completed: %s",
            json.dumps(
                {
                    "user_id": str(current_user.id),
                    "hit_count": result.hit_count,
                    "requested_top_k": result.requested_top_k,
                    "semantic_candidate_count": result.semantic_candidate_count,
                    "keyword_candidate_count": result.keyword_candidate_count,
                    "fused_candidate_count": result.fused_candidate_count,
                    "rrf_k": result.rrf_k,
                    "semantic_weight": result.semantic_weight,
                    "keyword_weight": result.keyword_weight,
                    "variant_count": len(queries),
                    "retrieval_ms": int((perf_counter() - retrieval_started) * 1000),
                },
                ensure_ascii=False,
            ),
        )
        return result


def _merge_variant_fusions(results: list[tuple[object, int, int]], *, top_k: int) -> _MergedFusion:
    """Union variant results while preserving original-form precedence."""
    merged = {}
    fused_count = 0
    semantic_count = 0
    keyword_count = 0
    for variant_index, (
        fusion,
        semantic_variant_count,
        keyword_variant_count,
    ) in enumerate(results):
        fused_count += fusion.fused_candidate_count
        semantic_count += semantic_variant_count
        keyword_count += keyword_variant_count
        for hit in fusion.hits:
            score = float(hit.hybrid_score) + (1.0 / (1000 * (variant_index + 1)))
            existing = merged.get(hit.chunk_id)
            if existing is None or score > existing[0]:
                merged[hit.chunk_id] = (score, hit)
    hits = tuple(
        replace(hit, hybrid_score=score)
        for score, hit in sorted(
            merged.values(),
            key=lambda item: (-item[0], item[1].document_id.hex, item[1].chunk_index),
        )[:top_k]
    )
    # The concrete result is constructed by the caller; this small object keeps the
    # fusion helper independent from branch result accounting.
    return _MergedFusion(
        hits=hits,
        fused_candidate_count=fused_count,
        semantic_candidate_count=semantic_count,
        keyword_candidate_count=keyword_count,
    )
