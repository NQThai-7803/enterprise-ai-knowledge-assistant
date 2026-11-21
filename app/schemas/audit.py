from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from app.audit import AuditOutcome, AuditScalar
from app.audit.metadata import sanitize_stored_audit_metadata_for_response
from app.core.config import get_settings
from app.models import AuditLog, User, UserRole

if TYPE_CHECKING:
    from app.services.display_names import AuditLabels


class AuditLogRead(BaseModel):
    id: UUID
    event_type: str
    outcome: AuditOutcome
    actor_user_id: UUID | None
    target_type: str | None
    target_id: str | None
    request_id: str | None
    error_code: str | None
    metadata: dict[str, AuditScalar] = Field(default_factory=dict)
    created_at: datetime

    @classmethod
    def from_audit_log(cls, audit_log: AuditLog) -> AuditLogRead:
        settings = get_settings()
        return cls(
            id=audit_log.id,
            event_type=audit_log.action,
            outcome=AuditOutcome(audit_log.outcome),
            actor_user_id=audit_log.user_id,
            target_type=audit_log.entity_type,
            target_id=str(audit_log.entity_id) if audit_log.entity_id is not None else None,
            request_id=audit_log.request_id,
            error_code=audit_log.error_code,
            metadata=sanitize_stored_audit_metadata_for_response(
                audit_log.metadata_json,
                max_length=settings.audit_metadata_max_length,
            ),
            created_at=audit_log.created_at,
        )


class AuditLogListResponse(BaseModel):
    items: list[AdminAuditLogRead | AuditLogRead]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class AdminAuditLogRead(AuditLogRead):
    """BR-11: an Admin caller's audit row; both fields required, so an item without them never
    parses as this model."""

    actor_full_name: str | None
    target_label: str | None


def audit_log_view(
    audit_log: AuditLog, *, current_user: User, labels: AuditLabels | None
) -> AuditLogRead:
    """The serializer checks the role again: only an Admin's row carries names and labels."""
    item = AuditLogRead.from_audit_log(audit_log)
    if labels is None or current_user.role != UserRole.ADMIN:
        return item
    return AdminAuditLogRead(
        **item.model_dump(),
        actor_full_name=labels.actor(audit_log.user_id),
        target_label=labels.target(audit_log.entity_type, audit_log.entity_id),
    )
