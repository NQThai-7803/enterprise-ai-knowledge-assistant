from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.citations.errors import CitationFailureCode, CitationMappingError
from app.citations.excerpt import build_excerpt
from app.citations.models import PromptSourceRegistry, ValidatedCitation, ValidatedCitationAnswer
from app.citations.parser import SOURCE_MARKER_PATTERN
from app.models import CitationSourceType


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
    marker_map = {marker: f"[{index}]" for index, marker in enumerate(ordered_markers, start=1)}
    public_answer = rewrite_internal_markers(answer, marker_map)
    citations: list[ValidatedCitation] = []
    for citation_order, marker in enumerate(ordered_markers, start=1):
        source = source_registry.by_marker(marker)
        if source is None:
            raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED)
        if source.page_numbers[0] != source.start_page:
            raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED)
        try:
            excerpt = build_excerpt(
                source_text=source.text,
                max_characters=excerpt_max_characters,
            )
            if source.source_type == CitationSourceType.INTERNAL:
                document_title = document_titles_by_id.get(source.document_id)
                if not isinstance(document_title, str) or not document_title.strip():
                    raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED)
                citations.append(
                    ValidatedCitation(
                        source_type=CitationSourceType.INTERNAL,
                        document_id=source.document_id,
                        document_title=document_title,
                        chunk_id=source.chunk_id,
                        page_number=source.start_page,
                        excerpt=excerpt,
                        relevance_score=source.semantic_score,
                        citation_order=citation_order,
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
                )
            )
        except (CitationMappingError, ValueError) as exc:
            raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED) from exc
    return ValidatedCitationAnswer(answer=public_answer, citations=tuple(citations))
