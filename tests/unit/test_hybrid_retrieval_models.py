from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan
from uuid import UUID

import pytest

from app.retrieval.models import HybridRetrievalHit, HybridRetrievalResult

CONFIDENTIAL_HYBRID_MARKER = "CONFIDENTIAL_HYBRID_MARKER"


def make_hit(
    *,
    text: str = CONFIDENTIAL_HYBRID_MARKER,
    hybrid_score: float = 0.2,
    semantic_rank: int | None = 1,
    keyword_rank: int | None = 2,
    matched_by: tuple[str, ...] = ("semantic", "keyword"),
) -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=UUID("00000000-0000-0000-0000-000000000301"),
        document_id=UUID("00000000-0000-0000-0000-000000000401"),
        document_title="Hybrid Policy",
        chunk_index=1,
        text=text,
        page_numbers=(2, 5),
        start_page=2,
        end_page=5,
        token_count=9,
        hybrid_score=hybrid_score,
        semantic_score=0.7 if semantic_rank is not None else None,
        semantic_rank=semantic_rank,
        keyword_score=0.4 if keyword_rank is not None else None,
        keyword_rank=keyword_rank,
        matched_by=matched_by,
    )


def test_hybrid_hit_is_immutable() -> None:
    hit = make_hit()

    with pytest.raises(FrozenInstanceError):
        hit.hybrid_score = 1.0  # type: ignore[misc]


def test_hybrid_result_is_immutable() -> None:
    result = HybridRetrievalResult(
        hits=(make_hit(),),
        hit_count=1,
        requested_top_k=5,
        semantic_candidate_count=1,
        keyword_candidate_count=1,
        fused_candidate_count=1,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    with pytest.raises(FrozenInstanceError):
        result.hit_count = 0  # type: ignore[misc]


def test_hybrid_hit_repr_does_not_include_text() -> None:
    assert CONFIDENTIAL_HYBRID_MARKER not in repr(make_hit())


def test_hybrid_score_is_finite() -> None:
    with pytest.raises(ValueError):
        make_hit(hybrid_score=nan)
    with pytest.raises(ValueError):
        make_hit(hybrid_score=inf)


def test_matched_by_contains_supported_channels_only() -> None:
    assert make_hit(matched_by=("keyword", "semantic")).matched_by == ("semantic", "keyword")
    with pytest.raises(ValueError):
        make_hit(matched_by=("semantic", "reranker"))


def test_semantic_rank_is_one_based() -> None:
    with pytest.raises(ValueError):
        make_hit(semantic_rank=0)


def test_keyword_rank_is_one_based() -> None:
    with pytest.raises(ValueError):
        make_hit(keyword_rank=0)


def test_hybrid_result_counts_are_consistent() -> None:
    hit = make_hit()
    result = HybridRetrievalResult(
        hits=(hit,),
        hit_count=1,
        requested_top_k=1,
        semantic_candidate_count=1,
        keyword_candidate_count=1,
        fused_candidate_count=1,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert result.hit_count == len(result.hits)
    with pytest.raises(ValueError):
        HybridRetrievalResult(
            hits=(hit,),
            hit_count=0,
            requested_top_k=1,
            semantic_candidate_count=1,
            keyword_candidate_count=1,
            fused_candidate_count=1,
            rrf_k=60,
            semantic_weight=1.0,
            keyword_weight=1.0,
        )
