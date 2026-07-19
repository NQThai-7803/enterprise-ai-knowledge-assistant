from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models import User
from app.retrieval.models import HybridRetrievalResult, KeywordRetrievalResult, RetrievalResult


@runtime_checkable
class RetrievalService(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
        min_relevance_score: float | None = None,
    ) -> RetrievalResult: ...


@runtime_checkable
class KeywordRetrievalService(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
        min_keyword_rank: float | None = None,
    ) -> KeywordRetrievalResult: ...


@runtime_checkable
class HybridRetrievalService(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        current_user: User,
        top_k: int | None = None,
    ) -> HybridRetrievalResult: ...
