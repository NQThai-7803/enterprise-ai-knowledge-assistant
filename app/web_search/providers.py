from __future__ import annotations

import asyncio
from collections.abc import Iterable
from time import perf_counter
from typing import Any

import httpx
from pydantic import SecretStr

from app.llm.http import safe_request_id, secret_value
from app.web_search.content import clean_web_text
from app.web_search.errors import WebSearchError, WebSearchFailureCode
from app.web_search.models import WebSearchProviderHealth, WebSearchResult, WebSearchResults
from app.web_search.provider_names import (
    BING_PROVIDER,
    DUCKDUCKGO_PROVIDER,
    GOOGLE_CUSTOM_SEARCH_PROVIDER,
    MOCK_PROVIDER,
    web_search_provider_display_name,
)

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class BaseHTTPWebSearchProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        endpoint: str,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        user_agent: str,
        allow_external: bool,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0 or max_retries < 0 or retry_backoff_seconds < 0:
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_NOT_CONFIGURED)
        if not endpoint.strip():
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_NOT_CONFIGURED)
        if not user_agent.strip():
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_NOT_CONFIGURED)
        self.provider_name = provider_name
        self.display_name = web_search_provider_display_name(provider_name)
        self.endpoint = endpoint.strip()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.user_agent = user_agent.strip()
        self.allow_external = allow_external
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def health_check(self, *, check_connectivity: bool = False) -> WebSearchProviderHealth:
        if not self.allow_external:
            return WebSearchProviderHealth(
                provider=self.provider_name,
                display_name=self.display_name,
                status="blocked",
                configured=False,
                connectivity_checked=False,
                external_allowed=False,
                message="External web search is disabled.",
            )
        if not check_connectivity:
            return WebSearchProviderHealth(
                provider=self.provider_name,
                display_name=self.display_name,
                status="configured",
                configured=True,
                connectivity_checked=False,
                external_allowed=True,
                message="Provider configuration is valid.",
            )
        try:
            response = await self._get_client().get(self.endpoint, headers=self._headers())
        except httpx.TimeoutException:
            return self._unreachable_health("Provider connectivity check timed out.")
        except httpx.HTTPError:
            return self._unreachable_health("Provider endpoint is unreachable.")
        status = "reachable" if response.status_code < 500 else "unreachable"
        return WebSearchProviderHealth(
            provider=self.provider_name,
            display_name=self.display_name,
            status=status,
            configured=True,
            connectivity_checked=True,
            external_allowed=True,
            request_id=safe_request_id(response),
            message=(
                "Provider endpoint is reachable."
                if status == "reachable"
                else "Provider endpoint is unreachable."
            ),
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_json(
        self,
        *,
        params: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], int]:
        if not self.allow_external:
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_EXTERNAL_DISABLED)
        started_at = perf_counter()
        last_error: WebSearchError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._get_client().get(
                    self.endpoint,
                    params=params,
                    headers={**self._headers(), **(headers or {})},
                )
                error = _response_error(response.status_code)
                if error is None:
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_BAD_RESPONSE)
                    return payload, max(0, int((perf_counter() - started_at) * 1000))
                if not _is_retryable_status(response.status_code) or attempt >= self.max_retries:
                    raise error
                last_error = error
            except httpx.TimeoutException as exc:
                last_error = WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_TIMEOUT)
                if attempt >= self.max_retries:
                    raise last_error from exc
            except (httpx.ConnectError, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNAVAILABLE)
                if attempt >= self.max_retries:
                    raise last_error from exc
            except ValueError as exc:
                raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_BAD_RESPONSE) from exc
            if self.retry_backoff_seconds > 0:
                await asyncio.sleep(self.retry_backoff_seconds)
        raise last_error or WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNAVAILABLE)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json"}

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(
                self.timeout_seconds,
                connect=self.timeout_seconds,
                read=self.timeout_seconds,
                write=self.timeout_seconds,
                pool=self.timeout_seconds,
            )
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
                follow_redirects=False,
                transport=self._transport,
            )
        return self._client

    def _unreachable_health(self, message: str) -> WebSearchProviderHealth:
        return WebSearchProviderHealth(
            provider=self.provider_name,
            display_name=self.display_name,
            status="unreachable",
            configured=True,
            connectivity_checked=True,
            external_allowed=True,
            message=message,
        )


class BingWebSearchProvider(BaseHTTPWebSearchProvider):
    def __init__(self, *, api_key: SecretStr, **kwargs: object) -> None:
        if not secret_value(api_key):
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_NOT_CONFIGURED)
        super().__init__(provider_name=BING_PROVIDER, **kwargs)
        self.api_key = api_key

    async def search(self, *, query: str, max_results: int) -> WebSearchResults:
        payload, _ = await self._get_json(
            params={
                "q": query,
                "count": max_results,
                "textDecorations": "false",
                "textFormat": "Raw",
            },
            headers={"Ocp-Apim-Subscription-Key": secret_value(self.api_key)},
        )
        values = (payload.get("webPages") or {}).get("value") or []
        if not isinstance(values, list):
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_BAD_RESPONSE)
        return WebSearchResults(
            query=query,
            provider=self.provider_name,
            requested_max_results=max_results,
            results=tuple(
                _result_from_fields(
                    provider=self.provider_name,
                    rank=index,
                    title=item.get("name"),
                    url=item.get("url"),
                    snippet=item.get("snippet"),
                )
                for index, item in _dict_items(values, max_results=max_results)
            ),
        )


