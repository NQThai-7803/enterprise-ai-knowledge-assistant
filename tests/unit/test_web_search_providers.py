from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app.web_search.errors import WebSearchError, WebSearchFailureCode
from app.web_search.providers import BingWebSearchProvider, DuckDuckGoWebSearchProvider


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


def test_http_provider_rejects_external_calls_when_disabled() -> None:
    provider = DuckDuckGoWebSearchProvider(
        endpoint="https://api.duckduckgo.com/",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        user_agent="Tests",
        allow_external=False,
    )

    async def scenario() -> None:
        with pytest.raises(WebSearchError) as exc_info:
            await provider.search(query="question", max_results=1)
        assert exc_info.value.code == WebSearchFailureCode.WEB_SEARCH_EXTERNAL_DISABLED
        await provider.aclose()

    run_async(scenario())


def test_bing_provider_retries_retryable_status_and_parses_results() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["user-agent"] == "Tests"
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            json={
                "webPages": {
                    "value": [
                        {
                            "name": "Microsoft Learn",
                            "url": "https://learn.microsoft.com/en-us/azure/ai/",
                            "snippet": "Azure AI documentation.",
                        }
                    ]
                }
            },
            request=request,
        )

    provider = BingWebSearchProvider(
        endpoint="https://api.bing.test/v7.0/search",
        api_key=SecretStr("test-key"),
        timeout_seconds=1.0,
        max_retries=1,
        retry_backoff_seconds=0.0,
        user_agent="Tests",
        allow_external=True,
        transport=httpx.MockTransport(handler),
    )

    async def scenario() -> None:
        results = await provider.search(query="azure ai", max_results=3)
        await provider.aclose()
        assert calls == 2
        assert results.provider == "bing"
        assert len(results.results) == 1
        assert results.results[0].title == "Microsoft Learn"
        assert results.results[0].url == "https://learn.microsoft.com/en-us/azure/ai/"

    run_async(scenario())
