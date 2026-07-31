from __future__ import annotations

from sqlalchemy import CheckConstraint, Index

from app.db.base import Base
from app.models import ChatMessage, ChatMessageRole, ChatSession


def test_chat_session_table_registered() -> None:
    assert ChatSession.__tablename__ == "chat_sessions"
    assert "chat_sessions" in Base.metadata.tables


def test_chat_message_table_registered() -> None:
    assert ChatMessage.__tablename__ == "chat_messages"
    assert "chat_messages" in Base.metadata.tables


def test_chat_message_role_values() -> None:
    assert [role.value for role in ChatMessageRole] == ["USER", "ASSISTANT", "SYSTEM"]


def test_chat_message_content_constraint() -> None:
    constraints = {
        constraint.name
        for constraint in ChatMessage.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_chat_messages_content_not_blank" in constraints


def test_chat_message_metric_constraints() -> None:
    constraints = {
        constraint.name
        for constraint in ChatMessage.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_chat_messages_response_time_non_negative" in constraints
    assert "ck_chat_messages_prompt_tokens_non_negative" in constraints
    assert "ck_chat_messages_completion_tokens_non_negative" in constraints


def test_chat_message_session_cascade() -> None:
    foreign_key = next(iter(ChatMessage.__table__.c.session_id.foreign_keys))

    assert foreign_key.target_fullname == "chat_sessions.id"
    assert foreign_key.ondelete == "CASCADE"


def test_chat_session_defaults_to_not_archived() -> None:
    column = ChatSession.__table__.c.is_archived

    assert column.default is not None
    assert column.default.arg is False
    assert column.server_default is not None


def test_chat_session_user_foreign_key_restricts_delete() -> None:
    foreign_key = next(iter(ChatSession.__table__.c.user_id.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "RESTRICT"


def test_chat_session_indexes_exist() -> None:
    indexes = {index.name for index in ChatSession.__table__.indexes if isinstance(index, Index)}

    assert "ix_chat_sessions_user_updated" in indexes


def test_chat_message_history_index_exists() -> None:
    indexes = {index.name for index in ChatMessage.__table__.indexes if isinstance(index, Index)}

    assert "ix_chat_messages_session_created" in indexes
