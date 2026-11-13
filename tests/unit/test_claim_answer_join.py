"""D2: a sub-claim answer that only restates an earlier one is not shown twice."""

from __future__ import annotations

from app.citations.grounded_output import StructuredGroundedClaim
from app.services.grounded_answer_service import _join_claim_answers


def claim(claim_id: str, answer: str, *citations: str) -> StructuredGroundedClaim:
    return StructuredGroundedClaim(claim_id=claim_id, answer=answer, citations=citations)


FIRST = claim(
    "CLAIM_1",
    "Thợ hàn được cấp tối đa 03 bộ đồ bảo hộ, từ bộ thứ tư tự trả 450.000 đồng/bộ.",
    "SOURCE_1",
)


def test_a_reworded_restatement_is_left_out() -> None:
    second = claim("CLAIM_2", "Từ bộ thứ tư thợ hàn tự trả 450.000 đồng/bộ", "SOURCE_1")
    assert _join_claim_answers((FIRST, second), dedupe=True) == FIRST.answer


def test_the_flag_off_keeps_every_answer() -> None:
    second = claim("CLAIM_2", "Từ bộ thứ tư thợ hàn tự trả 450.000 đồng/bộ", "SOURCE_1")
    assert _join_claim_answers((FIRST, second), dedupe=False) == f"{FIRST.answer} {second.answer}"


def test_new_facts_short_answers_and_other_sources_are_kept() -> None:
    new_fact = claim("CLAIM_2", "Đồ bảo hộ được thay mới sau 12 tháng sử dụng.", "SOURCE_1")
    short = claim("CLAIM_3", "Có.", "SOURCE_1")
    other_source = claim("CLAIM_4", "Thợ hàn tự trả 450.000 đồng/bộ từ bộ thứ tư", "SOURCE_2")
    claims = (FIRST, new_fact, short, other_source)
    assert _join_claim_answers(claims, dedupe=True) == " ".join(c.answer for c in claims)


ONE_CLAUSE = claim(
    "CLAIM_1",
    "Thợ hàn được cấp tối đa 03 bộ đồ bảo hộ và từ bộ thứ tư tự trả 450.000 đồng/bộ.",
    "SOURCE_1",
)


def test_one_extra_word_is_still_a_restatement_but_not_a_number_or_negation() -> None:
    reworded = claim("CLAIM_2", "Thợ hàn tự trả tiền 450.000 đồng/bộ từ bộ thứ tư", "SOURCE_1")
    assert _join_claim_answers((ONE_CLAUSE, reworded), dedupe=True) == ONE_CLAUSE.answer
    new_number = claim("CLAIM_2", "Thợ hàn tự trả 450.000 đồng/bộ từ bộ thứ 5", "SOURCE_1")
    negated = claim("CLAIM_3", "Thợ hàn không tự trả 450.000 đồng/bộ từ bộ thứ tư", "SOURCE_1")
    for kept in (new_number, negated):
        assert (
            _join_claim_answers((ONE_CLAUSE, kept), dedupe=True)
            == f"{ONE_CLAUSE.answer} {kept.answer}"
        )


def test_the_same_words_about_another_subject_are_kept() -> None:
    first = claim(
        "CLAIM_1",
        "Phòng Kế toán được nghỉ 02 ngày, phòng Kho được nghỉ 03 ngày khi kiểm kê.",
        "SOURCE_1",
    )
    other_department = claim("CLAIM_2", "Phòng Kế toán được nghỉ 03 ngày khi kiểm kê.", "SOURCE_1")
    other_role = claim(
        "CLAIM_3",
        "Trưởng ca ký biên bản, thủ kho giữ chìa khóa.",
        "SOURCE_1",
    )
    after_role = claim("CLAIM_4", "Thủ kho ký biên bản, trưởng ca giữ chìa khóa.", "SOURCE_1")
    for later in (other_department,):
        assert _join_claim_answers((first, later), dedupe=True) == f"{first.answer} {later.answer}"
    assert (
        _join_claim_answers((other_role, after_role), dedupe=True)
        == f"{other_role.answer} {after_role.answer}"
    )
