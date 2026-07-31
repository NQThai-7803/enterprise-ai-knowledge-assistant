from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.openai_compatible_provider import OpenAICompatibleLLMProvider
from app.llm.registry import LLMProviderRegistry


def settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "_env_file": None,
        "llm_enabled": True,
        "llm_provider": "openai_compatible",
        "llm_base_url": "http://localhost:11434/v1",
        "llm_model": "test-model",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_supported_provider_names() -> None:
    registry = LLMProviderRegistry(settings(llm_enabled=False))

    assert registry.supported_provider_names() == (
        "anthropic",
        "azure_openai",
        "gemini",
        "lm_studio",
        "ollama",
        "openai_compatible",
        "openrouter",
    )


def test_unknown_provider_is_rejected() -> None:
    registry = LLMProviderRegistry(settings(llm_enabled=False, llm_provider="unknown"))

    with pytest.raises(LLMError) as exc_info:
        registry.validate_provider_name()

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_UNSUPPORTED


def test_provider_created_lazily() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"unexpected": True})

    registry = LLMProviderRegistry(settings(), transport=httpx.MockTransport(handler))
    provider = registry.create_provider()

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert calls == 0


def test_provider_registry_does_not_call_network_on_import() -> None:
    import app.llm.registry as registry_module

    assert registry_module.LLMProviderRegistry is LLMProviderRegistry


def test_openrouter_uses_compatible_adapter() -> None:
    provider = LLMProviderRegistry(
        settings(
            llm_provider="openrouter",
            llm_openrouter_api_key="router-key",
            llm_openrouter_model="openrouter/model",
        )
    ).create_provider()

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.provider_name == "openrouter"


def test_ollama_uses_compatible_adapter() -> None:
    provider = LLMProviderRegistry(
        settings(llm_provider="ollama", llm_ollama_model="llama3")
    ).create_provider()

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.provider_name == "ollama"
    assert provider.base_url.endswith("/v1")


def test_lm_studio_uses_compatible_adapter() -> None:
    provider = LLMProviderRegistry(
        settings(llm_provider="lm_studio", llm_lm_studio_model="local-model")
    ).create_provider()

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.provider_name == "lm_studio"


def test_configuration_health_is_safe_for_disabled_llm() -> None:
    health = LLMProviderRegistry(settings(llm_enabled=False, llm_model="")).configuration_health()

    assert health.status == "disabled"
    assert health.configured is False
    assert health.request_id is None
