from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.audit.metadata import AuditScalar, sanitize_audit_metadata


class AuditOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class AuditEventType(StrEnum):
    AUTH_LOGIN_SUCCEEDED = "AUTH_LOGIN_SUCCEEDED"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_STATUS_CHANGED = "USER_STATUS_CHANGED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_REACTIVATED = "USER_REACTIVATED"
    DEPARTMENT_CREATED = "DEPARTMENT_CREATED"
    DEPARTMENT_UPDATED = "DEPARTMENT_UPDATED"
    DEPARTMENT_DELETED = "DEPARTMENT_DELETED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_UPDATED = "DOCUMENT_UPDATED"
    DOCUMENT_DOWNLOADED = "DOCUMENT_DOWNLOADED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    DOCUMENT_PERMISSION_GRANTED = "DOCUMENT_PERMISSION_GRANTED"
    DOCUMENT_PERMISSION_UPDATED = "DOCUMENT_PERMISSION_UPDATED"
    DOCUMENT_PERMISSION_REVOKED = "DOCUMENT_PERMISSION_REVOKED"
    CHAT_SESSION_CREATED = "CHAT_SESSION_CREATED"
    CHAT_SESSION_DELETED = "CHAT_SESSION_DELETED"
    CHAT_QUESTION_SUBMITTED = "CHAT_QUESTION_SUBMITTED"
    CHAT_ANSWER_GENERATED = "CHAT_ANSWER_GENERATED"
    CHAT_NO_ANSWER_GENERATED = "CHAT_NO_ANSWER_GENERATED"
    FEEDBACK_UPSERTED = "FEEDBACK_UPSERTED"


class AuditTargetType(StrEnum):
    USER = "USER"
    DEPARTMENT = "DEPARTMENT"
    DOCUMENT = "DOCUMENT"
    DOCUMENT_PERMISSION = "DOCUMENT_PERMISSION"
    CHAT_SESSION = "CHAT_SESSION"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    FEEDBACK = "FEEDBACK"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: AuditEventType
    outcome: AuditOutcome
    actor_user_id: UUID | None
    target_type: AuditTargetType | None
    target_id: str | None
    request_id: str | None
    error_code: str | None
    metadata: Mapping[str, AuditScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", sanitize_audit_metadata(self.metadata))

    def __repr__(self) -> str:
        metadata_keys = tuple(sorted(self.metadata))
        return (
            "AuditEvent("
            f"event_type={self.event_type.value!r}, "
            f"outcome={self.outcome.value!r}, "
            f"actor_user_id={self.actor_user_id!r}, "
            f"target_type={self.target_type.value if self.target_type is not None else None!r}, "
            f"target_id={self.target_id!r}, "
            f"request_id={self.request_id!r}, "
            f"error_code={self.error_code!r}, "
            f"metadata_keys={metadata_keys!r})"
        )
