from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import isfinite
from uuid import UUID

from app.models import CitationSourceType

_SOURCE_MARKER_RE = re.compile(r"\[SOURCE_([1-9][0-9]*)\]")


@dataclass(frozen=True, slots=True)
class PromptSource:
    marker: str
    source_type: CitationSourceType
    document_title: str
    text: str = field(repr=False)
    page_numbers: tuple[int, ...]
    start_page: int
    end_page: int
    hybrid_score: float
    reranker_score: float | None = None
    chunk_id: UUID | None = None
    document_id: UUID | None = None
    source_url: str | None = None
    semantic_score: float | None = None
    keyword_score: float | None = None

    def __post_init__(self) -> None:
        if _SOURCE_MARKER_RE.fullmatch(self.marker) is None:
            msg = "source marker must use [SOURCE_n] format."
            raise ValueError(msg)
        object.__setattr__(self, "source_type", CitationSourceType(self.source_type))
        if not self.document_title.strip():
            msg = "document_title must not be empty."
            raise ValueError(msg)
        if not self.text.strip():
            msg = "source text must not be empty."
            raise ValueError(msg)
        page_numbers = tuple(self.page_numbers)
        object.__setattr__(self, "page_numbers", page_numbers)
        if not page_numbers or any(page_number <= 0 for page_number in page_numbers):
            msg = "page_numbers must be positive."
            raise ValueError(msg)
        if self.start_page <= 0 or self.end_page < self.start_page:
            msg = "source page range is invalid."
            raise ValueError(msg)
        if self.source_type == CitationSourceType.INTERNAL:
            if self.document_id is None or self.chunk_id is None:
                msg = "internal source must include document_id and chunk_id."
                raise ValueError(msg)
            if self.source_url is not None:
                msg = "internal source must not include source_url."
                raise ValueError(msg)
        elif self.source_type == CitationSourceType.WEB:
            if self.document_id is not None or self.chunk_id is not None:
                msg = "web source must not include internal document or chunk IDs."
                raise ValueError(msg)
            if self.source_url is None or not self.source_url.strip():
                msg = "web source must include source_url."
                raise ValueError(msg)
        else:  # pragma: no cover - enum construction above is the validation path.
            msg = "source_type is invalid."
            raise ValueError(msg)
        if self.semantic_score is not None and (
            not isfinite(self.semantic_score)
            or self.semantic_score < 0.0
            or self.semantic_score > 1.0
        ):
            msg = "semantic_score must be between 0 and 1 when present."
            raise ValueError(msg)
        if self.keyword_score is not None and (
            not isfinite(self.keyword_score) or self.keyword_score < 0.0
        ):
            msg = "keyword_score must be non-negative when present."
            raise ValueError(msg)
        if not isfinite(self.hybrid_score) or self.hybrid_score < 0.0:
            msg = "hybrid_score must be non-negative."
            raise ValueError(msg)

    @property
    def label(self) -> str:
        return self.marker[1:-1]


@dataclass(frozen=True, slots=True)
class PromptSourceRegistry:
    sources: tuple[PromptSource, ...]

    def __post_init__(self) -> None:
        sources = tuple(self.sources)
        object.__setattr__(self, "sources", sources)
        markers = [source.marker for source in sources]
        if len(markers) != len(set(markers)):
            msg = "source markers must be unique."
            raise ValueError(msg)
        internal_chunk_ids = [
            source.chunk_id
            for source in sources
            if source.source_type == CitationSourceType.INTERNAL
        ]
        if len(internal_chunk_ids) != len(set(internal_chunk_ids)):
            msg = "internal source chunk IDs must be unique."
            raise ValueError(msg)
        web_urls = [
            source.source_url for source in sources if source.source_type == CitationSourceType.WEB
        ]
        if len(web_urls) != len(set(web_urls)):
            msg = "web source URLs must be unique."
            raise ValueError(msg)

    def by_marker(self, marker: str) -> PromptSource | None:
        for source in self.sources:
            if source.marker == marker:
                return source
        return None

    def require_marker(self, marker: str) -> PromptSource:
        source = self.by_marker(marker)
        if source is None:
            msg = "source marker is not in registry."
            raise KeyError(msg)
        return source


@dataclass(frozen=True, slots=True)
class ParsedCitationMarkers:
    ordered_unique_markers: tuple[str, ...]
    all_marker_occurrences: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidatedCitation:
    document_title: str
    page_number: int
    excerpt: str = field(repr=False)
    citation_order: int
    source_type: CitationSourceType = CitationSourceType.INTERNAL
    document_id: UUID | None = None
    chunk_id: UUID | None = None
    source_url: str | None = None
    relevance_score: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_type", CitationSourceType(self.source_type))
        if not self.document_title.strip():
            msg = "document_title must not be empty."
            raise ValueError(msg)
        if self.page_number <= 0:
            msg = "page_number must be positive."
            raise ValueError(msg)
        if not self.excerpt.strip():
            msg = "excerpt must not be empty."
            raise ValueError(msg)
        if self.source_type == CitationSourceType.INTERNAL:
            if self.document_id is None:
                msg = "internal citation must include document_id."
                raise ValueError(msg)
            if self.source_url is not None:
                msg = "internal citation must not include source_url."
                raise ValueError(msg)
        elif self.source_type == CitationSourceType.WEB:
            if self.document_id is not None or self.chunk_id is not None:
                msg = "web citation must not include internal document or chunk IDs."
                raise ValueError(msg)
            if self.source_url is None or not self.source_url.strip():
                msg = "web citation must include source_url."
                raise ValueError(msg)
        else:  # pragma: no cover - enum construction above is the validation path.
            msg = "source_type is invalid."
            raise ValueError(msg)
        if self.relevance_score is not None and (
            not isfinite(self.relevance_score)
            or self.relevance_score < 0.0
            or self.relevance_score > 1.0
        ):
            msg = "relevance_score must be between 0 and 1 when present."
            raise ValueError(msg)
        if self.citation_order < 1:
            msg = "citation_order must be one-based."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ValidatedCitationAnswer:
    answer: str = field(repr=False)
    citations: tuple[ValidatedCitation, ...]

    def __post_init__(self) -> None:
        citations = tuple(self.citations)
        object.__setattr__(self, "citations", citations)
        if not self.answer.strip():
            msg = "answer must not be empty."
            raise ValueError(msg)
        orders = [citation.citation_order for citation in citations]
        if orders != list(range(1, len(citations) + 1)):
            msg = "citation_order values must be contiguous and one-based."
            raise ValueError(msg)
