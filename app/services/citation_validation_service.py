from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.citations.errors import (
    CitationFailureCode,
    CitationMappingError,
    CitationPermissionRevalidationError,
    CitationValidationError,
)
from app.citations.mapper import map_validated_citations
from app.citations.models import PromptSourceRegistry, ValidatedCitationAnswer
from app.citations.parser import parse_citation_markers
from app.core.config import Settings, get_settings
from app.models import User
from app.repositories import citation_source_repository


class CitationValidationService:
    def __init__(
        self,
        *,
        session_provider: async_sessionmaker[AsyncSession],
        settings: Settings | None = None,
        source_repository=citation_source_repository,
    ) -> None:
        self.session_provider = session_provider
        self.settings = settings or get_settings()
        self.source_repository = source_repository

    async def validate_and_map(
        self,
        *,
        answer: str,
        source_registry: PromptSourceRegistry,
        current_user: User,
    ) -> ValidatedCitationAnswer:
        ordered_markers = _validate_answer_markers(
            answer=answer,
            source_registry=source_registry,
            max_sources=self.settings.citation_max_sources_per_answer,
        )
        cited_sources = tuple(source_registry.require_marker(marker) for marker in ordered_markers)
        async with self.session_provider() as session:
            permitted_rows = await self.source_repository.get_permitted_ready_chunks_by_ids(
                session,
                chunk_ids=tuple(source.chunk_id for source in cited_sources),
                current_user=current_user,
            )
        permitted_by_chunk_id = {row.chunk_id: row for row in permitted_rows}
        if set(permitted_by_chunk_id) != {source.chunk_id for source in cited_sources}:
            raise CitationPermissionRevalidationError()
        if any(
            permitted_by_chunk_id[source.chunk_id].document_id != source.document_id
            for source in cited_sources
        ):
            raise CitationPermissionRevalidationError()
        document_titles_by_id = {row.document_id: row.document_title for row in permitted_rows}
        try:
            return map_validated_citations(
                answer=answer,
                ordered_markers=ordered_markers,
                source_registry=source_registry,
                document_titles_by_id=document_titles_by_id,
                excerpt_max_characters=self.settings.citation_excerpt_max_characters,
            )
        except CitationMappingError:
            raise
        except Exception as exc:
            raise CitationMappingError(CitationFailureCode.CITATION_MAPPING_FAILED) from exc


def _validate_answer_markers(
    *,
    answer: str,
    source_registry: PromptSourceRegistry,
    max_sources: int,
) -> tuple[str, ...]:
    parsed = parse_citation_markers(answer)
    if not parsed.ordered_unique_markers:
        code = (
            CitationFailureCode.CITATION_MARKER_INVALID
            if "[SOURCE_" in answer
            else CitationFailureCode.CITATION_MARKER_MISSING
        )
        raise CitationValidationError(code)
    if len(parsed.ordered_unique_markers) > max_sources:
        raise CitationValidationError(CitationFailureCode.CITATION_MARKER_INVALID)
    registry_markers = {source.marker for source in source_registry.sources}
    unknown_markers = [
        marker for marker in parsed.all_marker_occurrences if marker not in registry_markers
    ]
    if unknown_markers:
        raise CitationValidationError(CitationFailureCode.CITATION_MARKER_UNKNOWN)
    return parsed.ordered_unique_markers
