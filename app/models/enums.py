from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class DocumentLifecycleStatus(StrEnum):
    """Authority lifecycle, separate from technical processing readiness."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"  # not an issued document (template, draft); DEC-033


class DocumentChunkKind(StrEnum):
    """TEXT: page text as chunked; TABLE_ROW: one data-table row, extra to it (DEC-034)."""

    TEXT = "TEXT"
    TABLE_ROW = "TABLE_ROW"


class DocumentAccessScope(StrEnum):
    PRIVATE = "PRIVATE"
    DEPARTMENT = "DEPARTMENT"
    ORGANIZATION = "ORGANIZATION"


class DocumentPermissionLevel(StrEnum):
    VIEW = "VIEW"
    EDIT = "EDIT"
    MANAGE = "MANAGE"


class ChatMessageRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class FeedbackRating(StrEnum):
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"


class CitationSourceType(StrEnum):
    INTERNAL = "INTERNAL"
    WEB = "WEB"
