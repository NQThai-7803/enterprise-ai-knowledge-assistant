from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError

import pytest

from app.document_processing.chunking.models import ChunkingResult, TextChunk

SECRET = "CONFIDENTIAL_CHUNK_MARKER"


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_chunk(
    *,
    index: int = 0,
    text: str = SECRET,
    pages: tuple[int, ...] = (1,),
    overlap: int = 0,
) -> TextChunk:
    return TextChunk(
        chunk_index=index,
        text=text,
        token_count=max(1, len(text.split())),
        character_count=len(text),
        page_numbers=pages,
        start_page=pages[0],
        end_page=pages[-1],
        overlap_token_count=overlap,
        content_sha256=checksum(text),
    )


def make_result() -> ChunkingResult:
    chunk = make_chunk()
    return ChunkingResult(
        chunks=(chunk,),
        chunk_count=1,
        total_tokens=chunk.token_count,
        total_unique_source_pages=1,
        source_page_numbers=(1,),
    )


def test_text_chunk_is_immutable() -> None:
    chunk = make_chunk()

    with pytest.raises(FrozenInstanceError):
        chunk.chunk_index = 2  # type: ignore[misc]


def test_chunking_result_is_immutable() -> None:
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.chunk_count = 2  # type: ignore[misc]


def test_chunk_index_starts_at_zero() -> None:
    chunk = make_chunk(index=1)

    with pytest.raises(ValueError, match="start at zero"):
        ChunkingResult(
            chunks=(chunk,),
            chunk_count=1,
            total_tokens=chunk.token_count,
            total_unique_source_pages=1,
            source_page_numbers=(1,),
        )


def test_chunk_repr_does_not_include_text() -> None:
    assert SECRET not in repr(make_chunk())


def test_chunking_result_repr_does_not_include_chunk_text() -> None:
    assert SECRET not in repr(make_result())


def test_content_checksum_has_sha256_length() -> None:
    chunk = make_chunk()

    assert len(chunk.content_sha256) == 64
    assert chunk.content_sha256 == checksum(chunk.text)


def test_page_numbers_are_unique_and_ordered() -> None:
    assert make_chunk(pages=(1, 2)).page_numbers == (1, 2)
    with pytest.raises(ValueError, match="unique"):
        make_chunk(pages=(1, 1))
    with pytest.raises(ValueError, match="ordered"):
        make_chunk(pages=(2, 1))


def test_start_and_end_page_are_consistent() -> None:
    chunk = make_chunk(pages=(2, 3))

    assert chunk.start_page == 2
    assert chunk.end_page == 3
    with pytest.raises(ValueError, match="start_page"):
        TextChunk(
            chunk_index=0,
            text="safe text",
            token_count=2,
            character_count=len("safe text"),
            page_numbers=(2, 3),
            start_page=1,
            end_page=3,
            overlap_token_count=0,
            content_sha256=checksum("safe text"),
        )
