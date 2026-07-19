from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, UserRole
from app.repositories import audit_log_repository

MAX_USER_AGENT_LENGTH = 512
SENSITIVE_METADATA_KEY_FRAGMENTS = (
    "authorization",
    "database_url",
    "hashed_password",
    "password",
    "refresh_token",
    "secret",
    "token_hash",
    "token",
)


class AuditAction(StrEnum):
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_REACTIVATED = "USER_REACTIVATED"
    DEPARTMENT_CREATED = "DEPARTMENT_CREATED"
    DEPARTMENT_UPDATED = "DEPARTMENT_UPDATED"
    DEPARTMENT_DELETED = "DEPARTMENT_DELETED"


@dataclass(frozen=True)
class AuditContext:
    ip_address: str | None = None
    user_agent: str | None = None


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_audit_log(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str | None,
        entity_id: UUID | None,
        context: AuditContext | None,
        metadata: dict[str, Any] | None,
    ) -> AuditLog:
        user_agent = None
        if context is not None and context.user_agent is not None:
            user_agent = context.user_agent[:MAX_USER_AGENT_LENGTH]
        return await audit_log_repository.create(
            self.session,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=context.ip_address if context is not None else None,
            user_agent=user_agent,
            metadata=sanitize_audit_metadata(metadata or {}),
        )


def sanitize_audit_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if _is_sensitive_key(key):
            continue
        sanitized[key] = _to_json_safe(value)
    return sanitized


def _is_sensitive_key(key: str) -> bool:
    normalized_key = key.lower()
    return any(fragment in normalized_key for fragment in SENSITIVE_METADATA_KEY_FRAGMENTS)


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, UserRole):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return sanitize_audit_metadata(value)
    if isinstance(value, list | tuple | set):
        return [_to_json_safe(item) for item in value]
    return value
