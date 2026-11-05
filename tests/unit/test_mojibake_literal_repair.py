"""Behaviour of the runtime literals that were stored as mojibake (UTF-8 read as cp1252).

Bullets (U+2022, U+F0B7) and the dong sign (U+20AB) are written as escapes on purpose.
"""

from __future__ import annotations

import json
from uuid import UUID

from app.citations.models import PromptSource, PromptSourceRegistry
from app.models import CitationSourceType
from app.retrieval.question_analysis import analyze_question, fold_text
from app.retrieval.reranker import _value_alignment_score
from app.retrieval.structured import _LIST_MARKER_RE, value_units_for_analysis
from app.services.claim_evidence_validation_service import _policy_evidence_segments
from app.services.grounded_answer_service import (
    _structured_attendance_policy_answer,
    _structured_grouped_duration_answer,
    _structured_named_topic_answer,
    _structured_policy_clause_repair_generation,
)

BULLET = "\u2022"
SYMBOL_BULLET = "\uf0b7"
DONG_SIGN = "\u20ab"


def _source(text: str) -> PromptSourceRegistry:
    return PromptSourceRegistry(
        sources=(
            PromptSource(
                marker="[SOURCE_1]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Policy",
                text=text,
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                hybrid_score=1.0,
                chunk_id=UUID(int=1),
                document_id=UUID(int=2),
            ),
        )
    )


def test_line_starting_with_real_bullet_is_a_list_item() -> None:
    assert _LIST_MARKER_RE.match(f"{BULLET} Nghỉ phép năm") is not None
    assert _LIST_MARKER_RE.sub("", f"{BULLET} Nghỉ phép năm") == "Nghỉ phép năm"


def test_word_starting_with_a_circumflex_is_not_a_list_marker() -> None:
    assert _LIST_MARKER_RE.match("\u00e2 n\u0103m") is None
    assert _LIST_MARKER_RE.sub("", "\u00e2m l\u1ecbch") == "\u00e2m l\u1ecbch"


def test_amount_units_include_the_dong_sign() -> None:
    analysis = analyze_question("Phụ cấp ăn trưa mỗi tháng là bao nhiêu tiền?")

    assert analysis.asks_for_amount
    assert DONG_SIGN in value_units_for_analysis(analysis)


def test_dong_sign_amount_scores_like_a_vnd_amount() -> None:
    analysis = analyze_question("Phụ cấp ăn trưa mỗi tháng là bao nhiêu tiền?")
    terms = ("phu cap",)

    dong = _value_alignment_score(
        fold_text(f"Phụ cấp ăn trưa 730.000 {DONG_SIGN} mỗi tháng"), analysis=analysis, terms=terms
    )
    vnd = _value_alignment_score(
        fold_text("Phụ cấp ăn trưa 730.000 vnd mỗi tháng"), analysis=analysis, terms=terms
    )

    assert dong == vnd
    assert dong > 0


def test_policy_segments_do_not_split_inside_words() -> None:
    clause = "Nhân viên cấp cao cần báo trước 45 ngày."

    assert _policy_evidence_segments(clause) == (clause,)


def test_policy_segments_split_and_strip_real_bullets() -> None:
    evidence = (
        f"{BULLET} Nhân viên mới được 12 ngày. "
        f"{SYMBOL_BULLET} Nhân viên cấp cao được 15 ngày. {BULLET}"
    )

    assert _policy_evidence_segments(evidence) == (
        "Nhân viên mới được 12 ngày.",
        "Nhân viên cấp cao được 15 ngày.",
    )


def test_attendance_answer_strips_real_bullets_at_both_ends() -> None:
    answer = _structured_attendance_policy_answer(
        question="Ngày mai làm remote thì đăng ký trước mấy giờ?",
        source_registry=_source(
            f"{BULLET} Đăng ký lịch remote trước 14:30 của ngày làm việc liền trước. "
            f"{SYMBOL_BULLET}"
        ),
    )

    assert answer is not None
    assert BULLET not in answer[0]
    assert SYMBOL_BULLET not in answer[0]
    assert answer[0].endswith("liền trước.")


def test_named_topic_answer_strips_real_bullets_at_both_ends() -> None:
    answer = _structured_named_topic_answer(
        question="Làm việc hybrid được quy định như thế nào?",
        source_registry=_source(
            f"{BULLET} Làm việc hybrid được áp dụng tối đa 2 ngày mỗi tuần. {SYMBOL_BULLET}"
        ),
    )

    assert answer is not None
    assert answer[0] == "Làm việc hybrid được áp dụng tối đa 2 ngày mỗi tuần."


def test_policy_clause_repair_strips_real_bullets_at_both_ends() -> None:
    generation = _structured_policy_clause_repair_generation(
        question="Thoi gian xu ly su co on-call duoc ghi nhan the nao?",
        source_registry=_source(
            f"{BULLET} Phu cap on-call bu cho trang thai san sang theo lich; "
            "thoi gian thuc te xu ly ticket/su co duoc ghi nhan rieng de "
            f"danh gia OT hoac che do khac theo chinh sach. {BULLET}"
        ),
    )

    assert generation is not None
    answer = json.loads(generation.content)["answer"]
    assert BULLET not in answer
    assert "duoc ghi nhan rieng" in answer.casefold()


def _grouped_leave_answer(text: str) -> str:
    answer = _structured_grouped_duration_answer(
        question="Nghỉ phép năm được bao nhiêu ngày?", source_registry=_source(text)
    )
    assert answer is not None
    return answer[0]


def test_grouped_annual_leave_label_before_value_is_shown_in_vietnamese() -> None:
    text = _grouped_leave_answer(
        "Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm:\n"
        "16 ngày làm việc\n"
        "Lao động trong điều kiện bình thường: 12 ngày làm việc"
    )

    assert text == (
        "Mức nghỉ hằng năm theo đối tượng là "
        "16 ngày cho công việc đặc biệt nặng nhọc, độc hại, nguy hiểm; "
        "12 ngày cho công việc trong điều kiện bình thường."
    )


def test_grouped_annual_leave_keeps_three_categories_when_a_value_wraps_after_its_label() -> None:
    text = _grouped_leave_answer(
        "Công việc trong điều kiện bình thường 12 ngày làm việc/năm.\n"
        "Người chưa thành niên, người khuyết tật hoặc công việc nặng nhọc, độc hại, nguy hiểm\n"
        "14 ngày\n"
        "16 ngày Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm."
    )

    assert text == (
        "Mức nghỉ hằng năm theo đối tượng là "
        "12 ngày cho công việc trong điều kiện bình thường; "
        "14 ngày cho người chưa thành niên, người khuyết tật hoặc "
        "công việc nặng nhọc, độc hại, nguy hiểm; "
        "16 ngày cho công việc đặc biệt nặng nhọc, độc hại, nguy hiểm."
    )


def test_grouped_annual_leave_binds_values_that_precede_their_labels() -> None:
    text = _grouped_leave_answer(
        "Mức nghỉ Đối tượng áp dụng\n"
        "12 ngày\n"
        "Công việc trong điều kiện bình thường\n"
        "14 ngày\n"
        "Người chưa thành niên hoặc công việc nặng nhọc, độc hại\n"
        "16 ngày\n"
        "Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm"
    )

    assert text == (
        "Mức nghỉ hằng năm theo đối tượng là "
        "12 ngày cho công việc trong điều kiện bình thường; "
        "14 ngày cho người chưa thành niên, người khuyết tật hoặc "
        "công việc nặng nhọc, độc hại, nguy hiểm; "
        "16 ngày cho công việc đặc biệt nặng nhọc, độc hại, nguy hiểm."
    )
