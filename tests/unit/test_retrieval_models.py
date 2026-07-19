from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan
from uuid import UUID

import pytest

from app.retrieval.models import RetrievalHit, RetrievalResult

CONFIDENTIAL_RETRIEVAL_MARKER = "CONFIDENTIAL_RETRIEVAL_MARKER"


def make_hit(*, text: str = CONFIDENTIAL_RETRIEVAL_MARKER, score: float = 0.75) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        document_id=UUID("00000000-0000-0000-0000-000000000201"),
        document_title="Internal Policy",
        chunk_index=0,
        text=text,
        page_numbers=(2, 3),
        start_page=2,
        end_page=3,
        token_count=42,
        relevance_score=score,
    )


def make_result(*, hits: tuple[RetrievalHit, ...] | None = None) -> RetrievalResult:
    resolved_hits = hits if hits is not None else (make_hit(),)
    return RetrievalResult(
        hits=resolved_hits,
        hit_count=len(resolved_hits),
        requested_top_k=10,
        applied_min_relevance_score=0.5,
        embedding_dimensions=384,
    )


def test_retrieval_hit_is_immutable() -> None:
    hit = make_hit()

    with pytest.raises(FrozenInstanceError):
        hit.chunk_index = 1  # type: ignore[misc]


def test_retrieval_result_is_immutable() -> None:
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.hit_count = 2  # type: ignore[misc]


def test_retrieval_hit_repr_does_not_include_text() -> None:
    assert CONFIDENTIAL_RETRIEVAL_MARKER not in repr(make_hit())


def test_retrieval_result_repr_does_not_include_hit_text() -> None:
    assert CONFIDENTIAL_RETRIEVAL_MARKER not in repr(make_result())


def test_relevance_score_is_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        make_hit(score=nan)
    with pytest.raises(ValueError, match="finite"):
        make_hit(score=inf)


def test_relevance_score_range_is_valid() -> None:
    assert make_hit(score=0.0).relevance_score == 0.0
    assert make_hit(score=1.0).relevance_score == 1.0
    with pytest.raises(ValueError, match="between"):
        make_hit(score=-0.01)
    with pytest.raises(ValueError, match="between"):
        make_hit(score=1.01)


def test_hit_count_matches_hits() -> None:
    with pytest.raises(ValueError, match="hit_count"):
        RetrievalResult(
            hits=(make_hit(),),
            hit_count=0,
            requested_top_k=10,
            applied_min_relevance_score=0.5,
            embedding_dimensions=384,
        )


def test_page_numbers_are_preserved() -> None:
    assert make_hit().page_numbers == (2, 3)
