from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import FeedbackRating
from app.repositories.feedback_repository import FeedbackReportRow, FeedbackRow


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
