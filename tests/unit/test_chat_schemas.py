from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatSessionCreate


def test_chat_session_create_accepts_empty_body() -> None:
    payload = ChatSessionCreate()

    assert payload.title is None


def test_chat_session_create_accepts_title() -> None:
    payload = ChatSessionCreate(title="  Quy định nghỉ phép  ")

    assert payload.title == "Quy định nghỉ phép"


def test_chat_session_create_normalizes_blank_title_to_none() -> None:
    payload = ChatSessionCreate(title="   ")

    assert payload.title is None


def test_chat_session_create_rejects_long_title() -> None:
    with pytest.raises(ValidationError):
        ChatSessionCreate(title="x" * 201)


def test_chat_session_create_rejects_user_id() -> None:
    with pytest.raises(ValidationError):
        ChatSessionCreate(user_id="00000000-0000-0000-0000-000000000001")


def test_chat_session_create_rejects_is_archived() -> None:
    with pytest.raises(ValidationError):
        ChatSessionCreate(is_archived=True)


def test_chat_session_create_rejects_messages() -> None:
    with pytest.raises(ValidationError):
        ChatSessionCreate(messages=[])
