from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.models import User, UserRole
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.hybrid_service import HybridRetrievalService
from app.retrieval.models import (
    KeywordRetrievalHit,
    KeywordRetrievalResult,
    RetrievalHit,
    RetrievalResult,
)


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def uid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "retrieval_top_k": 3,
        "retrieval_max_top_k": 10,
        "min_relevance_score": 0.25,
        "retrieval_max_query_characters": 40,
        "keyword_retrieval_top_k": 3,
        "keyword_retrieval_max_top_k": 10,
        "keyword_min_rank": 0.0,
        "hybrid_retrieval_top_k": 2,
        "hybrid_retrieval_max_top_k": 5,
        "hybrid_candidate_multiplier": 4,
        "hybrid_rrf_k": 60,
        "hybrid_semantic_weight": 1.0,
        "hybrid_keyword_weight": 1.0,
        "hybrid_semantic_min_relevance_score": 0.3,
        "reranker_enabled": False,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def make_user() -> User:
    return User(
        id=uid(1),
        email="hybrid-user@example.com",
        full_name="Hybrid User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )


def semantic_hit(value: int, *, text: str | None = None, title: str | None = None) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uid(value),
        document_id=uid(1000 + value),
        document_title=title or f"Document {value}",
        chunk_index=value,
        text=text or f"Hybrid text {value}",
        page_numbers=(value + 1,),
        start_page=value + 1,
        end_page=value + 1,
        token_count=3,
        relevance_score=0.8,
    )


def keyword_hit(
    value: int,
    *,
    text: str | None = None,
    title: str | None = None,
) -> KeywordRetrievalHit:
    return KeywordRetrievalHit(
        chunk_id=uid(value),
        document_id=uid(1000 + value),
        document_title=title or f"Document {value}",
        chunk_index=value,
        text=text or f"Hybrid text {value}",
        page_numbers=(value + 1,),
        start_page=value + 1,
        end_page=value + 1,
        token_count=3,
        keyword_rank=0.5,
    )


class FakeSemanticBranch:
    def __init__(self, hits: tuple[RetrievalHit, ...] = ()) -> None:
        self.hits = hits
        self.calls: list[dict[str, object]] = []

    async def retrieve(self, **kwargs: object) -> RetrievalResult:
        self.calls.append(kwargs)
        top_k = int(kwargs["top_k"])
        return RetrievalResult(
            hits=self.hits,
            hit_count=len(self.hits),
            requested_top_k=top_k,
            applied_min_relevance_score=float(kwargs["min_relevance_score"]),
            embedding_dimensions=384,
        )


class FakeKeywordBranch:
    def __init__(self, hits: tuple[KeywordRetrievalHit, ...] = ()) -> None:
        self.hits = hits
        self.calls: list[dict[str, object]] = []

    async def retrieve(self, **kwargs: object) -> KeywordRetrievalResult:
        self.calls.append(kwargs)
        top_k = int(kwargs["top_k"])
        return KeywordRetrievalResult(
            hits=self.hits,
            hit_count=len(self.hits),
            requested_top_k=top_k,
            applied_min_keyword_rank=float(kwargs["min_keyword_rank"]),
        )


class FailingBranch:
    async def retrieve(self, **kwargs: object) -> RetrievalResult:
        raise RuntimeError(str(kwargs["query"]))


def make_service(
    *,
    semantic_hits: tuple[RetrievalHit, ...] = (),
    keyword_hits: tuple[KeywordRetrievalHit, ...] = (),
    settings: Settings | None = None,
) -> tuple[HybridRetrievalService, FakeSemanticBranch, FakeKeywordBranch]:
    semantic = FakeSemanticBranch(semantic_hits)
    keyword = FakeKeywordBranch(keyword_hits)
    service = HybridRetrievalService(
        settings=settings or make_settings(),
        semantic_retrieval_service=semantic,
        keyword_retrieval_service=keyword,
    )
    return service, semantic, keyword


def test_hybrid_calls_semantic_once() -> None:
    async def scenario() -> None:
        service, semantic, _ = make_service(semantic_hits=(semantic_hit(1),))

        await service.retrieve(query="policy", current_user=make_user())

        assert len(semantic.calls) == 1

    run_async(scenario())


def test_hybrid_calls_keyword_once() -> None:
    async def scenario() -> None:
        service, _, keyword = make_service(keyword_hits=(keyword_hit(1),))

        await service.retrieve(query="policy", current_user=make_user())

        assert len(keyword.calls) == 1

    run_async(scenario())


def test_diacritic_insensitive_variant_is_lexical_only() -> None:
    async def scenario() -> None:
        service, semantic, keyword = make_service()

        await service.retrieve(query="Phụ cấp ăn trưa", current_user=make_user())

        assert len(semantic.calls) == 1
        assert len(keyword.calls) == 2
        assert keyword.calls[0]["query"] != keyword.calls[1]["query"]

    run_async(scenario())


