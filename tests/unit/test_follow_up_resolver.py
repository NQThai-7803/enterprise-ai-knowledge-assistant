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


def test_subject_first_quantity_follow_up_retains_requested_attribute() -> None:
    resolved = resolve_conversation_question(
        FIVE_YEAR_FOLLOW_UP,
        messages=(
            row(
                1,
                ChatMessageRole.USER,
                "Nh\u00e2n vi\u00ean Nova Digital c\u00f3 bao nhi\u00eau "
                "ng\u00e0y ph\u00e9p n\u0103m?",
            ),
        ),
    )

    folded = resolved.standalone_question.casefold()
    assert "ng\u00e0y ph\u00e9p n\u0103m" in folded
    assert "nh\u00e2n vi\u00ean nova digital" in folded
    assert "5 n\u0103m" in folded
    assert "c\u00f3 sau" not in folded


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


def test_mode_reference_keeps_new_compound_question_without_replaying_prior_claims() -> None:
    previous = "Lam hybrid thi moi tuan duoc o nha may ngay va phai bao dam an toan gi?"
    current = (
        "Con khoan ho tro hang thang cho che do do la bao nhieu, "
        "va neu toi nam vien thi NovaCare toi da bao nhieu mot nam?"
    )

    resolved = resolve_conversation_question(
        current,
        messages=(row(1, ChatMessageRole.USER, previous),),
    )

    assert resolved.context_dependent is True
    assert "che do hybrid" in resolved.standalone_question.casefold()
    assert "bao dam an toan" not in resolved.standalone_question.casefold()
    assert "NovaCare" in resolved.standalone_question


def test_three_turn_role_follow_up_replays_from_standalone_anchor() -> None:
    resolved = resolve_conversation_question(
        "Còn COO?",
        messages=(
            row(1, ChatMessageRole.USER, CEO_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, CEO_ANSWER),
            row(3, ChatMessageRole.USER, "Còn CTO?"),
            row(4, ChatMessageRole.ASSISTANT, "Lê Thu Hà [1]"),
        ),
    )

    assert "COO" in resolved.standalone_question
    assert "Nova Digital" in resolved.standalone_question
    assert "CEO" not in resolved.standalone_question
    assert "CTO" not in resolved.standalone_question
    assert "Lê Thu Hà" not in resolved.standalone_question


def test_parallel_benefit_rows_replace_prior_requested_row() -> None:
    resolved = resolve_conversation_question(
        "Còn nha khoa?",
        messages=(
            row(1, ChatMessageRole.USER, "NovaCare có hạn mức nội trú bao nhiêu?"),
            row(2, ChatMessageRole.ASSISTANT, "150 triệu đồng [1]"),
            row(3, ChatMessageRole.USER, "Còn ngoại trú?"),
            row(4, ChatMessageRole.ASSISTANT, "12 triệu đồng [1]"),
        ),
    )

    folded = resolved.standalone_question.casefold()
    assert "novacare" in folded
    assert "hạn mức nha khoa" in folded
    assert "bao nhiêu" in folded
    assert "nội trú" not in folded
    assert "ngoại trú" not in folded
    assert "150" not in folded
    assert "12" not in folded


def test_new_condition_replaces_stale_condition_but_keeps_policy_topic() -> None:
    resolved = resolve_conversation_question(
        "Nếu chưa đủ 12 tháng thì sao?",
        messages=(
            row(1, ChatMessageRole.USER, LEAVE_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, "12 ngày [1]"),
            row(3, ChatMessageRole.USER, FIVE_YEAR_FOLLOW_UP),
            row(4, ChatMessageRole.ASSISTANT, "01 ngày [1]"),
        ),
    )

    assert "Nghỉ hằng năm" in resolved.standalone_question
    assert "chưa đủ 12 tháng" in resolved.standalone_question
    assert "5 năm" not in resolved.standalone_question
    assert "01" not in resolved.standalone_question


def test_explicit_multiword_follow_up_becomes_active_topic_for_pronoun() -> None:
    resolved = resolve_conversation_question(
        "Nó có chắc chắn làm tăng lương không?",
        messages=(
            row(1, ChatMessageRole.USER, "Nova Digital trả lương ngày nào?"),
            row(2, ChatMessageRole.ASSISTANT, "Ngày 10 [1]"),
            row(3, ChatMessageRole.USER, "Còn salary review thì sao?"),
            row(4, ChatMessageRole.ASSISTANT, "Salary review hàng năm [1]"),
        ),
    )

    assert "salary review" in resolved.standalone_question.casefold()
    assert "chắc chắn làm tăng lương không" in resolved.standalone_question.casefold()
    assert "trả lương ngày" not in resolved.standalone_question.casefold()
    assert "Ngày 10" not in resolved.standalone_question


def test_two_consecutive_standalone_topic_switches_use_latest_topic_only() -> None:
    resolved = resolve_conversation_question(
        "Còn điện thoại?",
        messages=(
            row(1, ChatMessageRole.USER, CEO_QUESTION),
            row(2, ChatMessageRole.ASSISTANT, CEO_ANSWER),
            row(3, ChatMessageRole.USER, WORK_HOURS_QUESTION),
            row(4, ChatMessageRole.ASSISTANT, "40 giờ [1]"),
            row(5, ChatMessageRole.USER, "Phụ cấp ăn trưa bao nhiêu?"),
            row(6, ChatMessageRole.ASSISTANT, "1 triệu [1]"),
        ),
    )

    folded = resolved.standalone_question.casefold()
    assert "phụ cấp điện thoại" in folded
    assert "ceo" not in folded
    assert "giờ" not in folded
    assert "1 triệu" not in folded
