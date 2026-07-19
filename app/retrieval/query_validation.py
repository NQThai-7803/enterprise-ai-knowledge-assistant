from __future__ import annotations

from math import isfinite
from numbers import Real

from app.models import User, UserRole
from app.retrieval.errors import RetrievalError, RetrievalFailureCode


def validate_active_retrieval_user(current_user: User) -> None:
    if current_user.id is None or not current_user.is_active:
        raise RetrievalError(RetrievalFailureCode.RETRIEVAL_USER_INACTIVE)
    try:
        UserRole(current_user.role)
    except ValueError as exc:
        raise RetrievalError(RetrievalFailureCode.SEMANTIC_RETRIEVAL_FAILED) from exc


def validate_retrieval_query(query: str, *, max_characters: int) -> str:
    if not isinstance(query, str):
        raise RetrievalError(RetrievalFailureCode.EMPTY_RETRIEVAL_QUERY)
    normalized_query = query.strip()
    if not normalized_query:
        raise RetrievalError(RetrievalFailureCode.EMPTY_RETRIEVAL_QUERY)
    if len(normalized_query) > max_characters:
        raise RetrievalError(RetrievalFailureCode.RETRIEVAL_QUERY_TOO_LONG)
    return normalized_query


def validate_top_k(value: int | None, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise RetrievalError(RetrievalFailureCode.INVALID_RETRIEVAL_TOP_K)
    if value < 1 or value > maximum:
        raise RetrievalError(RetrievalFailureCode.INVALID_RETRIEVAL_TOP_K)
    return value


def validate_relevance_threshold(value: float | None, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RetrievalError(RetrievalFailureCode.INVALID_RELEVANCE_THRESHOLD)
    score = float(value)
    if not isfinite(score) or not 0.0 <= score <= 1.0:
        raise RetrievalError(RetrievalFailureCode.INVALID_RELEVANCE_THRESHOLD)
    return score


def validate_min_keyword_rank(value: float | None, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RetrievalError(RetrievalFailureCode.INVALID_KEYWORD_RANK)
    rank = float(value)
    if not isfinite(rank) or rank < 0.0:
        raise RetrievalError(RetrievalFailureCode.INVALID_KEYWORD_RANK)
    return rank
