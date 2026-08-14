from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from numbers import Real
from typing import Literal

from app.web_search.content import clean_web_text, normalize_web_url

WebSearchProviderHealthStatus = Literal[
    "configured",
    "disabled",
    "blocked",
    "reachable",
    "unreachable",
    "misconfigured",
]


class KnowledgeSourceMode(StrEnum):
    INTERNAL_ONLY = "internal_only"
    HYBRID = "hybrid"
    WEB_ONLY = "web_only"


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str = field(repr=False)
    content: str = field(repr=False)
    provider: str
    rank: int
    score: float | None = None

    def __post_init__(self) -> None:
        title = clean_web_text(self.title, max_length=300)
        snippet = clean_web_text(self.snippet, max_length=1000)
        content = clean_web_text(self.content or self.snippet, max_length=4000)
        url = normalize_web_url(self.url)
        if not title:
            msg = "Web search title must not be empty."
            raise ValueError(msg)
        if not content:
            msg = "Web search content must not be empty."
            raise ValueError(msg)
        if not isinstance(self.provider, str) or not self.provider.strip():
            msg = "Web search provider must not be empty."
            raise ValueError(msg)
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank < 1:
            msg = "Web search rank must be one-based."
            raise ValueError(msg)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "snippet", snippet or content)
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "provider", self.provider.strip())
        if self.score is not None:
            if isinstance(self.score, bool) or not isinstance(self.score, Real):
                msg = "Web search score must be finite when present."
                raise ValueError(msg)
            score = float(self.score)
            if not isfinite(score) or score < 0.0:
                msg = "Web search score must be finite and non-negative."
                raise ValueError(msg)
            object.__setattr__(self, "score", score)

    @property
    def domain(self) -> str:
        return normalize_web_url(self.url, return_hostname=True)


@dataclass(frozen=True, slots=True)
class WebSearchResults:
    query: str = field(repr=False)
    provider: str
    results: tuple[WebSearchResult, ...]
    requested_max_results: int

    def __post_init__(self) -> None:
        if not isinstance(self.query, str) or not self.query.strip():
            msg = "Web search query must not be empty."
            raise ValueError(msg)
        if not isinstance(self.provider, str) or not self.provider.strip():
            msg = "Web search provider must not be empty."
            raise ValueError(msg)
        results = tuple(self.results)
        object.__setattr__(self, "results", results)
        if self.requested_max_results < 1:
            msg = "requested_max_results must be positive."
            raise ValueError(msg)
        if len(results) > self.requested_max_results:
            msg = "result count must not exceed requested_max_results."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class WebSearchProviderHealth:
    provider: str
    status: WebSearchProviderHealthStatus
    configured: bool
    display_name: str | None = None
    message: str | None = None
    connectivity_checked: bool = False
    external_allowed: bool = False
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider.strip():
            msg = "provider must not be empty."
            raise ValueError(msg)
        if self.display_name is not None and not self.display_name.strip():
            msg = "display_name must not be empty when present."
            raise ValueError(msg)
        if self.message is not None and not self.message.strip():
            msg = "message must not be empty when present."
            raise ValueError(msg)
        if self.request_id is not None and not self.request_id.strip():
            msg = "request_id must not be empty when present."
            raise ValueError(msg)
