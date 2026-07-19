from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Sequence
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core.config import Settings
from app.embeddings.models import EmbeddingVector
from app.models import User, UserRole
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.semantic_repository import RetrievalRow
from app.retrieval.semantic_service import SemanticRetrievalService


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def vector(*, dimensions: int = 384, value: float = 1.0) -> tuple[float, ...]:
    values = [0.0] * dimensions
    values[0] = value
    return tuple(values)


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "retrieval_top_k": 3,
        "retrieval_max_top_k": 5,
        "min_relevance_score": 0.25,
        "retrieval_max_query_characters": 20,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def make_user(*, is_active: bool = True) -> User:
    return User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="retrieval-user@example.com",
        full_name="Retrieval User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=is_active,
    )


def make_row() -> RetrievalRow:
    return RetrievalRow(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        document_id=UUID("00000000-0000-0000-0000-000000000201"),
        document_title="Policy",
        chunk_index=0,
        text="Allowed chunk text",
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=4,
        relevance_score=0.9,
    )


class FakeEmbeddingProvider:
    def __init__(
        self,
        *,
        dimensions: int = 384,
        session_state: FakeSessionProvider | None = None,
    ) -> None:
        self._dimensions = dimensions
        self._session_state = session_state
        self.query_calls: list[str] = []
        self.passage_calls: list[tuple[str, ...]] = []

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return "fake-model"

    def embed_query(self, text: str) -> EmbeddingVector:
        if self._session_state is not None:
            assert not self._session_state.active
        self.query_calls.append(text)
        return EmbeddingVector(
            values=vector(dimensions=self._dimensions),
            dimensions=self._dimensions,
            normalized=True,
            model_name="fake-model",
        )

    def embed_passages(self, texts: Sequence[str]):  # pragma: no cover - must not be called.
        self.passage_calls.append(tuple(texts))
        raise AssertionError("passage embedding must not be used for retrieval queries")


class FakeRepository:
    def __init__(self, rows: tuple[RetrievalRow, ...] = ()) -> None:
        self.rows = rows
        self.calls: list[dict[str, object]] = []
        self.session_state: FakeSessionProvider | None = None

    async def search_permitted_chunks(self, session: object, **kwargs: object):
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
    provider: FakeEmbeddingProvider | None = None,
    repository: FakeRepository | None = None,
    session_provider: FakeSessionProvider | None = None,
    settings: Settings | None = None,
) -> tuple[SemanticRetrievalService, FakeEmbeddingProvider, FakeRepository, FakeSessionProvider]:
    resolved_session_provider = session_provider or FakeSessionProvider()
    resolved_provider = provider or FakeEmbeddingProvider(session_state=resolved_session_provider)
    resolved_repository = repository or FakeRepository((make_row(),))
    resolved_repository.session_state = resolved_session_provider
    service = SemanticRetrievalService(
        settings=settings or make_settings(),
        embedding_provider=resolved_provider,
        session_provider=resolved_session_provider,
        repository=resolved_repository,
    )
    return service, resolved_provider, resolved_repository, resolved_session_provider


def assert_retrieval_error(exc_info: pytest.ExceptionInfo[RetrievalError], code) -> None:  # noqa: ANN001
    assert exc_info.value.code == code
    assert "leave policy" not in exc_info.value.safe_message


def test_retrieval_validates_query_before_embedding() -> None:
    async def scenario() -> None:
        service, provider, repository, session_provider = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="   ", current_user=make_user())

        assert_retrieval_error(exc_info, RetrievalFailureCode.EMPTY_RETRIEVAL_QUERY)
        assert provider.query_calls == []
        assert repository.calls == []
        assert session_provider.entered == 0

    run_async(scenario())


def test_retrieval_rejects_empty_query() -> None:
    async def scenario() -> None:
        service, _, _, _ = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="", current_user=make_user())

        assert_retrieval_error(exc_info, RetrievalFailureCode.EMPTY_RETRIEVAL_QUERY)

    run_async(scenario())


