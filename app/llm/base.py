from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.llm.models import (
    LLMMessage,
    LLMProviderCapabilities,
    LLMRequest,
    LLMResponse,
    ProviderHealth,
)


class LLMProvider(Protocol):
    capabilities: LLMProviderCapabilities

    async def generate(
        self,
        *,
        messages: Sequence[LLMMessage] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        request: LLMRequest | None = None,
    ) -> LLMResponse: ...

    async def health_check(self, *, check_connectivity: bool = False) -> ProviderHealth: ...

    async def aclose(self) -> None: ...