class GoogleCustomSearchProvider(BaseHTTPWebSearchProvider):
    def __init__(self, *, api_key: SecretStr, search_engine_id: str, **kwargs: object) -> None:
        if not secret_value(api_key) or not search_engine_id.strip():
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_NOT_CONFIGURED)
        super().__init__(provider_name=GOOGLE_CUSTOM_SEARCH_PROVIDER, **kwargs)
        self.api_key = api_key
        self.search_engine_id = search_engine_id.strip()

    async def search(self, *, query: str, max_results: int) -> WebSearchResults:
        payload, _ = await self._get_json(
            params={
                "q": query,
                "num": min(max_results, 10),
                "key": secret_value(self.api_key),
                "cx": self.search_engine_id,
            }
        )
        items = payload.get("items") or []
        if not isinstance(items, list):
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_BAD_RESPONSE)
        return WebSearchResults(
            query=query,
            provider=self.provider_name,
            requested_max_results=max_results,
            results=tuple(
                _result_from_fields(
                    provider=self.provider_name,
                    rank=index,
                    title=item.get("title"),
                    url=item.get("link"),
                    snippet=item.get("snippet"),
                )
                for index, item in _dict_items(items, max_results=max_results)
            ),
        )


class DuckDuckGoWebSearchProvider(BaseHTTPWebSearchProvider):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(provider_name=DUCKDUCKGO_PROVIDER, **kwargs)

    async def search(self, *, query: str, max_results: int) -> WebSearchResults:
        payload, _ = await self._get_json(
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "no_redirect": 1,
                "skip_disambig": 1,
            }
        )
        candidates: list[dict[str, object]] = []
        abstract_url = payload.get("AbstractURL")
        abstract_text = payload.get("AbstractText")
        heading = payload.get("Heading")
        if abstract_url and abstract_text:
            candidates.append(
                {
                    "title": heading or "DuckDuckGo result",
                    "url": abstract_url,
                    "snippet": abstract_text,
                }
            )
        candidates.extend(_flatten_duckduckgo_related(payload.get("RelatedTopics")))
        return WebSearchResults(
            query=query,
            provider=self.provider_name,
            requested_max_results=max_results,
            results=tuple(
                _result_from_fields(
                    provider=self.provider_name,
                    rank=index,
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=item.get("snippet"),
                )
                for index, item in _dict_items(candidates, max_results=max_results)
            ),
        )


class MockWebSearchProvider:
    provider_name = MOCK_PROVIDER
    display_name = web_search_provider_display_name(MOCK_PROVIDER)

    def __init__(self, *, results: tuple[WebSearchResult, ...] | None = None) -> None:
        self._results = results

    async def search(self, *, query: str, max_results: int) -> WebSearchResults:
        results = self._results
        if results is None:
            results = (
                WebSearchResult(
                    title="Mock Web Result",
                    url="https://example.com/mock-web-result",
                    snippet=f"Mock web search result for {query}.",
                    content=f"Mock web search result for {query}.",
                    provider=self.provider_name,
                    rank=1,
                    score=1.0,
                ),
            )
        return WebSearchResults(
            query=query,
            provider=self.provider_name,
            results=tuple(results[:max_results]),
            requested_max_results=max_results,
        )

    async def health_check(self, *, check_connectivity: bool = False) -> WebSearchProviderHealth:
        return WebSearchProviderHealth(
            provider=self.provider_name,
            display_name=self.display_name,
            status="configured",
            configured=True,
            connectivity_checked=check_connectivity,
            external_allowed=False,
            message="Mock provider is configured.",
        )

    async def aclose(self) -> None:
        return None


def _result_from_fields(
    *,
    provider: str,
    rank: int,
    title: object,
    url: object,
    snippet: object,
) -> WebSearchResult:
    title_text = clean_web_text(str(title or ""), max_length=300)
    snippet_text = clean_web_text(str(snippet or ""), max_length=1000)
    return WebSearchResult(
        title=title_text,
        url=str(url or ""),
        snippet=snippet_text,
        content=snippet_text,
        provider=provider,
        rank=rank,
        score=1.0 / rank,
    )


def _dict_items(
    items: Iterable[object],
    *,
    max_results: int,
) -> Iterable[tuple[int, dict[str, Any]]]:
    emitted = 0
    for item in items:
        if emitted >= max_results:
            break
        if not isinstance(item, dict):
            continue
        try:
            _ = _result_from_fields(
                provider="validation",
                rank=emitted + 1,
                title=item.get("title") or item.get("name"),
                url=item.get("url") or item.get("link") or item.get("FirstURL"),
                snippet=item.get("snippet") or item.get("Text"),
            )
        except ValueError:
            continue
        emitted += 1
        yield emitted, item


def _flatten_duckduckgo_related(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    flattened: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("Topics"), list):
            flattened.extend(_flatten_duckduckgo_related(item.get("Topics")))
            continue
        if item.get("FirstURL") and item.get("Text"):
            flattened.append(
                {
                    "title": item.get("Text"),
                    "url": item.get("FirstURL"),
                    "snippet": item.get("Text"),
                }
            )
    return flattened


def _response_error(status_code: int) -> WebSearchError | None:
    if status_code < 400:
        return None
    if status_code in {401, 403}:
        return WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_NOT_CONFIGURED)
    if status_code == 408:
        return WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_TIMEOUT)
    if status_code == 429:
        return WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_RATE_LIMITED)
    if 500 <= status_code <= 599:
        return WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNAVAILABLE)
    if status_code in {400, 422}:
        return WebSearchError(WebSearchFailureCode.WEB_SEARCH_REQUEST_REJECTED)
    return WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_BAD_RESPONSE)


def _is_retryable_status(status_code: int) -> bool:
    return status_code in _RETRYABLE_STATUS_CODES
