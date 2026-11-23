"""DEC-042 direction 1 (RAG_VALIDATOR_V2_ENABLED): each corrected rule lets the right claim
through and still rejects the matching wrong one; without the flag nothing changes.
Invented policy text only."""

from __future__ import annotations

import pytest

from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    _validate_answer_against_evidence,
    simple_validation,
)

SUPPORTED = ClaimEvidenceStatus.SUPPORTED


def status(question: str, answer: str, evidence: str, *, v2: bool) -> ClaimEvidenceStatus:
    with simple_validation(relaxed_rules=True, question_list_segments=True, validator_v2=v2):
        return _validate_answer_against_evidence(
            answer=answer, evidence=evidence, question=question
        )


# (rule, question, evidence, right claim, wrong claim)
CASES = [
    (
        "passive action keeps its link word",
        "Phụ cấp sửa máy dựa trên quãng làm việc nào?",
        "Thời gian chờ linh kiện không được ghi nhận là giờ làm thêm. Thời gian sửa máy thực tế "
        "được ghi nhận để tính phụ cấp sửa máy theo bảng kỹ thuật.",
        "Chỉ thời gian sửa máy thực tế mới được ghi nhận để tính phụ cấp sửa máy.",
        "Thời gian chờ linh kiện được ghi nhận là giờ làm thêm.",
    ),
    (
        "polarity cues of the sentence the claim rests on",
        "Lỡ quên quẹt thẻ lúc ra về thì xử lý ra sao?",
        "Nhân viên không thể tự xóa bản ghi chấm công trên cổng nội bộ.\n"
        "Quên quẹt thẻ lúc ra về có thể được điều chỉnh khi có xác nhận của quản lý trực tiếp.",
        "Trường hợp quên quẹt thẻ lúc ra về có thể được yêu cầu điều chỉnh khi có xác nhận của "
        "quản lý trực tiếp.",
        "Quên quẹt thẻ lúc ra về thì không thể được điều chỉnh khi có xác nhận của quản lý "
        "trực tiếp.",
    ),
    (
        "a function word after a number is not its unit",
        "Kỳ rà soát năng lực nội bộ diễn ra vào tháng nào?",
        "Lịch nhân sự nội bộ\nRà soát năng lực nội bộ Tháng 03 - 04\nHọp hội đồng Tháng 05",
        "Kỳ rà soát năng lực nội bộ diễn ra trong Tháng 03 - 04 của năm.",
        "Kỳ rà soát năng lực nội bộ diễn ra trong Tháng 07 - 08 của năm.",
    ),
    (
        "the recipient of a disclosure is not its scope",
        "Nhân viên có được trao đổi điểm thưởng của bản thân với đồng nghiệp khác không?",
        "Chính sách không cấm người lao động trao đổi điểm thưởng của bản thân khi thực hiện "
        "quyền hợp pháp. Không được truy cập điểm thưởng của người lao động khác.",
        "Có, nhân viên được trao đổi điểm thưởng của bản thân.",
        "Không, nhân viên không được trao đổi điểm thưởng của bản thân.",
    ),
    (
        "a fixed benefit row grants the benefit",
        "Con của nhân viên vào lớp một thì công ty có tiền hỗ trợ không?",
        "Bảng mức hỗ trợ phúc lợi nội bộ\nCon nhân viên vào lớp một 1.500.000 đ\n"
        "Sinh nhật nhân viên 500.000 đ",
        "Có, con nhân viên vào lớp một được hỗ trợ 1.500.000 đ.",
        "Có, con nhân viên vào lớp một được hỗ trợ 2.500.000 đ.",
    ),
    (
        "short Vietnamese syllables count as grounding",
        "Làm ca đêm có phải giữ giờ họp cố định không?",
        "Quy định làm việc ca đêm\nCa đêm: Giữ nguyên giờ họp cố định và lịch trực như ca ngày.",
        "Có, khi làm ca đêm vẫn phải giữ giờ họp cố định.",
        "Không, khi làm ca đêm không phải giữ giờ họp cố định.",
    ),
]


@pytest.mark.parametrize(("rule", "question", "evidence", "right", "wrong"), CASES)
def test_v2_passes_the_right_claim_and_rejects_the_wrong_one(
    rule: str, question: str, evidence: str, right: str, wrong: str
) -> None:
    assert status(question, right, evidence, v2=True) == SUPPORTED, rule
    assert status(question, wrong, evidence, v2=True) != SUPPORTED, rule


@pytest.mark.parametrize(("rule", "question", "evidence", "right", "wrong"), CASES)
def test_without_the_flag_the_old_rule_still_decides(
    rule: str, question: str, evidence: str, right: str, wrong: str
) -> None:
    # the misfire the flag corrects
    assert status(question, right, evidence, v2=False) != SUPPORTED, rule


def test_v2_also_rejects_a_reversal_the_old_cue_check_let_through() -> None:
    # Old: "khong the" in both the chunk and the claim read as agreement, wherever it stood.
    _, question, evidence, _, wrong = CASES[1]
    assert status(question, wrong, evidence, v2=False) == SUPPORTED
    assert status(question, wrong, evidence, v2=True) != SUPPORTED


RATES = (
    "Bảng đơn giá tăng ca\n"
    "Tăng ca ngày thường Tối thiểu 150%.\n"
    "Tăng ca dịp nghỉ định kỳ Tối thiểu 200%.\n"
    "Tăng ca dịp lễ Tối thiểu 300%."
)


def test_a_rate_the_cited_source_does_not_state_is_rejected() -> None:
    question = "Xưởng B tăng ca dịp nghỉ định kỳ thì tính mấy phần trăm đơn giá?"
    right = "Tăng ca dịp nghỉ định kỳ hưởng mức tối thiểu 200%."
    wrong = "Tăng ca dịp nghỉ định kỳ hưởng mức tối thiểu 250%."
    assert status(question, right, RATES, v2=True) == SUPPORTED
    assert status(question, wrong, RATES, v2=True) != SUPPORTED


def test_days_and_amounts_are_checked_but_other_numbers_are_not() -> None:
    evidence = "Hoàn tất khóa đào tạo nội bộ: được 03 ngày nghỉ bù có lương sau 2 năm công tác."
    question = "Hoàn tất khóa đào tạo nội bộ được nghỉ bù mấy ngày?"
    assert status(question, "Được 03 ngày nghỉ bù có lương.", evidence, v2=True) == SUPPORTED
    assert status(question, "Được 05 ngày nghỉ bù có lương.", evidence, v2=True) != SUPPORTED
