from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.models import User, UserRole
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.keyword_repository import KeywordRetrievalRow, _fallback_tsquery_text
from app.retrieval.keyword_service import KeywordRetrievalService


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "keyword_retrieval_top_k": 3,
        "keyword_retrieval_max_top_k": 5,
        "keyword_min_rank": 0.2,
        "retrieval_max_query_characters": 20,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def make_user(*, is_active: bool = True) -> User:
    return User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="keyword-user@example.com",
        full_name="Keyword User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=is_active,
    )


def make_row() -> KeywordRetrievalRow:
    return KeywordRetrievalRow(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        document_id=UUID("00000000-0000-0000-0000-000000000201"),
        document_title="Keyword Policy",
        chunk_index=0,
        text="Allowed keyword chunk text",
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=4,
        keyword_rank=0.9,
    )


class FakeRepository:
    def __init__(self, rows: tuple[KeywordRetrievalRow, ...] = ()) -> None:
        self.rows = rows
        self.calls: list[dict[str, object]] = []
        self.session_state: FakeSessionProvider | None = None

    async def search_permitted_chunks_by_keyword(self, session: object, **kwargs: object):
        if self.session_state is not None:
            assert self.session_state.active
        self.calls.append({"session": session, **kwargs})
        return self.rows


class FakeSessionContext:
    def __init__(self, provider: FakeSessionProvider) -> None:
        self.provider = provider

    async def __aenter__(self) -> object:
        self.provider.active = True
        self.provider.entered += 1
        return object()

    async def __aexit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        self.provider.active = False


class FakeSessionProvider:
    def __init__(self) -> None:
        self.active = False
        self.entered = 0

    def __call__(self) -> FakeSessionContext:
        return FakeSessionContext(self)


def make_service(
    *,
    repository: FakeRepository | None = None,
    session_provider: FakeSessionProvider | None = None,
    settings: Settings | None = None,
) -> tuple[KeywordRetrievalService, FakeRepository, FakeSessionProvider]:
    resolved_session_provider = session_provider or FakeSessionProvider()
    resolved_repository = repository or FakeRepository((make_row(),))
    resolved_repository.session_state = resolved_session_provider
    service = KeywordRetrievalService(
        settings=settings or make_settings(),
        session_provider=resolved_session_provider,
        repository=resolved_repository,
    )
    return service, resolved_repository, resolved_session_provider


def test_keyword_retrieval_validates_query() -> None:
    async def scenario() -> None:
        service, repository, _ = make_service()

        await service.retrieve(query="  HD-2026-001  ", current_user=make_user())

        assert repository.calls[0]["query"] == "HD-2026-001"

    run_async(scenario())


def test_keyword_retrieval_rejects_empty_query() -> None:
    async def scenario() -> None:
        service, repository, session_provider = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="   ", current_user=make_user())

        assert exc_info.value.code == RetrievalFailureCode.EMPTY_RETRIEVAL_QUERY
        assert repository.calls == []
        assert session_provider.entered == 0

    run_async(scenario())


def test_keyword_retrieval_rejects_query_over_limit() -> None:
    async def scenario() -> None:
        service, repository, _ = make_service(settings=make_settings())

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="x" * 21, current_user=make_user())

        assert exc_info.value.code == RetrievalFailureCode.RETRIEVAL_QUERY_TOO_LONG
        assert repository.calls == []

    run_async(scenario())


def test_keyword_retrieval_uses_default_top_k() -> None:
    async def scenario() -> None:
        service, repository, _ = make_service()

        result = await service.retrieve(query="policy", current_user=make_user())

        assert result.requested_top_k == 3
        assert repository.calls[0]["top_k"] == 3

    run_async(scenario())


def test_keyword_retrieval_rejects_top_k_over_maximum() -> None:
    async def scenario() -> None:
        service, repository, _ = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="policy", current_user=make_user(), top_k=6)

        assert exc_info.value.code == RetrievalFailureCode.INVALID_RETRIEVAL_TOP_K
        assert repository.calls == []

    run_async(scenario())


def test_keyword_retrieval_validates_min_rank() -> None:
    async def scenario() -> None:
        service, repository, _ = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="policy", current_user=make_user(), min_keyword_rank=-0.1)

        assert exc_info.value.code == RetrievalFailureCode.INVALID_KEYWORD_RANK
        assert repository.calls == []

    run_async(scenario())


def test_keyword_retrieval_returns_empty_result() -> None:
    async def scenario() -> None:
        service, _, _ = make_service(repository=FakeRepository(()))

        result = await service.retrieve(query="policy", current_user=make_user())

        assert result.hits == ()
        assert result.hit_count == 0

    run_async(scenario())


def test_keyword_retrieval_does_not_create_embedding() -> None:
    assert not hasattr(KeywordRetrievalService, "embedding_provider")


def test_keyword_retrieval_does_not_log_query(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.keyword_service")
        service, _, _ = make_service()

        await service.retrieve(query="Sensitive key query", current_user=make_user())

        assert "Sensitive key query" not in caplog.text

    run_async(scenario())


def test_keyword_logs_do_not_include_chunk_text(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.keyword_service")
        marker = "CONFIDENTIAL_KEYWORD_LOG_MARKER"
        row = KeywordRetrievalRow(
            chunk_id=UUID("00000000-0000-0000-0000-000000000102"),
            document_id=UUID("00000000-0000-0000-0000-000000000202"),
            document_title="Keyword Policy",
            chunk_index=0,
            text=marker,
            page_numbers=(1,),
            start_page=1,
            end_page=1,
            token_count=4,
            keyword_rank=0.9,
        )
        service, _, _ = make_service(repository=FakeRepository((row,)))

        await service.retrieve(query="policy", current_user=make_user())

        assert marker not in caplog.text

    run_async(scenario())


def test_fallback_query_keeps_meaningful_vietnamese_terms() -> None:
    query_text = _fallback_tsquery_text(
        "Trong công việc điều kiện bình thường, mức nghỉ hằng năm hưởng nguyên lương "
        "là bao nhiêu ngày?"
    )

    assert "công <-> việc" in query_text
    assert "điều <-> kiện" in query_text
    assert "bình <-> thường" in query_text
    assert "hằng" in query_text
    assert "nguyên" in query_text
    assert "lương" in query_text
    assert "trong" not in query_text
    assert "bao" not in query_text
    assert "nhiêu" not in query_text


def test_fallback_query_sanitizes_user_tsquery_syntax() -> None:
    query_text = _fallback_tsquery_text("' OR 1=1 -- nghỉ (phép) / ../../ nguyên lương")

    assert "'" not in query_text
    assert ";" not in query_text
    assert "&" not in query_text
    assert "nghỉ" in query_text
    assert "phép" in query_text
    assert "nguyên" in query_text
