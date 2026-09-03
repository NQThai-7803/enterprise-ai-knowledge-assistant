from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from app.citations.errors import CitationFailureCode, CitationMappingError
from app.citations.evidence import extract_exact_evidence
from app.citations.excerpt import build_evidence_centered_excerpt
from app.citations.models import PromptSourceRegistry, ValidatedCitation, ValidatedCitationAnswer
from app.citations.parser import SOURCE_MARKER_PATTERN
from app.citations.pruning import (
    prune_redundant_markers,
    remove_pruned_markers,
)
from app.models import CitationSourceType

_CITATION_VALUE_PATTERN = re.compile(
    r"(?<!\w)\d{1,4}(?::\d{2})?(?:[.,]\d+)?\s*(?:%|đ|₫|vnd)?",
    re.IGNORECASE,
)


def rewrite_internal_markers(answer: str, marker_map: Mapping[str, str]) -> str:
    def replace(match) -> str:  # noqa: ANN001
        return marker_map.get(match.group(0), match.group(0))

    return SOURCE_MARKER_PATTERN.sub(replace, answer)


def map_validated_citations(
    *,
    answer: str,
    ordered_markers: Sequence[str],
    source_registry: PromptSourceRegistry,
    document_titles_by_id: Mapping[object, str],
    excerpt_max_characters: int,
) -> ValidatedCitationAnswer:
    retained_markers = prune_redundant_markers(
        answer=answer,
        ordered_markers=ordered_markers,
        source_registry=source_registry,
    )

    pruned_answer = remove_pruned_markers(
        answer=answer,
        retained_markers=retained_markers,
    )

    marker_map = {
        marker: f"[{index}]"
        for index, marker in enumerate(
            retained_markers,
            start=1,
        )
    }

    public_answer = rewrite_internal_markers(
        pruned_answer,
        marker_map,
    )

    citations: list[ValidatedCitation] = []

    for citation_order, marker in enumerate(
        retained_markers,
        start=1,
    ):
        source = source_registry.by_marker(marker)

        if source is None:
            raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED)

        if source.page_numbers[0] != source.start_page:
            raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED)

        try:
            evidence_text = extract_exact_evidence(
                answer=answer,
                marker=marker,
                source_text=source.text,
            )
            shared_value_anchor = _shared_answer_value_anchor(
                answer=answer,
                source_text=source.text,
            )
            excerpt_anchor = shared_value_anchor or evidence_text
            excerpt = build_evidence_centered_excerpt(
                source_text=source.text,
                evidence_text=excerpt_anchor,
                max_characters=excerpt_max_characters,
            )

            if source.source_type == CitationSourceType.INTERNAL:
                document_title = document_titles_by_id.get(source.document_id)

                if not isinstance(document_title, str) or not document_title.strip():
                    raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED)

                citations.append(
                    ValidatedCitation(
                        source_type=(CitationSourceType.INTERNAL),
                        document_id=source.document_id,
                        document_title=document_title,
                        chunk_id=source.chunk_id,
                        page_number=source.start_page,
                        excerpt=excerpt,
                        relevance_score=(source.semantic_score),
                        citation_order=citation_order,
                        evidence_text=evidence_text,
                    )
                )

                continue

            citations.append(
                ValidatedCitation(
                    source_type=CitationSourceType.WEB,
                    document_title=source.document_title,
                    source_url=source.source_url,
                    page_number=source.start_page,
                    excerpt=excerpt,
                    relevance_score=None,
                    citation_order=citation_order,
                    evidence_text=evidence_text,
                )
            )

        except (
            CitationMappingError,
            ValueError,
        ) as exc:
            raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED) from exc

    return ValidatedCitationAnswer(
        answer=public_answer,
        citations=tuple(citations),
    )


def _shared_answer_value_anchor(*, answer: str, source_text: str) -> str | None:
    """Locate a cited source value when claim markers were joined at answer end."""

    answer_values = tuple(
        dict.fromkeys(match.group(0).strip() for match in _CITATION_VALUE_PATTERN.finditer(answer))
    )
    for value in sorted(answer_values, key=len, reverse=True):
        if value and value in source_text:
            return value
    return None
