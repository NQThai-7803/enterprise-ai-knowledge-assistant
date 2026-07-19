from __future__ import annotations

from enum import StrEnum


class EmbeddingFailureCode(StrEnum):
    EMPTY_EMBEDDING_INPUT = "EMPTY_EMBEDDING_INPUT"
    EMBEDDING_MODEL_LOAD_FAILED = "EMBEDDING_MODEL_LOAD_FAILED"
    EMBEDDING_DIMENSION_MISMATCH = "EMBEDDING_DIMENSION_MISMATCH"
    EMBEDDING_INVALID_VECTOR = "EMBEDDING_INVALID_VECTOR"
    EMBEDDING_GENERATION_FAILED = "EMBEDDING_GENERATION_FAILED"
    EMBEDDING_BATCH_MISMATCH = "EMBEDDING_BATCH_MISMATCH"


_SAFE_MESSAGES = {
    EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT: "No text is available for embedding.",
    EmbeddingFailureCode.EMBEDDING_MODEL_LOAD_FAILED: "The embedding model could not be loaded.",
    EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH: (
        "The embedding dimensions do not match the configured schema."
    ),
    EmbeddingFailureCode.EMBEDDING_INVALID_VECTOR: "The embedding vector is invalid.",
    EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED: (
        "The embedding vector could not be generated."
    ),
    EmbeddingFailureCode.EMBEDDING_BATCH_MISMATCH: (
        "The embedding batch size does not match the input size."
    ),
}


class EmbeddingError(Exception):
    code: EmbeddingFailureCode
    safe_message: str

    def __init__(
        self,
        code: EmbeddingFailureCode,
        safe_message: str | None = None,
    ) -> None:
        self.code = code
        self.safe_message = safe_message or _SAFE_MESSAGES[code]
        super().__init__(self.safe_message)