def test_hybrid_uses_larger_candidate_limit() -> None:
    async def scenario() -> None:
        service, semantic, keyword = make_service()

        await service.retrieve(query="policy", current_user=make_user(), top_k=2)

        assert semantic.calls[0]["top_k"] == 8
        assert keyword.calls[0]["top_k"] == 8

    run_async(scenario())


def test_hybrid_applies_top_k_after_fusion() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(
            semantic_hits=(semantic_hit(1), semantic_hit(2), semantic_hit(3)),
            keyword_hits=(),
        )

        result = await service.retrieve(query="policy", current_user=make_user(), top_k=2)

        assert result.hit_count == 2
        assert result.fused_candidate_count == 3

    run_async(scenario())


def test_hybrid_merges_same_chunk() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(
            semantic_hits=(semantic_hit(1),),
            keyword_hits=(keyword_hit(1),),
        )

        result = await service.retrieve(query="policy", current_user=make_user())

        assert result.hit_count == 1
        assert result.hits[0].matched_by == ("semantic", "keyword")
        assert result.hits[0].semantic_rank == 1
        assert result.hits[0].keyword_rank == 1

    run_async(scenario())


def test_hybrid_retains_semantic_only_hit() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(semantic_hits=(semantic_hit(1),), keyword_hits=())

        result = await service.retrieve(query="policy", current_user=make_user())

        assert result.hits[0].matched_by == ("semantic",)

    run_async(scenario())


def test_hybrid_retains_keyword_only_hit() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(semantic_hits=(), keyword_hits=(keyword_hit(1),))

        result = await service.retrieve(query="policy", current_user=make_user())

        assert result.hits[0].matched_by == ("keyword",)

    run_async(scenario())


def test_hybrid_returns_empty_when_both_empty() -> None:
    async def scenario() -> None:
        service, _, _ = make_service()

        result = await service.retrieve(query="policy", current_user=make_user())

        assert result.hits == ()
        assert result.hit_count == 0

    run_async(scenario())


def test_hybrid_does_not_retain_query() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(semantic_hits=(semantic_hit(1),))

        result = await service.retrieve(query="Sensitive hybrid query", current_user=make_user())

        assert not hasattr(result, "query")
        assert "Sensitive hybrid query" not in repr(result)

    run_async(scenario())


def test_hybrid_does_not_return_embeddings() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(semantic_hits=(semantic_hit(1),))

        result = await service.retrieve(query="policy", current_user=make_user())

        assert not hasattr(result.hits[0], "embedding")
        assert "1.0, 0.0" not in repr(result)

    run_async(scenario())


def test_hybrid_is_deterministic() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(
            semantic_hits=(semantic_hit(2), semantic_hit(1)),
            keyword_hits=(keyword_hit(1),),
        )

        first = await service.retrieve(query="policy", current_user=make_user())
        second = await service.retrieve(query="policy", current_user=make_user())

        assert [hit.chunk_id for hit in first.hits] == [hit.chunk_id for hit in second.hits]

    run_async(scenario())


def test_hybrid_logs_do_not_include_query(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.hybrid_service")
        service, _, _ = make_service(semantic_hits=(semantic_hit(1),))

        await service.retrieve(query="Sensitive hybrid query", current_user=make_user())

        assert "Sensitive hybrid query" not in caplog.text

    run_async(scenario())


def test_hybrid_logs_do_not_include_chunk_text(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.hybrid_service")
        marker = "CONFIDENTIAL_HYBRID_LOG_MARKER"
        service, _, _ = make_service(semantic_hits=(semantic_hit(1, text=marker),))

        await service.retrieve(query="policy", current_user=make_user())

        assert marker not in caplog.text

    run_async(scenario())


def test_hybrid_logs_do_not_include_document_title(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.hybrid_service")
        marker = "CONFIDENTIAL_HYBRID_TITLE_MARKER"
        service, _, _ = make_service(semantic_hits=(semantic_hit(1, title=marker),))

        await service.retrieve(query="policy", current_user=make_user())

        assert marker not in caplog.text

    run_async(scenario())


def test_hybrid_errors_do_not_include_query(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        service = HybridRetrievalService(
            settings=make_settings(),
            semantic_retrieval_service=FailingBranch(),
            keyword_retrieval_service=FakeKeywordBranch(),
        )

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="Sensitive hybrid query", current_user=make_user())

        assert exc_info.value.code == RetrievalFailureCode.HYBRID_RETRIEVAL_FAILED
        assert "Sensitive hybrid query" not in str(exc_info.value)
        assert "Sensitive hybrid query" not in caplog.text

    run_async(scenario())