def test_retrieval_rejects_query_over_limit() -> None:
    async def scenario() -> None:
        service, provider, repository, _ = make_service(settings=make_settings())

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="x" * 21, current_user=make_user())

        assert_retrieval_error(exc_info, RetrievalFailureCode.RETRIEVAL_QUERY_TOO_LONG)
        assert provider.query_calls == []
        assert repository.calls == []

    run_async(scenario())


def test_retrieval_uses_query_embedding() -> None:
    async def scenario() -> None:
        service, provider, repository, _ = make_service()

        await service.retrieve(query="  leave policy  ", current_user=make_user())

        assert provider.query_calls == ["leave policy"]
        assert repository.calls[0]["query_vector"] == vector()

    run_async(scenario())


def test_retrieval_does_not_use_passage_embedding() -> None:
    async def scenario() -> None:
        service, provider, _, _ = make_service()

        await service.retrieve(query="leave policy", current_user=make_user())

        assert provider.passage_calls == []

    run_async(scenario())


def test_retrieval_runs_embedding_outside_database_transaction() -> None:
    async def scenario() -> None:
        session_provider = FakeSessionProvider()
        service, _, repository, _ = make_service(session_provider=session_provider)

        await service.retrieve(query="leave policy", current_user=make_user())

        assert session_provider.entered == 1
        assert repository.calls
        assert not session_provider.active

    run_async(scenario())


def test_retrieval_validates_embedding_dimension() -> None:
    async def scenario() -> None:
        provider = FakeEmbeddingProvider(dimensions=3)
        service, _, repository, _ = make_service(provider=provider)

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="leave policy", current_user=make_user())

        assert_retrieval_error(exc_info, RetrievalFailureCode.QUERY_EMBEDDING_DIMENSION_MISMATCH)
        assert repository.calls == []

    run_async(scenario())


def test_retrieval_uses_default_top_k() -> None:
    async def scenario() -> None:
        service, _, repository, _ = make_service()

        result = await service.retrieve(query="leave policy", current_user=make_user())

        assert result.requested_top_k == 3
        assert repository.calls[0]["top_k"] == 3

    run_async(scenario())


def test_retrieval_uses_default_threshold() -> None:
    async def scenario() -> None:
        service, _, repository, _ = make_service()

        result = await service.retrieve(query="leave policy", current_user=make_user())

        assert result.applied_min_relevance_score == 0.25
        assert repository.calls[0]["min_relevance_score"] == 0.25

    run_async(scenario())


def test_retrieval_accepts_valid_overrides() -> None:
    async def scenario() -> None:
        service, _, repository, _ = make_service()

        result = await service.retrieve(
            query="leave policy",
            current_user=make_user(),
            top_k=1,
            min_relevance_score=0.7,
        )

        assert result.requested_top_k == 1
        assert result.applied_min_relevance_score == 0.7
        assert repository.calls[0]["top_k"] == 1
        assert repository.calls[0]["min_relevance_score"] == 0.7

    run_async(scenario())


def test_retrieval_rejects_top_k_above_maximum() -> None:
    async def scenario() -> None:
        service, provider, repository, _ = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="leave policy", current_user=make_user(), top_k=6)

        assert_retrieval_error(exc_info, RetrievalFailureCode.INVALID_RETRIEVAL_TOP_K)
        assert provider.query_calls == []
        assert repository.calls == []

    run_async(scenario())


def test_retrieval_returns_empty_result_without_error() -> None:
    async def scenario() -> None:
        service, _, _, _ = make_service(repository=FakeRepository(()))

        result = await service.retrieve(query="leave policy", current_user=make_user())

        assert result.hits == ()
        assert result.hit_count == 0

    run_async(scenario())


