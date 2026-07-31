from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.audit import AuditEventType, AuditOutcome, AuditTargetType
from app.db.session import get_db_session
from app.models import User
from app.schemas.audit import AuditLogListResponse, AuditLogRead
from app.schemas.common import DEFAULT_PAGE
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit logs"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    event_type: AuditEventType | None = None,
    outcome: AuditOutcome | None = None,
    actor_user_id: UUID | None = None,
    target_type: AuditTargetType | None = None,
    target_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    request_id: Annotated[str | None, Query(max_length=128)] = None,
    error_code: Annotated[str | None, Query(max_length=100)] = None,
) -> AuditLogListResponse:
    report = await AuditService(session).list_audit_report(
        current_user=current_user,
        page=page,
        page_size=page_size,
        event_type=event_type,
        outcome=outcome,
        actor_user_id=actor_user_id,
        target_type=target_type,
        target_id=target_id,
        date_from=date_from,
        date_to=date_to,
        request_id=request_id,
        error_code=error_code,
    )
    return AuditLogListResponse(
        items=[AuditLogRead.from_audit_log(audit_log) for audit_log in report.rows],
        page=report.pagination.page,
        page_size=report.pagination.page_size,
        total=report.pagination.total,
        total_pages=report.pagination.total_pages,
    )
