from __future__ import annotations

from collections.abc import Sequence

import pytest

from app.core.config import Settings
from app.llm.manager import LLMProviderManager
from app.llm.models import LLMMessage, LLMRequest, LLMResponse, ProviderHealth


class FakeProvider:
    def __init__(self) -> None:
        self.closed = 0

    async def generate(
        self,
        *,
        messages: Sequence[LLMMessage] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        request: LLMRequest | None = None,
    ) -> LLMResponse:
        raise AssertionError("generate should not be called by lifecycle tests")

    async def health_check(self, *, check_connectivity: bool = False) -> ProviderHealth:
        return ProviderHealth(
            provider="openai_compatible",
            status="configured",
            configured=True,
            display_name="OpenAI-compatible",
            model="test-model",
            connectivity_checked=check_connectivity,
        )

    async def aclose(self) -> None:
        self.closed += 1


class FakeRegistry:
    def __init__(self) -> None:
        self.created = 0
        self.provider = FakeProvider()
        self.health_calls = 0

    def create_provider(self) -> FakeProvider:
        self.created += 1
        return self.provider

    def configuration_health(self) -> ProviderHealth:
        self.health_calls += 1
        return ProviderHealth(
            provider="openai_compatible",
            status="configured",
            configured=True,
            display_name="OpenAI-compatible",
            model="test-model",
        )


def make_manager(registry: FakeRegistry) -> LLMProviderManager:
    return LLMProviderManager(Settings(_env_file=None), registry=registry)  # type: ignore[arg-type]


def test_provider_manager_does_not_create_provider_until_requested() -> None:
    registry = FakeRegistry()
    manager = make_manager(registry)

    assert registry.created == 0

    health = manager.configuration_health()

    assert registry.created == 0
    assert registry.health_calls == 1
    assert health.status == "configured"


def test_provider_manager_reuses_provider_instance() -> None:
    registry = FakeRegistry()
    manager = make_manager(registry)

    first = manager.get_provider()
    second = manager.get_provider()

    assert first is second
    assert registry.created == 1


@pytest.mark.anyio
async def test_provider_manager_closes_cached_provider_once() -> None:
    registry = FakeRegistry()
    manager = make_manager(registry)
    provider = manager.get_provider()

    await manager.aclose()
    await manager.aclose()

    assert provider.closed == 1
