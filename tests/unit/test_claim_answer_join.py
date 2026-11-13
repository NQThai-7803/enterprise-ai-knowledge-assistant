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
