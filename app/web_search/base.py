from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.web_search.models import WebSearchProviderHealth, WebSearchResults


@runtime_checkable
class WebSearchProvider(Protocol):
    provider_name: str
    display_name: str

    async def search(self, *, query: str, max_results: int) -> WebSearchResults: ...

    async def health_check(
        self, *, check_connectivity: bool = False
    ) -> WebSearchProviderHealth: ...

    async def aclose(self) -> None: ...
