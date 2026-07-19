from __future__ import annotations

from uuid import UUID

import pytest

from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.fusion import fuse_retrieval_hits
from app.retrieval.models import KeywordRetrievalHit, RetrievalHit


def uid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def semantic_hit(value: int, *, score: float = 0.8) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uid(value),
        document_id=uid(1000 + value),
        document_title=f"Document {value}",
        chunk_index=value,
        text=f"Semantic text {value}",
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=3,
        relevance_score=score,
    )


def keyword_hit(value: int, *, score: float = 0.4) -> KeywordRetrievalHit:
    return KeywordRetrievalHit(
        chunk_id=uid(value),
        document_id=uid(1000 + value),
        document_title=f"Document {value}",
        chunk_index=value,
        text=f"Semantic text {value}",
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=3,
        keyword_rank=score,
    )


def test_rrf_chunk_in_both_channels_scores_higher() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1), semantic_hit(2), semantic_hit(3)),
        keyword_hits=(keyword_hit(3),),
        top_k=3,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert result.hits[0].chunk_id == uid(3)
    assert result.hits[0].matched_by == ("semantic", "keyword")


def test_rrf_semantic_only_chunk_is_retained() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1),),
        keyword_hits=(),
        top_k=5,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert [hit.chunk_id for hit in result.hits] == [uid(1)]
    assert result.hits[0].matched_by == ("semantic",)


def test_rrf_keyword_only_chunk_is_retained() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(),
        keyword_hits=(keyword_hit(1),),
        top_k=5,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert [hit.chunk_id for hit in result.hits] == [uid(1)]
    assert result.hits[0].matched_by == ("keyword",)


def test_rrf_uses_one_based_ranks() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1),),
        keyword_hits=(),
        top_k=1,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert result.hits[0].semantic_rank == 1
    assert result.hits[0].hybrid_score == pytest.approx(1.0 / 61.0)


def test_rrf_respects_semantic_weight() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1),),
        keyword_hits=(keyword_hit(2),),
        top_k=2,
        rrf_k=60,
        semantic_weight=2.0,
        keyword_weight=1.0,
    )

    assert result.hits[0].chunk_id == uid(1)


def test_rrf_respects_keyword_weight() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1),),
        keyword_hits=(keyword_hit(2),),
        top_k=2,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=2.0,
    )

    assert result.hits[0].chunk_id == uid(2)


def test_rrf_rejects_zero_k() -> None:
    with pytest.raises(RetrievalError) as exc_info:
        fuse_retrieval_hits(
            semantic_hits=(),
            keyword_hits=(),
            top_k=1,
            rrf_k=0,
            semantic_weight=1.0,
            keyword_weight=1.0,
        )

    assert exc_info.value.code == RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION


def test_rrf_rejects_negative_weight() -> None:
    with pytest.raises(RetrievalError) as exc_info:
        fuse_retrieval_hits(
            semantic_hits=(),
            keyword_hits=(),
            top_k=1,
            rrf_k=60,
            semantic_weight=-0.1,
            keyword_weight=1.0,
        )

    assert exc_info.value.code == RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION


def test_rrf_rejects_both_weights_zero() -> None:
    with pytest.raises(RetrievalError) as exc_info:
        fuse_retrieval_hits(
            semantic_hits=(),
            keyword_hits=(),
            top_k=1,
            rrf_k=60,
            semantic_weight=0.0,
            keyword_weight=0.0,
        )

    assert exc_info.value.code == RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION


def test_rrf_deduplicates_chunk_ids() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1), semantic_hit(1)),
        keyword_hits=(),
        top_k=5,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert [hit.chunk_id for hit in result.hits] == [uid(1)]
    assert result.hits[0].semantic_rank == 1
    assert result.fused_candidate_count == 1


def test_rrf_produces_stable_order() -> None:
    first = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(3), semantic_hit(2), semantic_hit(1)),
        keyword_hits=(),
        top_k=3,
        rrf_k=60,
        semantic_weight=0.0,
        keyword_weight=1.0,
    )
    second = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(3), semantic_hit(2), semantic_hit(1)),
        keyword_hits=(),
        top_k=3,
        rrf_k=60,
        semantic_weight=0.0,
        keyword_weight=1.0,
    )

    assert [hit.chunk_id for hit in first.hits] == [hit.chunk_id for hit in second.hits]


def test_rrf_applies_final_top_k() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1), semantic_hit(2), semantic_hit(3)),
        keyword_hits=(),
        top_k=2,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert len(result.hits) == 2
    assert result.fused_candidate_count == 3


def test_rrf_does_not_use_raw_score_addition() -> None:
    result = fuse_retrieval_hits(
        semantic_hits=(semantic_hit(1, score=0.1),),
        keyword_hits=(keyword_hit(1, score=1000.0),),
        top_k=1,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )

    assert result.hits[0].hybrid_score == pytest.approx(2.0 / 61.0)
    assert result.hits[0].hybrid_score != pytest.approx(1000.1)
