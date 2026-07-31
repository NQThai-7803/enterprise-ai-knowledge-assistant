from __future__ import annotations

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.llm.models import ProviderHealth
from app.llm.registry import LLMProviderRegistry, create_provider_registry


class LLMProviderManager:
    """Owns the lazy LLM provider lifecycle for an application instance."""

    def __init__(
        self,
        settings: Settings,
        *,
        registry: LLMProviderRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry or create_provider_registry(settings)
        self._provider: LLMProvider | None = None

    def get_provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = self.registry.create_provider()
        return self._provider

    def configuration_health(self) -> ProviderHealth:
        return self.registry.configuration_health()

    async def aclose(self) -> None:
        provider = self._provider
        self._provider = None
        if provider is not None:
            await provider.aclose()
