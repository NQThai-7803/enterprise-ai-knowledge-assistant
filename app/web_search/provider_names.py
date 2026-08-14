from __future__ import annotations

BING_PROVIDER = "bing"
DUCKDUCKGO_PROVIDER = "duckduckgo"
GOOGLE_CUSTOM_SEARCH_PROVIDER = "google_custom_search"
MOCK_PROVIDER = "mock"

SUPPORTED_WEB_SEARCH_PROVIDERS = frozenset(
    {
        BING_PROVIDER,
        DUCKDUCKGO_PROVIDER,
        GOOGLE_CUSTOM_SEARCH_PROVIDER,
        MOCK_PROVIDER,
    }
)

_PROVIDER_DISPLAY_NAMES = {
    BING_PROVIDER: "Bing Web Search",
    DUCKDUCKGO_PROVIDER: "DuckDuckGo",
    GOOGLE_CUSTOM_SEARCH_PROVIDER: "Google Custom Search",
    MOCK_PROVIDER: "Mock Web Search",
}


def normalize_web_search_provider_name(provider_name: str) -> str:
    return provider_name.strip().lower().replace("-", "_")


def web_search_provider_display_name(provider_name: str) -> str:
    normalized = normalize_web_search_provider_name(provider_name)
    return _PROVIDER_DISPLAY_NAMES.get(normalized, normalized)
