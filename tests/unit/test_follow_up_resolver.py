from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

from app.chat.follow_up_resolver import (
    is_context_dependent_question,
    resolve_conversation_question,
)
from app.models import ChatMessageRole

CEO_QUESTION = "CEO Nova Digital l\u00e0 ai?"
CEO_ANSWER = "Nguy\u1ec5n Anh Khoa [1]"
WORK_HOURS_QUESTION = "Tuan lam viec tieu chuan bao nhieu gio?"
CTO_FOLLOW_UP = "C\u00f2n CTO th\u00ec sao?"
LEAVE_QUESTION = "Ngh\u1ec9 h\u1eb1ng n\u0103m bao nhi\u00eau ng\u00e0y?"
FIVE_YEAR_FOLLOW_UP = "C\u00f2n sau 5 n\u0103m th\u00ec sao?"
PRONOUN_FOLLOW_UP = "Ng\u01b0\u1eddi n\u00e0y ph\u1ee5 tr\u00e1ch nh\u1eefng g\u00ec?"
REASON_FOLLOW_UP = "T\u1ea1i sao h\u1ecd ch\u1ecdn ng\u01b0\u1eddi \u0111\u00f3?"


def row(index: int, role: ChatMessageRole, content: str):  # noqa: ANN201
    return SimpleNamespace(
        id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
        role=role,
        content=content,
        created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index),
    )


def test_topic_switch_is_standalone_and_does_not_use_ceo_history() -> None:
    resolved = resolve_conversation_question(
        WORK_HOURS_QUESTION,
        messages=(
            row(1, ChatMessageRole.USER, CEO_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, CEO_ANSWER),
        ),
    )

    assert resolved.context_dependent is False
    assert resolved.standalone_question == WORK_HOURS_QUESTION
    assert resolved.source_user_message_ids == ()


def test_entity_follow_up_preserves_new_role_and_organization_without_answer() -> None:
    resolved = resolve_conversation_question(
        CTO_FOLLOW_UP,
        messages=(
            row(1, ChatMessageRole.USER, CEO_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, CEO_ANSWER),
        ),
    )

    assert resolved.context_dependent is True
    assert "CTO" in resolved.standalone_question
    assert "Nova Digital" in resolved.standalone_question
    assert "CEO" not in resolved.standalone_question
    assert "Nguy\u1ec5n Anh Khoa" not in resolved.standalone_question


def test_policy_follow_up_preserves_leave_topic_and_condition_without_injecting_answer() -> None:
    resolved = resolve_conversation_question(
        FIVE_YEAR_FOLLOW_UP,
        messages=(
            row(1, ChatMessageRole.USER, LEAVE_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, "12 ng\u00e0y [1]"),
        ),
    )

    assert resolved.context_dependent is True
    assert "Ngh\u1ec9 h\u1eb1ng n\u0103m" in resolved.standalone_question
    assert "5 n\u0103m" in resolved.standalone_question
    assert "01" not in resolved.standalone_question
    assert "+1" not in resolved.standalone_question
    assert "t\u0103ng th\u00eam" not in resolved.standalone_question


def test_pronoun_reference_uses_previous_user_question_not_assistant_answer() -> None:
    resolved = resolve_conversation_question(
        PRONOUN_FOLLOW_UP,
        messages=(
            row(1, ChatMessageRole.USER, CEO_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, CEO_ANSWER),
        ),
    )

    assert resolved.context_dependent is True
    assert "CEO Nova Digital" in resolved.standalone_question
    assert "ph\u1ee5 tr\u00e1ch" in resolved.standalone_question
    assert "Nguy\u1ec5n Anh Khoa" not in resolved.standalone_question


def test_unsupported_reason_follow_up_is_detected_without_using_answer() -> None:
    resolved = resolve_conversation_question(
        REASON_FOLLOW_UP,
        messages=(
            row(1, ChatMessageRole.USER, CEO_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, CEO_ANSWER),
        ),
    )

    assert is_context_dependent_question(REASON_FOLLOW_UP) is True
    assert "CEO Nova Digital" in resolved.standalone_question
    assert "Nguy\u1ec5n Anh Khoa" not in resolved.standalone_question
