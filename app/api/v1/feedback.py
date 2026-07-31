from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import enforce_feedback_rate_limit, get_audit_context, get_current_user
from app.db.session import get_db_session
from app.models import FeedbackRating, User
from app.schemas.common import DEFAULT_PAGE, DataResponse, ListResponse
from app.schemas.feedback import FeedbackRead, FeedbackReportItem, FeedbackUpsertRequest
from app.services.audit_service import AuditContext
from app.services.feedback_service import FeedbackService

router = APIRouter(tags=["Feedback"])


@router.put(
    "/messages/{message_id}/feedback",
    response_model=DataResponse[FeedbackRead],
    status_code=status.HTTP_200_OK,
)
async def upsert_message_feedback(
    request: Request,
    message_id: UUID,
    payload: FeedbackUpsertRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[FeedbackRead]:
    await enforce_feedback_rate_limit(request, current_user)
    feedback = await FeedbackService(session).upsert_feedback(
        message_id=message_id,
        current_user=current_user,
        rating=payload.rating,
        reason=payload.reason,
        audit_context=audit_context,
    )
    return DataResponse[FeedbackRead](data=FeedbackRead.from_row(feedback), meta=None)


@router.get("/feedback", response_model=ListResponse[FeedbackReportItem])
async def list_feedback_report(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    rating: FeedbackRating | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    department_id: UUID | None = None,
    user_id: UUID | None = None,
) -> ListResponse[FeedbackReportItem]:
    report = await FeedbackService(session).list_feedback_report(
        current_user=current_user,
        page=page,
        page_size=page_size,
        rating=rating,
        date_from=date_from,
        date_to=date_to,
        department_id=department_id,
        user_id=user_id,
    )
    return ListResponse[FeedbackReportItem](
        data=[FeedbackReportItem.from_row(row) for row in report.rows],
        meta=report.pagination,
    )
