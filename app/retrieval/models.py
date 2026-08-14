from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real
from uuid import UUID

_SCORE_EPSILON = 1e-12
_SUPPORTED_CHANNELS = ("semantic", "keyword")


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    text: str = field(repr=False)
    page_numbers: tuple[int, ...]
    start_page: int
    end_page: int
    token_count: int
    relevance_score: float

    def __post_init__(self) -> None:
        _validate_common_hit_fields(self)
        object.__setattr__(self, "relevance_score", _coerce_relevance_score(self.relevance_score))


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    hits: tuple[RetrievalHit, ...]
    hit_count: int
    requested_top_k: int
    applied_min_relevance_score: float
    embedding_dimensions: int

    def __post_init__(self) -> None:
        hits = tuple(self.hits)
        object.__setattr__(self, "hits", hits)
        object.__setattr__(
            self,
            "applied_min_relevance_score",
            _coerce_relevance_score(self.applied_min_relevance_score),
        )
        if self.hit_count != len(hits):
            msg = "hit_count must match hits length."
            raise ValueError(msg)
        if self.requested_top_k <= 0:
            msg = "requested_top_k must be greater than zero."
            raise ValueError(msg)
        if self.hit_count > self.requested_top_k:
            msg = "hit_count must not exceed requested_top_k."
            raise ValueError(msg)
        if self.embedding_dimensions <= 0:
            msg = "embedding_dimensions must be greater than zero."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class KeywordRetrievalHit:
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

    def __post_init__(self) -> None:
        _validate_common_hit_fields(self)
        object.__setattr__(self, "keyword_rank", _coerce_non_negative_score(self.keyword_rank))


@dataclass(frozen=True, slots=True)
class KeywordRetrievalResult:
    hits: tuple[KeywordRetrievalHit, ...]
    hit_count: int
    requested_top_k: int
    applied_min_keyword_rank: float

    def __post_init__(self) -> None:
        hits = tuple(self.hits)
        object.__setattr__(self, "hits", hits)
        object.__setattr__(
            self,
            "applied_min_keyword_rank",
            _coerce_non_negative_score(self.applied_min_keyword_rank),
        )
        if self.hit_count != len(hits):
            msg = "hit_count must match hits length."
            raise ValueError(msg)
        if self.requested_top_k <= 0:
            msg = "requested_top_k must be greater than zero."
            raise ValueError(msg)
        if self.hit_count > self.requested_top_k:
            msg = "hit_count must not exceed requested_top_k."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class HybridRetrievalHit:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    text: str = field(repr=False)
    page_numbers: tuple[int, ...]
    start_page: int
    end_page: int
    token_count: int
    hybrid_score: float
    semantic_score: float | None
    semantic_rank: int | None
    keyword_score: float | None
    keyword_rank: int | None
    matched_by: tuple[str, ...]
    reranker_score: float | None = None

    def __post_init__(self) -> None:
        _validate_common_hit_fields(self)
        object.__setattr__(self, "hybrid_score", _coerce_non_negative_score(self.hybrid_score))
        if self.semantic_score is not None:
            object.__setattr__(
                self,
                "semantic_score",
                _coerce_relevance_score(self.semantic_score),
            )
        if self.keyword_score is not None:
            object.__setattr__(
                self,
                "keyword_score",
                _coerce_non_negative_score(self.keyword_score),
            )
        if self.semantic_rank is not None:
            object.__setattr__(self, "semantic_rank", _coerce_one_based_rank(self.semantic_rank))
        if self.keyword_rank is not None:
            object.__setattr__(self, "keyword_rank", _coerce_one_based_rank(self.keyword_rank))
        if self.reranker_score is not None:
            object.__setattr__(
                self,
                "reranker_score",
                _coerce_non_negative_score(self.reranker_score, field_name="reranker_score"),
            )
        object.__setattr__(self, "matched_by", _coerce_matched_by(self.matched_by))
        if ("semantic" in self.matched_by) != (self.semantic_rank is not None):
            msg = "semantic match state must be consistent."
            raise ValueError(msg)
        if ("keyword" in self.matched_by) != (self.keyword_rank is not None):
            msg = "keyword match state must be consistent."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class HybridRetrievalResult:
    hits: tuple[HybridRetrievalHit, ...]
    hit_count: int
    requested_top_k: int
    semantic_candidate_count: int
    keyword_candidate_count: int
    fused_candidate_count: int
    rrf_k: int
    semantic_weight: float
    keyword_weight: float

    def __post_init__(self) -> None:
        hits = tuple(self.hits)
        object.__setattr__(self, "hits", hits)
        if self.hit_count != len(hits):
            msg = "hit_count must match hits length."
            raise ValueError(msg)
        if self.requested_top_k <= 0:
            msg = "requested_top_k must be greater than zero."
            raise ValueError(msg)
        if self.hit_count > self.requested_top_k:
            msg = "hit_count must not exceed requested_top_k."
            raise ValueError(msg)
        if (
            min(
                self.semantic_candidate_count,
                self.keyword_candidate_count,
                self.fused_candidate_count,
            )
            < 0
        ):
            msg = "candidate counts must not be negative."
            raise ValueError(msg)
        if self.hit_count > self.fused_candidate_count:
            msg = "hit_count must not exceed fused_candidate_count."
            raise ValueError(msg)
        if self.rrf_k <= 0:
            msg = "rrf_k must be greater than zero."
            raise ValueError(msg)
        semantic_weight = _coerce_non_negative_score(self.semantic_weight)
        keyword_weight = _coerce_non_negative_score(self.keyword_weight)
        object.__setattr__(self, "semantic_weight", semantic_weight)
        object.__setattr__(self, "keyword_weight", keyword_weight)
        if semantic_weight == 0.0 and keyword_weight == 0.0:
            msg = "semantic_weight and keyword_weight must not both be zero."
            raise ValueError(msg)


