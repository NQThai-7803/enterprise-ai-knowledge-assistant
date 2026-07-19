from __future__ import annotations

from enum import StrEnum


class RetrievalFailureCode(StrEnum):
    EMPTY_RETRIEVAL_QUERY = "EMPTY_RETRIEVAL_QUERY"
    RETRIEVAL_QUERY_TOO_LONG = "RETRIEVAL_QUERY_TOO_LONG"
    INVALID_RETRIEVAL_TOP_K = "INVALID_RETRIEVAL_TOP_K"
    INVALID_RELEVANCE_THRESHOLD = "INVALID_RELEVANCE_THRESHOLD"
    RETRIEVAL_USER_INACTIVE = "RETRIEVAL_USER_INACTIVE"
    QUERY_EMBEDDING_FAILED = "QUERY_EMBEDDING_FAILED"
    QUERY_EMBEDDING_DIMENSION_MISMATCH = "QUERY_EMBEDDING_DIMENSION_MISMATCH"
    SEMANTIC_RETRIEVAL_FAILED = "SEMANTIC_RETRIEVAL_FAILED"
    KEYWORD_RETRIEVAL_FAILED = "KEYWORD_RETRIEVAL_FAILED"
    INVALID_KEYWORD_RANK = "INVALID_KEYWORD_RANK"
    HYBRID_RETRIEVAL_FAILED = "HYBRID_RETRIEVAL_FAILED"
    INVALID_HYBRID_CONFIGURATION = "INVALID_HYBRID_CONFIGURATION"


_SAFE_MESSAGES = {
    RetrievalFailureCode.EMPTY_RETRIEVAL_QUERY: "The retrieval query must not be empty.",
    RetrievalFailureCode.RETRIEVAL_QUERY_TOO_LONG: "The retrieval query is too long.",
    RetrievalFailureCode.INVALID_RETRIEVAL_TOP_K: "The retrieval top-k value is invalid.",
    RetrievalFailureCode.INVALID_RELEVANCE_THRESHOLD: (
        "The retrieval relevance threshold is invalid."
    ),
    RetrievalFailureCode.RETRIEVAL_USER_INACTIVE: "The retrieval user is inactive.",
    RetrievalFailureCode.QUERY_EMBEDDING_FAILED: "The query embedding could not be generated.",
    RetrievalFailureCode.QUERY_EMBEDDING_DIMENSION_MISMATCH: (
        "The query embedding dimensions do not match the configured schema."
    ),
    RetrievalFailureCode.SEMANTIC_RETRIEVAL_FAILED: "Semantic retrieval failed.",
    RetrievalFailureCode.KEYWORD_RETRIEVAL_FAILED: ("The keyword retrieval operation failed."),
    RetrievalFailureCode.INVALID_KEYWORD_RANK: "The keyword rank threshold is invalid.",
    RetrievalFailureCode.HYBRID_RETRIEVAL_FAILED: "The hybrid retrieval operation failed.",
    RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION: (
        "The hybrid retrieval configuration is invalid."
    ),
}


class RetrievalError(Exception):
    code: RetrievalFailureCode
    safe_message: str

    def __init__(
        self,
        code: RetrievalFailureCode,
        safe_message: str | None = None,
    ) -> None:
        self.code = code
        self.safe_message = safe_message or _SAFE_MESSAGES[code]
        super().__init__(self.safe_message)