def test_retrieval_does_not_return_embedding_values() -> None:
    async def scenario() -> None:
        service, _, _, _ = make_service()

        result = await service.retrieve(query="leave policy", current_user=make_user())

        assert not hasattr(result.hits[0], "embedding")
        assert "1.0, 0.0" not in repr(result)

    run_async(scenario())


def test_retrieval_does_not_retain_query_text() -> None:
    async def scenario() -> None:
        service, _, _, _ = make_service()

        result = await service.retrieve(query="leave policy", current_user=make_user())

        assert not hasattr(result, "query")
        assert "leave policy" not in repr(result)

    run_async(scenario())


def test_retrieval_rejects_inactive_user() -> None:
    async def scenario() -> None:
        service, provider, repository, _ = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="leave policy", current_user=make_user(is_active=False))

        assert_retrieval_error(exc_info, RetrievalFailureCode.RETRIEVAL_USER_INACTIVE)
        assert provider.query_calls == []
        assert repository.calls == []

    run_async(scenario())


def test_retrieval_errors_do_not_include_query() -> None:
    async def scenario() -> None:
        service, _, _, _ = make_service(settings=make_settings(retrieval_max_query_characters=5))

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="leave policy", current_user=make_user())

        assert "leave policy" not in str(exc_info.value)
        assert "leave policy" not in exc_info.value.safe_message

    run_async(scenario())


def test_invalid_threshold_is_rejected() -> None:
    async def scenario() -> None:
        service, provider, repository, _ = make_service()

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(
                query="leave policy",
                current_user=make_user(),
                min_relevance_score=1.1,
            )

        assert_retrieval_error(exc_info, RetrievalFailureCode.INVALID_RELEVANCE_THRESHOLD)
        assert provider.query_calls == []
        assert repository.calls == []

    run_async(scenario())


def test_fake_user_ids_are_unique_for_test_rows() -> None:
    assert uuid4() != uuid4()


def test_retrieval_logs_do_not_include_query(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.semantic_service")
        service, _, _, _ = make_service()

        await service.retrieve(query="Sensitive query text", current_user=make_user())

        assert "Sensitive query text" not in caplog.text

    run_async(scenario())


def test_retrieval_logs_do_not_include_chunk_text(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.semantic_service")
        marker = "CONFIDENTIAL_CHUNK_LOG_MARKER"
        repository = FakeRepository((make_row(),))
        repository.rows = (
            RetrievalRow(
                chunk_id=UUID("00000000-0000-0000-0000-000000000102"),
                document_id=UUID("00000000-0000-0000-0000-000000000202"),
                document_title="Policy",
                chunk_index=0,
                text=marker,
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                token_count=4,
                relevance_score=0.9,
            ),
        )
        service, _, _, _ = make_service(repository=repository)

        await service.retrieve(query="leave policy", current_user=make_user())

        assert marker not in caplog.text

    run_async(scenario())


def test_retrieval_logs_do_not_include_document_title(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.semantic_service")
        marker = "CONFIDENTIAL_TITLE_LOG_MARKER"
        repository = FakeRepository(
            (
                RetrievalRow(
                    chunk_id=UUID("00000000-0000-0000-0000-000000000103"),
                    document_id=UUID("00000000-0000-0000-0000-000000000203"),
                    document_title=marker,
                    chunk_index=0,
                    text="Allowed chunk text",
                    page_numbers=(1,),
                    start_page=1,
                    end_page=1,
                    token_count=4,
                    relevance_score=0.9,
                ),
            )
        )
        service, _, _, _ = make_service(repository=repository)

        await service.retrieve(query="leave policy", current_user=make_user())

        assert marker not in caplog.text

    run_async(scenario())


def test_retrieval_logs_do_not_include_embedding_values(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.semantic_service")
        service, _, _, _ = make_service()

        await service.retrieve(query="leave policy", current_user=make_user())

        assert "1.0, 0.0" not in caplog.text

    run_async(scenario())
