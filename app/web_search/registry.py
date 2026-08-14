from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import httpx

from app.web_search.errors import WebSearchError, WebSearchFailureCode
from app.web_search.models import WebSearchProviderHealth
from app.web_search.provider_names import (
    BING_PROVIDER,
    DUCKDUCKGO_PROVIDER,
    GOOGLE_CUSTOM_SEARCH_PROVIDER,
    MOCK_PROVIDER,
    SUPPORTED_WEB_SEARCH_PROVIDERS,
    normalize_web_search_provider_name,
    web_search_provider_display_name,
)
from app.web_search.providers import (
    BingWebSearchProvider,
    DuckDuckGoWebSearchProvider,
    GoogleCustomSearchProvider,
    MockWebSearchProvider,
)

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.web_search.base import WebSearchProvider


class WebSearchProviderRegistry:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        transports_by_provider: Mapping[str, httpx.AsyncBaseTransport] | None = None,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self._transports_by_provider = {
            normalize_web_search_provider_name(provider): provider_transport
            for provider, provider_transport in (transports_by_provider or {}).items()
        }

    def supported_provider_names(self) -> tuple[str, ...]:
        return tuple(sorted(SUPPORTED_WEB_SEARCH_PROVIDERS))

    def validate_provider_name(self, provider_name: str | None = None) -> str:
        normalized = normalize_web_search_provider_name(
            provider_name or self.settings.web_search_provider
        )
        if normalized not in SUPPORTED_WEB_SEARCH_PROVIDERS:
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNSUPPORTED)
        return normalized

    def create_provider(self, provider_name: str | None = None) -> WebSearchProvider:
        if not self.settings.web_search_enabled:
            raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_DISABLED)
        normalized = self.validate_provider_name(provider_name)
        return self._build_provider(normalized)

    def configuration_health(self, provider_name: str | None = None) -> WebSearchProviderHealth:
        normalized = normalize_web_search_provider_name(
            provider_name or self.settings.web_search_provider
        )
        display_name = web_search_provider_display_name(normalized)
        if not self.settings.web_search_enabled:
            return WebSearchProviderHealth(
                provider=normalized,
                display_name=display_name,
                status="disabled",
                configured=False,
                external_allowed=False,
                message="Web search is disabled.",
            )
        try:
            self.validate_provider_name(normalized)
            provider = self._build_provider(normalized)
        except WebSearchError as exc:
            return WebSearchProviderHealth(
                provider=normalized,
                display_name=display_name,
                status="misconfigured",
                configured=False,
                external_allowed=self.settings.web_search_allow_external,
                message=exc.safe_message,
            )
        return WebSearchProviderHealth(
            provider=normalized,
            display_name=provider.display_name,
            status="configured",
            configured=True,
            external_allowed=(
                self.settings.web_search_allow_external or normalized == MOCK_PROVIDER
            ),
            message="Provider configuration is valid.",
        )

    def _build_provider(self, provider_name: str) -> WebSearchProvider:
        transport = self._transports_by_provider.get(provider_name, self._transport)
        if provider_name == MOCK_PROVIDER:
            return MockWebSearchProvider()
        common = {
            "timeout_seconds": self.settings.web_search_timeout_seconds,
            "max_retries": self.settings.web_search_max_retries,
            "retry_backoff_seconds": self.settings.web_search_retry_backoff_seconds,
            "user_agent": self.settings.web_search_user_agent,
            "allow_external": self.settings.web_search_allow_external,
            "transport": transport,
        }
        if provider_name == BING_PROVIDER:
            return BingWebSearchProvider(
                endpoint=self.settings.web_search_bing_endpoint,
                api_key=self.settings.web_search_bing_api_key,
                **common,
            )
        if provider_name == DUCKDUCKGO_PROVIDER:
            return DuckDuckGoWebSearchProvider(
                endpoint=self.settings.web_search_duckduckgo_endpoint,
                **common,
            )
        if provider_name == GOOGLE_CUSTOM_SEARCH_PROVIDER:
            return GoogleCustomSearchProvider(
                endpoint=self.settings.web_search_google_endpoint,
                api_key=self.settings.web_search_google_api_key,
                search_engine_id=self.settings.web_search_google_cx,
                **common,
            )
        raise WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNSUPPORTED)


def create_web_search_provider_registry(
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    transports_by_provider: Mapping[str, httpx.AsyncBaseTransport] | None = None,
) -> WebSearchProviderRegistry:
    return WebSearchProviderRegistry(
        settings,
        transport=transport,
        transports_by_provider=transports_by_provider,
    )