def _validate_common_hit_fields(
    hit: RetrievalHit | KeywordRetrievalHit | HybridRetrievalHit,
) -> None:
    page_numbers = tuple(hit.page_numbers)
    object.__setattr__(hit, "page_numbers", page_numbers)
    if not hit.document_title.strip():
        msg = "document_title must not be empty."
        raise ValueError(msg)
    if hit.chunk_index < 0:
        msg = "chunk_index must not be negative."
        raise ValueError(msg)
    if not hit.text.strip():
        msg = "text must not be empty."
        raise ValueError(msg)
    if not page_numbers:
        msg = "page_numbers must not be empty."
        raise ValueError(msg)
    if any(page_number <= 0 for page_number in page_numbers):
        msg = "page_numbers must be positive."
        raise ValueError(msg)
    if hit.start_page <= 0:
        msg = "start_page must be positive."
        raise ValueError(msg)
    if hit.end_page < hit.start_page:
        msg = "end_page must be greater than or equal to start_page."
        raise ValueError(msg)
    if hit.token_count <= 0:
        msg = "token_count must be greater than zero."
        raise ValueError(msg)


def _coerce_relevance_score(value: float) -> float:
    score = _coerce_finite_real(value, field_name="relevance_score")
    if -_SCORE_EPSILON <= score < 0.0:
        return 0.0
    if 1.0 < score <= 1.0 + _SCORE_EPSILON:
        return 1.0
    if not 0.0 <= score <= 1.0:
        msg = "relevance_score must be between 0.0 and 1.0."
        raise ValueError(msg)
    return score


def _coerce_non_negative_score(value: float, *, field_name: str = "score") -> float:
    score = _coerce_finite_real(value, field_name=field_name)
    if score < 0.0:
        msg = f"{field_name} must not be negative."
        raise ValueError(msg)
    return score


def _coerce_finite_real(value: float, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        msg = f"{field_name} must be a finite number."
        raise ValueError(msg)
    score = float(value)
    if not isfinite(score):
        msg = f"{field_name} must be finite."
        raise ValueError(msg)
    return score


def _coerce_one_based_rank(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "rank must be an integer."
        raise ValueError(msg)
    if value < 1:
        msg = "rank must be one-based."
        raise ValueError(msg)
    return value


def _coerce_matched_by(value: Iterable[str]) -> tuple[str, ...]:
    channels = tuple(value)
    if not channels:
        msg = "matched_by must not be empty."
        raise ValueError(msg)
    if len(set(channels)) != len(channels):
        msg = "matched_by must not contain duplicates."
        raise ValueError(msg)
    if any(channel not in _SUPPORTED_CHANNELS for channel in channels):
        msg = "matched_by contains an unsupported channel."
        raise ValueError(msg)
    return tuple(channel for channel in _SUPPORTED_CHANNELS if channel in channels)
