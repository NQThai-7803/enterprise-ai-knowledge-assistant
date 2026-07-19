from __future__ import annotations

import socket

import pytest

from app.document_processing.errors import ChunkingError, ChunkingFailureCode
from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter


def test_tiktoken_count_matches_encoded_length() -> None:
    counter = TiktokenTokenCounter("cl100k_base")
    text = "Enterprise knowledge assistant"

    assert counter.count(text) == len(counter.encode(text))


def test_tiktoken_encode_returns_immutable_tuple() -> None:
    counter = TiktokenTokenCounter("cl100k_base")

    encoded = counter.encode("immutable tokens")

    assert isinstance(encoded, tuple)


def test_tiktoken_decode_round_trips_vietnamese_text() -> None:
    counter = TiktokenTokenCounter("cl100k_base")
    text = "Hợp đồng số HD-2026-001 có hiệu lực từ 17/07/2026."

    assert counter.decode(counter.encode(text)) == text


def test_tiktoken_handles_emoji() -> None:
    counter = TiktokenTokenCounter("cl100k_base")
    text = "Status ✅ priority ⚠️"

    assert counter.decode(counter.encode(text)) == text
    assert counter.count(text) > 0


def test_tiktoken_handles_empty_text() -> None:
    counter = TiktokenTokenCounter("cl100k_base")

    assert counter.encode("") == ()
    assert counter.count("") == 0
    assert counter.decode(()) == ""


def test_invalid_encoding_name_is_rejected() -> None:
    with pytest.raises(ChunkingError) as exc_info:
        TiktokenTokenCounter("not-a-real-encoding")

    assert exc_info.value.code == ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION
    assert exc_info.value.safe_message == "The chunking configuration is invalid."


def test_token_counter_does_not_require_network(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = TiktokenTokenCounter("cl100k_base")

    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_network)
    assert counter.count("offline token counting") == len(counter.encode("offline token counting"))
