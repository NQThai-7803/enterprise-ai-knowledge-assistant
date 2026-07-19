from __future__ import annotations

import logging
from collections.abc import Sequence

import pytest

from app.document_processing.chunking.page_aware_chunker import PageAwareTokenChunker
from app.document_processing.errors import ChunkingError, ChunkingFailureCode
from tests.unit.test_page_aware_chunker import CharacterTokenCounter, make_extraction

SECRET = "CONFIDENTIAL_CHUNK_MARKER"


class TokenIdLeakingCounter:
    def count(self, text: str) -> int:
        raise RuntimeError(f"token ids [123, 456] failed for {text}")

    def encode(self, text: str) -> tuple[int, ...]:
        raise RuntimeError(f"token ids [123, 456] failed for {text}")

    def decode(self, tokens: Sequence[int]) -> str:
        raise RuntimeError(f"token ids {list(tokens)} failed")


def make_secure_chunker(token_counter: object | None = None) -> PageAwareTokenChunker:
    return PageAwareTokenChunker(
        token_counter=token_counter or CharacterTokenCounter(),  # type: ignore[arg-type]
        target_tokens=30,
        max_tokens=40,
        overlap_tokens=5,
        min_tokens=0,
    )


def test_chunk_repr_does_not_include_confidential_text() -> None:
    result = make_secure_chunker().chunk(make_extraction((1, SECRET)))

    assert SECRET not in repr(result.chunks[0])


def test_chunking_error_does_not_include_source_text() -> None:
    with pytest.raises(ChunkingError) as exc_info:
        make_secure_chunker(TokenIdLeakingCounter()).chunk(make_extraction((1, SECRET)))

    assert exc_info.value.code == ChunkingFailureCode.TOKENIZATION_FAILED
    assert SECRET not in str(exc_info.value)
    assert SECRET not in exc_info.value.safe_message


def test_tokenization_error_does_not_include_token_ids() -> None:
    with pytest.raises(ChunkingError) as exc_info:
        make_secure_chunker(TokenIdLeakingCounter()).chunk(make_extraction((1, "safe text")))

    assert "123" not in str(exc_info.value)
    assert "456" not in str(exc_info.value)


def test_chunking_log_does_not_include_page_text(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    make_secure_chunker().chunk(make_extraction((1, SECRET)))

    assert SECRET not in caplog.text


def test_chunking_log_does_not_include_chunk_text(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    result = make_secure_chunker().chunk(make_extraction((1, SECRET)))

    assert result.chunks[0].text == SECRET
    assert SECRET not in caplog.text


def test_chunk_result_does_not_include_storage_key() -> None:
    storage_key = "documents/private/secret-storage-key.pdf"
    result = make_secure_chunker().chunk(make_extraction((1, "safe content")))

    assert not hasattr(result.chunks[0], "storage_key")
    assert storage_key not in repr(result)


def test_chunk_result_does_not_include_absolute_path() -> None:
    absolute_path = "C:\\private\\secret.pdf"
    result = make_secure_chunker().chunk(make_extraction((1, "safe content")))

    assert not hasattr(result.chunks[0], "absolute_path")
    assert absolute_path not in repr(result)


def test_chunk_result_does_not_include_document_id() -> None:
    document_id = "00000000-0000-0000-0000-000000000001"
    result = make_secure_chunker().chunk(make_extraction((1, "safe content")))

    assert not hasattr(result.chunks[0], "document_id")
    assert document_id not in repr(result)
