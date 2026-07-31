from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEventType, AuditTargetType
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ApplicationError,
    FeedbackDateRangeInvalidError,
    FeedbackOperationFailedError,
    FeedbackReasonTooLongError,
    FeedbackReportForbiddenError,
    FeedbackReportScopeUnavailableError,
    FeedbackTargetNotFoundError,
)
from app.models import FeedbackRating, User, UserRole
from app.repositories import feedback_repository
from app.repositories.feedback_repository import (
    FeedbackReportFilters,
    FeedbackReportRow,
    FeedbackRow,
)
from app.schemas.common import PaginationMeta, build_pagination_meta, calculate_offset
from app.services.audit_service import AuditContext, AuditService
from app.services.chat_session_service import resolve_page_size, validate_page


@dataclass(frozen=True, slots=True)
class FeedbackReportData:
    rows: tuple[FeedbackReportRow, ...]
    pagination: PaginationMeta


class FeedbackService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        repository=feedback_repository,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository

    async def upsert_feedback(
        self,
        *,
        message_id: UUID,
        current_user: User,
        rating: FeedbackRating,
        reason: str | None,
        audit_context: AuditContext | None = None,
    ) -> FeedbackRow:
        normalized_reason = normalize_feedback_reason(
            reason,
            max_characters=self.settings.feedback_reason_max_characters,
        )
        try:
            target_id = await self.repository.get_owned_assistant_message_id(
                self.session,
                message_id=message_id,
                owner_user_id=current_user.id,
            )
            if target_id is None:
                raise FeedbackTargetNotFoundError()

            feedback = await self.repository.upsert_owned_message_feedback(
                self.session,
                message_id=target_id,
                user_id=current_user.id,
                rating=rating,
                reason=normalized_reason,
            )
            await AuditService(self.session, settings=self.settings).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.FEEDBACK_UPSERTED,
                target_type=AuditTargetType.FEEDBACK,
                target_id=feedback.id,
                context=audit_context,
                metadata={"rating": feedback.rating},
            )
            await self.session.commit()
        except ApplicationError:
            await self.session.rollback()
            raise
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise FeedbackOperationFailedError() from exc
        return feedback

    async def list_feedback_report(
        self,
        *,
        current_user: User,
        page: int,
        page_size: int | None,
        rating: FeedbackRating | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        department_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> FeedbackReportData:
        if current_user.role == UserRole.STAFF:
            raise FeedbackReportForbiddenError()
        if current_user.role == UserRole.MANAGER and current_user.department_id is None:
            raise FeedbackReportScopeUnavailableError()
        if current_user.role not in {UserRole.ADMIN, UserRole.MANAGER}:
            raise FeedbackReportForbiddenError()

        resolved_page = validate_page(page)
        resolved_page_size = resolve_page_size(
            page_size,
            default=self.settings.feedback_report_page_size,
            maximum=self.settings.feedback_report_max_page_size,
        )
        validate_report_date_range(date_from=date_from, date_to=date_to)
        filters = FeedbackReportFilters(
            rating=rating,
            date_from=date_from,
            date_to=date_to,
            department_id=department_id,
            user_id=user_id,
        )
        total = await self.repository.count_report(
            self.session,
            current_user=current_user,
            filters=filters,
        )
        rows = await self.repository.list_report(
            self.session,
            current_user=current_user,
            filters=filters,
            limit=resolved_page_size,
            offset=calculate_offset(resolved_page, resolved_page_size),
        )
        return FeedbackReportData(
            rows=rows,
            pagination=build_pagination_meta(
                page=resolved_page,
                page_size=resolved_page_size,
                total=total,
            ),
        )


def normalize_feedback_reason(reason: str | None, *, max_characters: int) -> str | None:
    if reason is None:
        return None
    normalized = reason.strip()
    if not normalized:
        return None
    if len(normalized) > max_characters:
        raise FeedbackReasonTooLongError()
    return normalized


def validate_report_date_range(
    *,
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    for value in (date_from, date_to):
        if value is not None and (value.tzinfo is None or value.tzinfo.utcoffset(value) is None):
            raise FeedbackDateRangeInvalidError()
    if date_from is not None and date_to is not None and date_from > date_to:
        raise FeedbackDateRangeInvalidError()
