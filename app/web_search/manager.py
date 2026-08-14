from __future__ import annotations

from app.core.config import Settings
from app.web_search.base import WebSearchProvider
from app.web_search.models import WebSearchProviderHealth
from app.web_search.registry import WebSearchProviderRegistry, create_web_search_provider_registry


class WebSearchProviderManager:
    """Owns the lazy web-search provider lifecycle for an application instance."""

    def __init__(
        self,
        settings: Settings,
        *,
        registry: WebSearchProviderRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry or create_web_search_provider_registry(settings)
        self._provider: WebSearchProvider | None = None

    def get_provider(self) -> WebSearchProvider:
        if self._provider is None:
            self._provider = self.registry.create_provider()
        return self._provider

    def configuration_health(self) -> WebSearchProviderHealth:
        return self.registry.configuration_health()

    async def aclose(self) -> None:
        provider = self._provider
        self._provider = None
        if provider is not None:
            await provider.aclose()
