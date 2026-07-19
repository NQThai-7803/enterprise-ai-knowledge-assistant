from __future__ import annotations

from dataclasses import dataclass, field

_HEX_DIGITS = set("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_index: int
    text: str = field(repr=False)
    token_count: int
    character_count: int
    page_numbers: tuple[int, ...]
    start_page: int
    end_page: int
    overlap_token_count: int
    content_sha256: str

    def __post_init__(self) -> None:
        page_numbers = tuple(self.page_numbers)
        object.__setattr__(self, "page_numbers", page_numbers)
        if self.chunk_index < 0:
            msg = "chunk_index must not be negative."
            raise ValueError(msg)
        if not self.text.strip():
            msg = "text must not be empty."
            raise ValueError(msg)
        if self.token_count <= 0:
            msg = "token_count must be greater than zero."
            raise ValueError(msg)
        if self.character_count != len(self.text):
            msg = "character_count must match text length."
            raise ValueError(msg)
        if not page_numbers:
            msg = "page_numbers must not be empty."
            raise ValueError(msg)
        if page_numbers != tuple(sorted(page_numbers)):
            msg = "page_numbers must be ordered."
            raise ValueError(msg)
        if len(set(page_numbers)) != len(page_numbers):
            msg = "page_numbers must be unique."
            raise ValueError(msg)
        if self.start_page != page_numbers[0]:
            msg = "start_page must match the first page number."
            raise ValueError(msg)
        if self.end_page != page_numbers[-1]:
            msg = "end_page must match the last page number."
            raise ValueError(msg)
        if self.overlap_token_count < 0:
            msg = "overlap_token_count must not be negative."
            raise ValueError(msg)
        if len(self.content_sha256) != 64:
            msg = "content_sha256 must be a SHA-256 hex digest."
            raise ValueError(msg)
        if self.content_sha256 != self.content_sha256.lower():
            msg = "content_sha256 must be lowercase."
            raise ValueError(msg)
        if any(character not in _HEX_DIGITS for character in self.content_sha256):
            msg = "content_sha256 must be hexadecimal."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ChunkingResult:
    chunks: tuple[TextChunk, ...]
    chunk_count: int
    total_tokens: int
    total_unique_source_pages: int
    source_page_numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        chunks = tuple(self.chunks)
        source_page_numbers = tuple(self.source_page_numbers)
        object.__setattr__(self, "chunks", chunks)
        object.__setattr__(self, "source_page_numbers", source_page_numbers)
        if self.chunk_count != len(chunks):
            msg = "chunk_count must match chunks length."
            raise ValueError(msg)
        if self.total_tokens != sum(chunk.token_count for chunk in chunks):
            msg = "total_tokens must match chunk token counts."
            raise ValueError(msg)
        expected_indexes = tuple(range(len(chunks)))
        if tuple(chunk.chunk_index for chunk in chunks) != expected_indexes:
            msg = "chunk indexes must start at zero and be contiguous."
            raise ValueError(msg)
        expected_pages = tuple(
            sorted({page_number for chunk in chunks for page_number in chunk.page_numbers})
        )
        if source_page_numbers != expected_pages:
            msg = "source_page_numbers must match chunk page metadata."
            raise ValueError(msg)
        if self.total_unique_source_pages != len(source_page_numbers):
            msg = "total_unique_source_pages must match source_page_numbers."
            raise ValueError(msg)
