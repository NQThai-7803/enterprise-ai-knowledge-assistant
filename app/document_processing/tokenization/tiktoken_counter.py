from __future__ import annotations

from collections.abc import Sequence

import tiktoken

from app.document_processing.errors import ChunkingError, ChunkingFailureCode


class TiktokenTokenCounter:
    def __init__(self, encoding_name: str) -> None:
        if not encoding_name.strip():
            raise ChunkingError(ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION)
        self.encoding_name = encoding_name
        try:
            self._encoding = tiktoken.get_encoding(encoding_name)
        except Exception as exc:
            raise ChunkingError(ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION) from exc

    def count(self, text: str) -> int:
        return len(self.encode(text))

    def encode(self, text: str) -> tuple[int, ...]:
        try:
            return tuple(self._encoding.encode(text))
        except Exception as exc:
            raise ChunkingError(ChunkingFailureCode.TOKENIZATION_FAILED) from exc

    def decode(self, tokens: Sequence[int]) -> str:
        try:
            return self._encoding.decode(list(tokens))
        except Exception as exc:
            raise ChunkingError(ChunkingFailureCode.TOKENIZATION_FAILED) from exc
