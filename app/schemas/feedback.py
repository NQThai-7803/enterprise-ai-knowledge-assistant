from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import FeedbackRating
from app.repositories.feedback_repository import FeedbackReportRow, FeedbackRow

if TYPE_CHECKING:
    from app.services.display_names import DisplayNames


class FeedbackUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: FeedbackRating
    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class FeedbackRead(BaseModel):
    id: UUID
    message_id: UUID
    rating: FeedbackRating
    reason: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: FeedbackRow) -> FeedbackRead:
        return cls(
            id=row.id,
            message_id=row.message_id,
            rating=row.rating,
            reason=row.reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class FeedbackReportItem(BaseModel):
    id: UUID
    message_id: UUID
    user_id: UUID
    department_id: UUID | None
    rating: FeedbackRating
    reason: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: FeedbackReportRow) -> FeedbackReportItem:
        return cls(
            id=row.id,
            message_id=row.message_id,
            user_id=row.user_id,
            department_id=row.department_id,
            rating=row.rating,
            reason=row.reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class AdminFeedbackReportItem(FeedbackReportItem):
    """BR-4 option (a): names for an Admin caller only; required so that a Manager's item
    (without these keys) never parses as this model."""

    user_full_name: str | None
    department_name: str | None


def feedback_report_view(
    row: FeedbackReportRow, *, names: DisplayNames | None
) -> FeedbackReportItem:
    item = FeedbackReportItem.from_row(row)
    if names is None:
        return item
    return AdminFeedbackReportItem(
        **item.model_dump(),
        user_full_name=names.user(row.user_id),
        department_name=names.department(row.department_id),
    )
