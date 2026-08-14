from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.config import Settings, get_settings
from app.web_search.base import WebSearchProvider
from app.web_search.content import clean_web_text
from app.web_search.errors import WebSearchError, WebSearchFailureCode
from app.web_search.models import WebSearchResult, WebSearchResults

logger = logging.getLogger(__name__)

WebSearchProviderFactory = Callable[[], WebSearchProvider]


class WebSearchService:
    def __init__(
        self,
        *,
        provider_factory: WebSearchProviderFactory,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider_factory = provider_factory

    async def search(self, *, query: str) -> WebSearchResults:
        if not self.settings.web_search_enabled:
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_DISABLED)
        normalized_query = clean_web_text(
            query,
            max_length=self.settings.retrieval_max_query_characters,
        )
        if not normalized_query:
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_REQUEST_REJECTED)
        provider = self.provider_factory()
        result = await provider.search(
            query=normalized_query,
            max_results=self.settings.web_search_max_results,
        )
        normalized_results = self._normalize_results(result.results)
        logger.info(
            "Web search completed.",
            extra={
                "provider": result.provider,
                "result_count": len(normalized_results),
                "requested_max_results": self.settings.web_search_max_results,
            },
        )
        return WebSearchResults(
            query=normalized_query,
            provider=result.provider,
            results=normalized_results,
            requested_max_results=self.settings.web_search_max_results,
        )

    def _normalize_results(
        self,
        results: tuple[WebSearchResult, ...],
    ) -> tuple[WebSearchResult, ...]:
        normalized: list[WebSearchResult] = []
        seen_urls: set[str] = set()
        for result in results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            try:
                normalized.append(
                    WebSearchResult(
                        title=result.title,
                        url=result.url,
                        snippet=result.snippet,
                        content=clean_web_text(
                            result.content,
                            max_length=self.settings.web_search_max_content_length,
                        ),
                        provider=result.provider,
                        rank=len(normalized) + 1,
                        score=result.score,
                    )
                )
            except ValueError:
                continue
            if len(normalized) >= self.settings.web_search_max_results:
                break
        return tuple(normalized)
