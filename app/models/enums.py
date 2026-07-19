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


class DocumentAccessScope(StrEnum):
    PRIVATE = "PRIVATE"
    DEPARTMENT = "DEPARTMENT"
    ORGANIZATION = "ORGANIZATION"


class DocumentPermissionLevel(StrEnum):
    VIEW = "VIEW"
    EDIT = "EDIT"
    MANAGE = "MANAGE"
