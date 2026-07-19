from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.document_processing.chunking.models import ChunkingResult, TextChunk
from app.document_processing.chunking.text_units import (
    TextUnit,
    TextUnitKind,
    split_paragraphs,
    split_sentences,
    split_text_unit_to_token_windows,
)
from app.document_processing.errors import ChunkingError, ChunkingFailureCode
from app.document_processing.models import ExtractionResult
from app.document_processing.tokenization.base import TokenCounter

_CHUNK_SEPARATOR = "\n\n"


@dataclass(slots=True)
class _ChunkSegment:
    text: str = field(repr=False)
    page_numbers: tuple[int, ...]
    token_count: int
    is_overlap: bool = False


@dataclass(slots=True)
class _DraftChunk:
    segments: list[_ChunkSegment] = field(default_factory=list)
    overlap_token_count: int = 0

    @property
    def has_new_content(self) -> bool:
        return any(not segment.is_overlap for segment in self.segments)


class PageAwareTokenChunker:
    def __init__(
        self,
        *,
        token_counter: TokenCounter,
        target_tokens: int,
        max_tokens: int,
        overlap_tokens: int,
        min_tokens: int,
    ) -> None:
        self.token_counter = token_counter
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens
        self._validate_configuration()

    def chunk(self, extraction: ExtractionResult) -> ChunkingResult:
        if extraction.total_usable_characters <= 0:
            raise ChunkingError(ChunkingFailureCode.EMPTY_EXTRACTION)
        try:
            units = self._build_units(extraction)
            if not units:
                raise ChunkingError(ChunkingFailureCode.EMPTY_EXTRACTION)
            drafts = self._assemble_units(units)
            drafts = self._merge_small_final_chunk(drafts)
            return self._build_result(drafts)
        except ChunkingError:
            raise
        except Exception as exc:
            raise ChunkingError(ChunkingFailureCode.CHUNKING_FAILED) from exc

    def _validate_configuration(self) -> None:
        if self.target_tokens <= 0:
            raise ChunkingError(ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION)
        if self.max_tokens < self.target_tokens:
            raise ChunkingError(ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION)
        if self.overlap_tokens < 0:
            raise ChunkingError(ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION)
        if self.overlap_tokens >= self.target_tokens:
            raise ChunkingError(ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION)
        if self.min_tokens < 0 or self.min_tokens > self.target_tokens:
            raise ChunkingError(ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION)

    def _build_units(self, extraction: ExtractionResult) -> tuple[TextUnit, ...]:
        pages = tuple(sorted(extraction.pages, key=lambda page: page.page_number))
        if len({page.page_number for page in pages}) != len(pages):
            raise ChunkingError(ChunkingFailureCode.CHUNKING_FAILED)

        units: list[TextUnit] = []
        for page in pages:
            if page.usable_character_count <= 0 or not page.text.strip():
                continue
            for paragraph in split_paragraphs(page.page_number, page.text):
                units.extend(self._split_unit_to_max_tokens(paragraph))
        return tuple(units)

    def _split_unit_to_max_tokens(self, unit: TextUnit) -> tuple[TextUnit, ...]:
        token_count = self._count(unit.text)
        if token_count <= self.max_tokens:
            return (
                TextUnit(
                    page_number=unit.page_number,
                    text=unit.text,
                    token_count=token_count,
                    kind=unit.kind,
                ),
            )

        sentence_units: list[TextUnit] = []
        for sentence in split_sentences(unit):
            sentence_count = self._count(sentence.text)
            if sentence_count <= self.max_tokens:
                sentence_units.append(
                    TextUnit(
                        page_number=sentence.page_number,
                        text=sentence.text,
                        token_count=sentence_count,
                        kind=TextUnitKind.SENTENCE,
                    )
                )
                continue
            sentence_units.extend(
                split_text_unit_to_token_windows(
                    TextUnit(
                        page_number=sentence.page_number,
                        text=sentence.text,
                        token_count=sentence_count,
                        kind=TextUnitKind.SENTENCE,
                    ),
                    self.token_counter,
                    max_tokens=self.max_tokens,
                    overlap_tokens=self.overlap_tokens,
                )
            )
        return tuple(sentence_units)

    def _assemble_units(self, units: tuple[TextUnit, ...]) -> list[_DraftChunk]:
        drafts: list[_DraftChunk] = []
        current = _DraftChunk()
        pending_overlap: list[_ChunkSegment] = []

        for unit in units:
            segment = self._segment_from_unit(unit)
            if not current.segments:
                current = self._new_draft_with_overlap(
                    pending_overlap,
                    segment,
                    unit.overlap_token_count,
                )

            candidate_segments = [*current.segments, segment]
            candidate_token_count = self._count_segments(candidate_segments)
            current_token_count = self._count_segments(current.segments)

            if candidate_token_count <= self.target_tokens or (
                current.has_new_content
                and current_token_count < self.target_tokens
                and candidate_token_count <= self.max_tokens
            ):
                current.segments.append(segment)
                continue

            if not current.has_new_content:
                if candidate_token_count > self.max_tokens:
                    current = _DraftChunk()
                    candidate_segments = [segment]
                    candidate_token_count = self._count_segments(candidate_segments)
                if candidate_token_count > self.max_tokens:
                    raise ChunkingError(ChunkingFailureCode.CHUNKING_FAILED)
                current.segments.append(segment)
                continue

            drafts.append(current)
            pending_overlap = self._make_overlap_segments(current)
            current = self._new_draft_with_overlap(
                pending_overlap,
                segment,
                unit.overlap_token_count,
            )
            candidate_segments = [*current.segments, segment]
            candidate_token_count = self._count_segments(candidate_segments)
            if candidate_token_count > self.max_tokens:
                current = _DraftChunk(overlap_token_count=unit.overlap_token_count)
                candidate_segments = [segment]
                candidate_token_count = self._count_segments(candidate_segments)
            if candidate_token_count > self.max_tokens:
                raise ChunkingError(ChunkingFailureCode.CHUNKING_FAILED)
            current.segments.append(segment)

        if current.has_new_content:
            drafts.append(current)
        return drafts

    def _merge_small_final_chunk(self, drafts: list[_DraftChunk]) -> list[_DraftChunk]:
        if len(drafts) < 2 or self.min_tokens == 0:
            return drafts
        final = drafts[-1]
        final_token_count = self._count_segments(final.segments)
        if final_token_count >= self.min_tokens:
            return drafts

        previous = drafts[-2]
        final_unique_segments = [segment for segment in final.segments if not segment.is_overlap]
        merged_segments = [*previous.segments, *final_unique_segments]
        if not final_unique_segments:
            return drafts
        if self._count_segments(merged_segments) > self.max_tokens:
            return drafts

        drafts[-2] = _DraftChunk(
            segments=merged_segments,
            overlap_token_count=previous.overlap_token_count,
        )
        return drafts[:-1]

    def _new_draft_with_overlap(
        self,
        pending_overlap: list[_ChunkSegment],
        first_segment: _ChunkSegment,
        unit_overlap_tokens: int,
    ) -> _DraftChunk:
        if unit_overlap_tokens > 0:
            return _DraftChunk(
                overlap_token_count=min(unit_overlap_tokens, first_segment.token_count)
            )

        fitted_overlap = self._fit_overlap_segments(pending_overlap, first_segment)
        return _DraftChunk(
            segments=fitted_overlap,
            overlap_token_count=self._count_segments(fitted_overlap),
        )

    def _fit_overlap_segments(
        self,
        pending_overlap: list[_ChunkSegment],
        first_segment: _ChunkSegment,
    ) -> list[_ChunkSegment]:
        if not pending_overlap or self.overlap_tokens == 0:
            return []

        overlap_text = _join_segments(pending_overlap)
        tokens = self._encode(overlap_text)
        max_overlap = min(len(tokens), self.overlap_tokens)
        page_numbers = _unique_pages_from_segments(pending_overlap)
        for token_count in range(max_overlap, 0, -1):
            text = self._decode(tokens[-token_count:]).strip()
            if not text:
                continue
            segment = _ChunkSegment(
                text=text,
                page_numbers=page_numbers,
                token_count=self._count(text),
                is_overlap=True,
            )
            if self._count_segments([segment, first_segment]) <= self.max_tokens:
                return [segment]
        return []

    def _make_overlap_segments(self, chunk: _DraftChunk) -> list[_ChunkSegment]:
        if self.overlap_tokens == 0:
            return []
        source_segments = [segment for segment in chunk.segments if not segment.is_overlap]
        if not source_segments:
            return []
        source_text = _join_segments(source_segments)
        source_tokens = self._encode(source_text)
        if len(source_tokens) <= 1:
            return []
        overlap_size = min(self.overlap_tokens, len(source_tokens) - 1)
        overlap_text = self._decode(source_tokens[-overlap_size:]).strip()
        if not overlap_text:
            return []
        page_numbers = self._tail_page_numbers(source_segments, overlap_size)
        return [
            _ChunkSegment(
                text=overlap_text,
                page_numbers=page_numbers,
                token_count=self._count(overlap_text),
                is_overlap=True,
            )
        ]

    def _tail_page_numbers(
        self,
        segments: list[_ChunkSegment],
        overlap_size: int,
    ) -> tuple[int, ...]:
        remaining = overlap_size
        pages: list[int] = []
        for segment in reversed(segments):
            for page_number in reversed(segment.page_numbers):
                if page_number not in pages:
                    pages.append(page_number)
            remaining -= max(1, segment.token_count)
            if remaining <= 0:
                break
        return tuple(sorted(pages))

    def _segment_from_unit(self, unit: TextUnit) -> _ChunkSegment:
        token_count = unit.token_count if unit.token_count is not None else self._count(unit.text)
        return _ChunkSegment(
            text=unit.text,
            page_numbers=(unit.page_number,),
            token_count=token_count,
            is_overlap=False,
        )

    def _build_result(self, drafts: list[_DraftChunk]) -> ChunkingResult:
        chunks: list[TextChunk] = []
        for chunk_index, draft in enumerate(drafts):
            text = _join_segments(draft.segments)
            token_count = self._count(text)
            page_numbers = _unique_pages_from_segments(draft.segments)
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    text=text,
                    token_count=token_count,
                    character_count=len(text),
                    page_numbers=page_numbers,
                    start_page=page_numbers[0],
                    end_page=page_numbers[-1],
                    overlap_token_count=0 if chunk_index == 0 else draft.overlap_token_count,
                    content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )

        chunk_tuple = tuple(chunks)
        source_page_numbers = tuple(
            sorted({page_number for chunk in chunk_tuple for page_number in chunk.page_numbers})
        )
        return ChunkingResult(
            chunks=chunk_tuple,
            chunk_count=len(chunk_tuple),
            total_tokens=sum(chunk.token_count for chunk in chunk_tuple),
            total_unique_source_pages=len(source_page_numbers),
            source_page_numbers=source_page_numbers,
        )

    def _count_segments(self, segments: list[_ChunkSegment]) -> int:
        if not segments:
            return 0
        return self._count(_join_segments(segments))

    def _count(self, text: str) -> int:
        try:
            return self.token_counter.count(text)
        except ChunkingError:
            raise
        except Exception as exc:
            raise ChunkingError(ChunkingFailureCode.TOKENIZATION_FAILED) from exc

    def _encode(self, text: str) -> tuple[int, ...]:
        try:
            return self.token_counter.encode(text)
        except ChunkingError:
            raise
        except Exception as exc:
            raise ChunkingError(ChunkingFailureCode.TOKENIZATION_FAILED) from exc

    def _decode(self, tokens: tuple[int, ...]) -> str:
        try:
            return self.token_counter.decode(tokens)
        except ChunkingError:
            raise
        except Exception as exc:
            raise ChunkingError(ChunkingFailureCode.TOKENIZATION_FAILED) from exc


def _join_segments(segments: list[_ChunkSegment]) -> str:
    return _CHUNK_SEPARATOR.join(segment.text for segment in segments if segment.text.strip())


def _unique_pages_from_segments(segments: list[_ChunkSegment]) -> tuple[int, ...]:
    return tuple(
        sorted({page_number for segment in segments for page_number in segment.page_numbers})
    )
