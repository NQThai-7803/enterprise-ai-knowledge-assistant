from __future__ import annotations

import httpx

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.llm.provider_names import OPENAI_COMPATIBLE_PROVIDER
from app.llm.registry import LLMProviderRegistry, create_provider_registry


def create_llm_provider(
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> LLMProvider:
    return create_provider_registry(settings, transport=transport).create_provider()


__all__ = [
    "LLMProviderRegistry",
    "OPENAI_COMPATIBLE_PROVIDER",
    "create_llm_provider",
    "create_provider_registry",
]
