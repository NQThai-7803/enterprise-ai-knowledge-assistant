from __future__ import annotations

from math import inf, nan

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_default_retrieval_top_k() -> None:
    assert make_settings().retrieval_top_k == 10


def test_default_min_relevance_score() -> None:
    assert make_settings().min_relevance_score == 0.50


def test_top_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(retrieval_top_k=0)


def test_default_top_k_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(retrieval_top_k=51, retrieval_max_top_k=50)


def test_min_relevance_score_must_be_in_range() -> None:
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=-0.01)
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=1.01)


def test_max_query_characters_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(retrieval_max_query_characters=0)


def test_nan_threshold_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=nan)


def test_infinite_threshold_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=inf)


def test_default_keyword_retrieval_settings() -> None:
    settings = make_settings()

    assert settings.keyword_retrieval_top_k == 20
    assert settings.keyword_retrieval_max_top_k == 100
    assert settings.keyword_min_rank == 0.0


def test_keyword_top_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(keyword_retrieval_top_k=0)


def test_default_keyword_top_k_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(keyword_retrieval_top_k=101, keyword_retrieval_max_top_k=100)


def test_keyword_min_rank_must_be_non_negative_and_finite() -> None:
    with pytest.raises(ValidationError):
        make_settings(keyword_min_rank=-0.01)
    with pytest.raises(ValidationError):
        make_settings(keyword_min_rank=nan)
    with pytest.raises(ValidationError):
        make_settings(keyword_min_rank=inf)


def test_default_hybrid_retrieval_settings() -> None:
    settings = make_settings()

    assert settings.hybrid_retrieval_top_k == 10
    assert settings.hybrid_retrieval_max_top_k == 50
    assert settings.hybrid_candidate_multiplier == 4
    assert settings.hybrid_rrf_k == 60
    assert settings.hybrid_semantic_weight == 1.0
    assert settings.hybrid_keyword_weight == 1.0
    assert settings.hybrid_semantic_min_relevance_score == 0.30


def test_hybrid_top_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_retrieval_top_k=0)


def test_default_hybrid_top_k_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_retrieval_top_k=51, hybrid_retrieval_max_top_k=50)


def test_hybrid_candidate_multiplier_must_be_at_least_one() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_candidate_multiplier=0)


def test_hybrid_rrf_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_rrf_k=0)


def test_hybrid_weights_must_not_both_be_zero() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_weight=0.0, hybrid_keyword_weight=0.0)


def test_hybrid_semantic_min_relevance_score_must_be_in_range() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_min_relevance_score=-0.01)
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_min_relevance_score=1.01)


def test_hybrid_float_settings_reject_nan_and_infinity() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_weight=nan)
    with pytest.raises(ValidationError):
        make_settings(hybrid_keyword_weight=inf)
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_min_relevance_score=nan)
