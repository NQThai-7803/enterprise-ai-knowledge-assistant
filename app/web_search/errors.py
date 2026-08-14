from __future__ import annotations

from enum import StrEnum


class WebSearchFailureCode(StrEnum):
    WEB_SEARCH_DISABLED = "WEB_SEARCH_DISABLED"
    WEB_SEARCH_EXTERNAL_DISABLED = "WEB_SEARCH_EXTERNAL_DISABLED"
    WEB_SEARCH_PROVIDER_UNSUPPORTED = "WEB_SEARCH_PROVIDER_UNSUPPORTED"
    WEB_SEARCH_PROVIDER_NOT_CONFIGURED = "WEB_SEARCH_PROVIDER_NOT_CONFIGURED"
    WEB_SEARCH_PROVIDER_TIMEOUT = "WEB_SEARCH_PROVIDER_TIMEOUT"
    WEB_SEARCH_PROVIDER_RATE_LIMITED = "WEB_SEARCH_PROVIDER_RATE_LIMITED"
    WEB_SEARCH_PROVIDER_UNAVAILABLE = "WEB_SEARCH_PROVIDER_UNAVAILABLE"
    WEB_SEARCH_PROVIDER_BAD_RESPONSE = "WEB_SEARCH_PROVIDER_BAD_RESPONSE"
    WEB_SEARCH_REQUEST_REJECTED = "WEB_SEARCH_REQUEST_REJECTED"


_SAFE_MESSAGES = {
    WebSearchFailureCode.WEB_SEARCH_DISABLED: "Web search is disabled.",
    WebSearchFailureCode.WEB_SEARCH_EXTERNAL_DISABLED: "External web search is disabled.",
    WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNSUPPORTED: "Web search provider is not supported.",
    WebSearchFailureCode.WEB_SEARCH_PROVIDER_NOT_CONFIGURED: (
        "Web search provider is not configured."
    ),
    WebSearchFailureCode.WEB_SEARCH_PROVIDER_TIMEOUT: "Web search provider timed out.",
    WebSearchFailureCode.WEB_SEARCH_PROVIDER_RATE_LIMITED: (
        "Web search provider rate-limited the request."
    ),
    WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNAVAILABLE: "Web search provider is unavailable.",
    WebSearchFailureCode.WEB_SEARCH_PROVIDER_BAD_RESPONSE: (
        "Web search provider returned an invalid response."
    ),
    WebSearchFailureCode.WEB_SEARCH_REQUEST_REJECTED: ("Web search provider rejected the request."),
}


class WebSearchError(Exception):
    def __init__(self, code: WebSearchFailureCode, message: str | None = None) -> None:
        super().__init__(_SAFE_MESSAGES.get(code, "Web search failed."))
        self.code = code
        self.safe_message = message or _SAFE_MESSAGES.get(code, "Web search failed.")
