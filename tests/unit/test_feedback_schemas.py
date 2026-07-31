from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.models import FeedbackRating
from app.schemas.feedback import FeedbackReportItem, FeedbackUpsertRequest


def test_feedback_request_accepts_helpful() -> None:
    payload = FeedbackUpsertRequest(rating="HELPFUL", reason="Useful")
    assert payload.rating == FeedbackRating.HELPFUL
    assert payload.reason == "Useful"


def test_feedback_request_accepts_not_helpful() -> None:
    payload = FeedbackUpsertRequest(rating="NOT_HELPFUL", reason="Missing detail")
    assert payload.rating == FeedbackRating.NOT_HELPFUL


def test_feedback_request_accepts_null_reason() -> None:
    payload = FeedbackUpsertRequest(rating="HELPFUL", reason=None)
    assert payload.reason is None


def test_feedback_request_normalizes_blank_reason_to_none() -> None:
    payload = FeedbackUpsertRequest(rating="HELPFUL", reason="   ")
    assert payload.reason is None


def test_feedback_request_rejects_long_reason() -> None:
    with pytest.raises(ValidationError):
        FeedbackUpsertRequest(rating="HELPFUL", reason="x" * 1001)


def test_feedback_request_rejects_invalid_rating() -> None:
    with pytest.raises(ValidationError):
        FeedbackUpsertRequest(rating="NEUTRAL", reason=None)


@pytest.mark.parametrize("field", ["user_id", "message_id", "created_at", "updated_at", "role"])
def test_feedback_request_rejects_forbidden_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        FeedbackUpsertRequest(rating="HELPFUL", **{field: str(uuid.uuid4())})


def test_feedback_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FeedbackUpsertRequest(rating="HELPFUL", metadata={"x": "y"})


def test_feedback_report_item_does_not_expose_chat_content() -> None:
    fields = set(FeedbackReportItem.model_fields)
    assert "content" not in fields
    assert "assistant_message" not in fields
    assert "citations" not in fields
    assert "retrieval_query" not in fields
