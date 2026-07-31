from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import httpx

from app.llm.anthropic_provider import DEFAULT_ANTHROPIC_VERSION, AnthropicLLMProvider
from app.llm.azure_openai_provider import AzureOpenAILLMProvider
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.gemini_provider import GeminiLLMProvider
from app.llm.http import append_v1_if_missing
from app.llm.models import ProviderHealth
from app.llm.openai_compatible_provider import OpenAICompatibleLLMProvider
from app.llm.provider_names import (
    ANTHROPIC_PROVIDER,
    AZURE_OPENAI_PROVIDER,
    GEMINI_PROVIDER,
    LM_STUDIO_PROVIDER,
    OLLAMA_PROVIDER,
    OPENAI_COMPATIBLE_PROVIDER,
    OPENROUTER_PROVIDER,
    SUPPORTED_PROVIDER_NAMES,
    normalize_provider_name,
    provider_display_name,
)

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.llm.base import LLMProvider


class LLMProviderRegistry:
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
            normalize_provider_name(provider): provider_transport
            for provider, provider_transport in (transports_by_provider or {}).items()
        }

    def supported_provider_names(self) -> tuple[str, ...]:
        return tuple(sorted(SUPPORTED_PROVIDER_NAMES))

    def validate_provider_name(self, provider_name: str | None = None) -> str:
        normalized = normalize_provider_name(provider_name or self.settings.llm_provider)
        if normalized not in SUPPORTED_PROVIDER_NAMES:
            raise LLMError(LLMFailureCode.LLM_PROVIDER_UNSUPPORTED)
        return normalized

    def create_provider(self, provider_name: str | None = None) -> LLMProvider:
        if not self.settings.llm_enabled:
            raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
        normalized = self.validate_provider_name(provider_name)
        return self._build_provider(normalized)

    def configuration_health(self, provider_name: str | None = None) -> ProviderHealth:
        normalized = normalize_provider_name(provider_name or self.settings.llm_provider)
        display_name = provider_display_name(normalized)
        if not self.settings.llm_enabled:
            return ProviderHealth(
                provider=normalized,
                display_name=display_name,
                status="disabled",
                configured=False,
                model=_selected_model(self.settings, normalized),
                message="LLM is disabled.",
            )
        try:
            self.validate_provider_name(normalized)
            provider = self._build_provider(normalized)
        except LLMError as exc:
            return ProviderHealth(
                provider=normalized,
                display_name=display_name,
                status="misconfigured",
                configured=False,
                model=_selected_model(self.settings, normalized),
                message=exc.safe_message,
            )
        return ProviderHealth(
            provider=normalized,
            display_name=provider.display_name,
            status="configured",
            configured=True,
            model=getattr(provider, "model", _selected_model(self.settings, normalized)),
            message="Provider configuration is valid.",
        )

    def _build_provider(self, provider_name: str) -> LLMProvider:
        transport = self._transports_by_provider.get(provider_name, self._transport)
        common = {
            "timeout_seconds": self.settings.llm_timeout_seconds,
            "max_retries": self.settings.llm_max_retries,
            "retry_backoff_seconds": self.settings.llm_retry_backoff_seconds,
            "app_env": self.settings.app_env,
            "transport": transport,
        }
        if provider_name == OPENAI_COMPATIBLE_PROVIDER:
            return OpenAICompatibleLLMProvider(
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key,
                model=self.settings.llm_model,
                provider_name=provider_name,
                **common,
            )
        if provider_name == OLLAMA_PROVIDER:
            return OpenAICompatibleLLMProvider(
                base_url=append_v1_if_missing(self.settings.llm_ollama_base_url),
                api_key=None,
                model=_required_model(self.settings.llm_ollama_model, self.settings.llm_model),
                provider_name=provider_name,
                **common,
            )
        if provider_name == LM_STUDIO_PROVIDER:
            return OpenAICompatibleLLMProvider(
                base_url=self.settings.llm_lm_studio_base_url,
                api_key=None,
                model=_required_model(self.settings.llm_lm_studio_model, self.settings.llm_model),
                provider_name=provider_name,
                **common,
            )
        if provider_name == OPENROUTER_PROVIDER:
            return OpenAICompatibleLLMProvider(
                base_url=self.settings.llm_openrouter_base_url,
                api_key=self.settings.llm_openrouter_api_key,
                model=_required_model(self.settings.llm_openrouter_model, self.settings.llm_model),
                provider_name=provider_name,
                **common,
            )
        if provider_name == AZURE_OPENAI_PROVIDER:
            return AzureOpenAILLMProvider(
                endpoint=self.settings.llm_azure_endpoint,
                api_key=self.settings.llm_azure_api_key,
                deployment=self.settings.llm_azure_deployment,
                api_version=self.settings.llm_azure_api_version,
                **common,
            )
        if provider_name == GEMINI_PROVIDER:
            return GeminiLLMProvider(
                api_key=self.settings.llm_gemini_api_key,
                model=_required_model(self.settings.llm_gemini_model, self.settings.llm_model),
                base_url=self.settings.llm_gemini_base_url,
                **common,
            )
        if provider_name == ANTHROPIC_PROVIDER:
            return AnthropicLLMProvider(
                api_key=self.settings.llm_anthropic_api_key,
                model=_required_model(self.settings.llm_anthropic_model, self.settings.llm_model),
                anthropic_version=self.settings.llm_anthropic_version or DEFAULT_ANTHROPIC_VERSION,
                base_url=self.settings.llm_anthropic_base_url,
                **common,
            )
        raise LLMError(LLMFailureCode.LLM_PROVIDER_UNSUPPORTED)


def create_provider_registry(
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    transports_by_provider: Mapping[str, httpx.AsyncBaseTransport] | None = None,
) -> LLMProviderRegistry:
    return LLMProviderRegistry(
        settings,
        transport=transport,
        transports_by_provider=transports_by_provider,
    )


def provider_configuration_health(settings: Settings) -> ProviderHealth:
    return LLMProviderRegistry(settings).configuration_health()


def _required_model(provider_model: str, default_model: str) -> str:
    model = provider_model.strip() or default_model.strip()
    if not model:
        raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
    return model


def _selected_model(settings: Settings, provider_name: str) -> str | None:
    model = ""
    if provider_name == OPENAI_COMPATIBLE_PROVIDER:
        model = settings.llm_model
    elif provider_name == OLLAMA_PROVIDER:
        model = settings.llm_ollama_model or settings.llm_model
    elif provider_name == LM_STUDIO_PROVIDER:
        model = settings.llm_lm_studio_model or settings.llm_model
    elif provider_name == OPENROUTER_PROVIDER:
        model = settings.llm_openrouter_model or settings.llm_model
    elif provider_name == AZURE_OPENAI_PROVIDER:
        model = settings.llm_azure_deployment
    elif provider_name == GEMINI_PROVIDER:
        model = settings.llm_gemini_model or settings.llm_model
    elif provider_name == ANTHROPIC_PROVIDER:
        model = settings.llm_anthropic_model or settings.llm_model
    return model.strip() or None
