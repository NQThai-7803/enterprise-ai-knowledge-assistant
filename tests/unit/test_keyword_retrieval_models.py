from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan
from uuid import UUID

import pytest

from app.retrieval.models import KeywordRetrievalHit, KeywordRetrievalResult

CONFIDENTIAL_KEYWORD_MARKER = "CONFIDENTIAL_KEYWORD_MARKER"


def make_hit(*, text: str = CONFIDENTIAL_KEYWORD_MARKER, keyword_rank: float = 0.8):
    return KeywordRetrievalHit(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        document_id=UUID("00000000-0000-0000-0000-000000000201"),
        document_title="Keyword Policy",
        chunk_index=2,
        text=text,
        page_numbers=(3, 4),
        start_page=3,
        end_page=4,
        token_count=7,
        keyword_rank=keyword_rank,
    )


def test_keyword_hit_is_immutable() -> None:
    hit = make_hit()

    with pytest.raises(FrozenInstanceError):
        hit.keyword_rank = 1.0  # type: ignore[misc]


def test_keyword_result_is_immutable() -> None:
    result = KeywordRetrievalResult(
        hits=(make_hit(),),
        hit_count=1,
        requested_top_k=5,
        applied_min_keyword_rank=0.0,
    )

    with pytest.raises(FrozenInstanceError):
        result.hit_count = 0  # type: ignore[misc]


def test_keyword_hit_repr_does_not_include_text() -> None:
    assert CONFIDENTIAL_KEYWORD_MARKER not in repr(make_hit())


def test_keyword_rank_must_be_finite() -> None:
    with pytest.raises(ValueError):
        make_hit(keyword_rank=nan)
    with pytest.raises(ValueError):
        make_hit(keyword_rank=inf)


def test_keyword_rank_cannot_be_negative() -> None:
    with pytest.raises(ValueError):
        make_hit(keyword_rank=-0.01)


def test_keyword_hit_preserves_page_metadata() -> None:
    hit = make_hit()

    assert hit.page_numbers == (3, 4)
    assert hit.start_page == 3
    assert hit.end_page == 4


def test_keyword_result_repr_does_not_include_hit_text() -> None:
    result = KeywordRetrievalResult(
        hits=(make_hit(),),
        hit_count=1,
        requested_top_k=5,
        applied_min_keyword_rank=0.0,
    )

    assert CONFIDENTIAL_KEYWORD_MARKER not in repr(result)
