from __future__ import annotations

from enum import StrEnum


class CitationFailureCode(StrEnum):
    CITATION_MARKER_MISSING = "CITATION_MARKER_MISSING"
    CITATION_MARKER_UNKNOWN = "CITATION_MARKER_UNKNOWN"
    CITATION_MARKER_INVALID = "CITATION_MARKER_INVALID"
    CITATION_MAPPING_FAILED = "CITATION_MAPPING_FAILED"
    CITATION_PERMISSION_REVALIDATION_FAILED = "CITATION_PERMISSION_REVALIDATION_FAILED"
    CITATION_PERSISTENCE_FAILED = "CITATION_PERSISTENCE_FAILED"


class CitationError(Exception):
    def __init__(self, code: CitationFailureCode) -> None:
        super().__init__(code.value)
        self.code = code


class CitationValidationError(CitationError):
    pass


class CitationMappingError(CitationError):
    pass


class CitationPermissionRevalidationError(CitationError):
    def __init__(self) -> None:
        super().__init__(CitationFailureCode.CITATION_PERMISSION_REVALIDATION_FAILED)
