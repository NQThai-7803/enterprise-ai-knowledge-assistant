from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from app.models import Feedback, FeedbackRating


def test_feedback_table_registered() -> None:
    assert Feedback.__tablename__ == "feedback"
    assert Feedback.__table__.metadata.tables["feedback"] is Feedback.__table__


def test_feedback_rating_values() -> None:
    assert [rating.value for rating in FeedbackRating] == ["HELPFUL", "NOT_HELPFUL"]


def test_feedback_unique_message_user_constraint() -> None:
    constraints = {
        constraint.name
        for constraint in Feedback.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_feedback_message_user" in constraints


def test_feedback_reason_constraints() -> None:
    constraints = {
        constraint.name
        for constraint in Feedback.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_feedback_reason_not_blank" in constraints
    assert "ck_feedback_reason_max_length" in constraints


def test_feedback_message_fk_cascades() -> None:
    fk = _foreign_key_for_column("message_id")
    assert fk.referred_table.name == "chat_messages"
    assert fk.ondelete == "CASCADE"


def test_feedback_user_fk_restricts() -> None:
    fk = _foreign_key_for_column("user_id")
    assert fk.referred_table.name == "users"
    assert fk.ondelete == "RESTRICT"


def test_feedback_indexes_declared() -> None:
    indexes = {index.name: index for index in Feedback.__table__.indexes}
    assert _index_columns(indexes["ix_feedback_user_updated"]) == ("user_id", "updated_at")
    assert _index_columns(indexes["ix_feedback_rating_updated"]) == ("rating", "updated_at")
    assert _index_columns(indexes["ix_feedback_message"]) == ("message_id",)


def _foreign_key_for_column(column_name: str) -> ForeignKeyConstraint:
    for constraint in Feedback.__table__.constraints:
        if isinstance(constraint, ForeignKeyConstraint) and column_name in constraint.columns:
            return constraint
    raise AssertionError(f"Missing FK for {column_name}")


def _index_columns(index: Index) -> tuple[str, ...]:
    return tuple(column.name for column in index.columns)
