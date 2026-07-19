from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def create(
    session: AsyncSession,
    *,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str | None,
    entity_id: UUID | None,
    ip_address: str | None,
    user_agent: str | None,
    metadata: dict[str, Any] | None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
    )
    session.add(audit_log)
    return audit_log
