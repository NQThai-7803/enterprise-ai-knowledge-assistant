from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest

from app.core.config import Settings
from app.web_search.errors import WebSearchError, WebSearchFailureCode
from app.web_search.models import WebSearchResult, WebSearchResults
from app.web_search.service import WebSearchService


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


def settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "web_search_enabled": True,
        "web_search_mode": "hybrid",
        "web_search_provider": "mock",
        "web_search_max_results": 2,
        "web_search_max_content_length": 80,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


class FakeProvider:
    provider_name = "fake"
    display_name = "Fake"

    def __init__(self, result: WebSearchResults | Exception) -> None:
        self.result = result
        self.queries: list[str] = []

    async def search(self, *, query: str, max_results: int):
        self.queries.append(query)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def health_check(self, *, check_connectivity: bool = False):  # noqa: ANN001
        raise NotImplementedError

    async def aclose(self) -> None:
        return None


def result(*items: WebSearchResult) -> WebSearchResults:
    return WebSearchResults(
        query="raw",
        provider="fake",
        results=items,
        requested_max_results=max(len(items), 1),
    )


def web_result(
    url: str,
    *,
    title: str = "Title",
    content: str = "<p>Visible</p><script>hidden()</script>",
    rank: int = 1,
) -> WebSearchResult:
    return WebSearchResult(
        title=title,
        url=url,
        snippet=content,
        content=content,
        provider="fake",
        rank=rank,
        score=1.0 / rank,
    )


def test_service_rejects_search_when_disabled() -> None:
    provider = FakeProvider(result(web_result("https://example.com/a")))
    service = WebSearchService(
        settings=settings(web_search_enabled=False),
        provider_factory=lambda: provider,
    )

    async def scenario() -> None:
        with pytest.raises(WebSearchError) as exc_info:
            await service.search(query="question")
        assert exc_info.value.code == WebSearchFailureCode.WEB_SEARCH_DISABLED
        assert provider.queries == []

    run_async(scenario())


def test_service_normalizes_deduplicates_and_limits_results() -> None:
    provider = FakeProvider(
        result(
            web_result("https://example.com/a", title=" One ", rank=1),
            web_result("https://example.com/a", title="Duplicate", rank=2),
            web_result("https://example.com/b", title="Two", rank=3),
        )
    )
    service = WebSearchService(settings=settings(), provider_factory=lambda: provider)

    async def scenario() -> None:
        results = await service.search(query="  <b>latest policy</b>  ")

        assert provider.queries == ["latest policy"]
        assert [item.title for item in results.results] == ["One", "Two"]
        assert all("<script" not in item.content for item in results.results)
        assert [item.rank for item in results.results] == [1, 2]

    run_async(scenario())


def test_service_surfaces_provider_failure_without_query_leakage() -> None:
    provider = FakeProvider(WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_TIMEOUT))
    service = WebSearchService(settings=settings(), provider_factory=lambda: provider)

    async def scenario() -> None:
        with pytest.raises(WebSearchError) as exc_info:
            await service.search(query="CONFIDENTIAL_QUERY")
        assert exc_info.value.code == WebSearchFailureCode.WEB_SEARCH_PROVIDER_TIMEOUT

    run_async(scenario())
