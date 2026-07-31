from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEvent, AuditEventType, AuditOutcome, AuditTargetType
from app.models import AuditLog


@dataclass(frozen=True, slots=True)
class AuditReportFilters:
    event_type: AuditEventType | None = None
    outcome: AuditOutcome | None = None
    actor_user_id: UUID | None = None
    target_type: AuditTargetType | None = None
    target_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    request_id: str | None = None
    error_code: str | None = None


async def create(
    session: AsyncSession,
    *,
    event: AuditEvent,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=event.actor_user_id,
        action=event.event_type.value,
        outcome=event.outcome.value,
        entity_type=event.target_type.value if event.target_type is not None else None,
        entity_id=UUID(event.target_id) if event.target_id is not None else None,
        request_id=event.request_id,
        error_code=event.error_code,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=dict(event.metadata),
    )
    session.add(audit_log)
    return audit_log


async def list_report(
    session: AsyncSession,
    *,
    filters: AuditReportFilters,
    limit: int,
    offset: int,
) -> tuple[AuditLog, ...]:
    statement = _apply_report_filters(select(AuditLog), filters=filters).order_by(
        AuditLog.created_at.desc(),
        AuditLog.id.desc(),
    )
    rows = await session.scalars(statement.limit(limit).offset(offset))
    return tuple(rows)


async def count_report(session: AsyncSession, *, filters: AuditReportFilters) -> int:
    statement = _apply_report_filters(
        select(func.count()).select_from(AuditLog),
        filters=filters,
    )
    return int(await session.scalar(statement) or 0)


def _apply_report_filters(stmt: Select[tuple], *, filters: AuditReportFilters) -> Select[tuple]:
    if filters.event_type is not None:
        stmt = stmt.where(AuditLog.action == filters.event_type.value)
    if filters.outcome is not None:
        stmt = stmt.where(AuditLog.outcome == filters.outcome.value)
    if filters.actor_user_id is not None:
        stmt = stmt.where(AuditLog.user_id == filters.actor_user_id)
    if filters.target_type is not None:
        stmt = stmt.where(AuditLog.entity_type == filters.target_type.value)
    if filters.target_id is not None:
        stmt = stmt.where(AuditLog.entity_id == filters.target_id)
    if filters.date_from is not None:
        stmt = stmt.where(AuditLog.created_at >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(AuditLog.created_at <= filters.date_to)
    if filters.request_id is not None:
        stmt = stmt.where(AuditLog.request_id == filters.request_id)
    if filters.error_code is not None:
        stmt = stmt.where(AuditLog.error_code == filters.error_code)
    return stmt
