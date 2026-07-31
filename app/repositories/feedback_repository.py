from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    Feedback,
    FeedbackRating,
    User,
    UserRole,
)


@dataclass(frozen=True, slots=True)
class FeedbackRow:
    id: UUID
    message_id: UUID
    user_id: UUID
    rating: FeedbackRating
    reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FeedbackReportFilters:
    rating: FeedbackRating | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    department_id: UUID | None = None
    user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class FeedbackReportRow:
    id: UUID
    message_id: UUID
    user_id: UUID
    department_id: UUID | None
    rating: FeedbackRating
    reason: str | None
    created_at: datetime
    updated_at: datetime


async def get_owned_assistant_message_id(
    session: AsyncSession,
    *,
    message_id: UUID,
    owner_user_id: UUID,
) -> UUID | None:
    stmt = (
        select(ChatMessage.id)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatMessage.id == message_id,
            ChatMessage.role == ChatMessageRole.ASSISTANT,
            ChatSession.user_id == owner_user_id,
        )
        .limit(1)
    )
    return await session.scalar(stmt)


async def upsert_owned_message_feedback(
    session: AsyncSession,
    *,
    message_id: UUID,
    user_id: UUID,
    rating: FeedbackRating,
    reason: str | None,
) -> FeedbackRow:
    stmt = (
        insert(Feedback)
        .values(
            message_id=message_id,
            user_id=user_id,
            rating=rating,
            reason=reason,
        )
        .on_conflict_do_update(
            constraint="uq_feedback_message_user",
            set_={
                "rating": rating,
                "reason": reason,
                "updated_at": func.now(),
            },
        )
        .returning(
            Feedback.id,
            Feedback.message_id,
            Feedback.user_id,
            Feedback.rating,
            Feedback.reason,
            Feedback.created_at,
            Feedback.updated_at,
        )
    )
    row = (await session.execute(stmt)).one()
    return FeedbackRow(
        id=row.id,
        message_id=row.message_id,
        user_id=row.user_id,
        rating=row.rating,
        reason=row.reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_report(
    session: AsyncSession,
    *,
    current_user: User,
    filters: FeedbackReportFilters,
    limit: int,
    offset: int,
) -> tuple[FeedbackReportRow, ...]:
    stmt = _apply_report_scope_and_filters(
        select(
            Feedback.id,
            Feedback.message_id,
            Feedback.user_id,
            User.department_id,
            Feedback.rating,
            Feedback.reason,
            Feedback.created_at,
            Feedback.updated_at,
        ),
        current_user=current_user,
        filters=filters,
    ).order_by(Feedback.updated_at.desc(), Feedback.id.desc())
    stmt = stmt.limit(limit).offset(offset)
    rows = (await session.execute(stmt)).all()
    return tuple(
        FeedbackReportRow(
            id=row.id,
            message_id=row.message_id,
            user_id=row.user_id,
            department_id=row.department_id,
            rating=row.rating,
            reason=row.reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    )


async def count_report(
    session: AsyncSession,
    *,
    current_user: User,
    filters: FeedbackReportFilters,
) -> int:
    stmt = _apply_report_scope_and_filters(
        select(func.count()).select_from(Feedback),
        current_user=current_user,
        filters=filters,
    )
    return int(await session.scalar(stmt) or 0)


def _apply_report_scope_and_filters(
    stmt: Select[tuple],
    *,
    current_user: User,
    filters: FeedbackReportFilters,
) -> Select[tuple]:
    stmt = stmt.join(User, User.id == Feedback.user_id)
    if current_user.role == UserRole.MANAGER:
        stmt = stmt.where(User.department_id == current_user.department_id)

    if filters.rating is not None:
        stmt = stmt.where(Feedback.rating == filters.rating)
    if filters.date_from is not None:
        stmt = stmt.where(Feedback.updated_at >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(Feedback.updated_at <= filters.date_to)
    if filters.department_id is not None:
        stmt = stmt.where(User.department_id == filters.department_id)
    if filters.user_id is not None:
        stmt = stmt.where(Feedback.user_id == filters.user_id)
    return stmt
