"""FIX 3a helpers: the asked phrase of a question, the supporting sentence, refusal phrases.

Every question and text here is invented; none comes from a dev or held-out set.
"""

from __future__ import annotations

import pytest

from app.retrieval.question_analysis import fold_text
from app.services.claim_evidence_validation_service import (
    REFUSAL_PHRASES,
    question_head_in_evidence,
    question_head_phrase,
    supporting_sentence,
)


@pytest.mark.parametrize(
    ("question", "head"),
    [
        ("Nhân viên kho phải mặc loại áo nào?", "áo"),  # classifier dropped
        ("Bảo vệ ca đêm dùng kiểu đèn pin gì?", "đèn pin"),
        ("Khi nghỉ ốm thì ai ký đơn xin nghỉ?", "xin nghỉ"),  # ask clause after "thì"
        ("Nhan vien kho phai mac loai ao nao?", "ao"),
        ("Which badge colour do visitors wear?", "badge colour"),
        ("Xe công ty có được dùng vào cuối tuần không?", None),  # yes/no: nothing to anchor
        ("Chính sách nghỉ phép", None),  # no question word
    ],
)
def test_head_phrase_is_the_end_of_the_phrase_the_question_word_attaches_to(
    question: str, head: str | None
) -> None:
    assert question_head_phrase(question) == head


def test_head_phrase_keeps_diacritics_when_the_question_has_them() -> None:
    question = "Phòng họp được trang bị loại bàn nào?"
    assert question_head_in_evidence(question=question, evidence="Phòng họp có bàn tròn.")
    assert not question_head_in_evidence(question=question, evidence="Phòng họp có bản đồ.")


def test_unaccented_question_is_compared_folded() -> None:
    question = "Phong hop duoc trang bi loai ban nao?"
    assert question_head_in_evidence(question=question, evidence="Phòng họp có bàn tròn.")


def test_question_without_a_head_phrase_never_blocks() -> None:
    assert question_head_in_evidence(question="Có được làm thêm giờ không?", evidence="x")


def test_supporting_sentence_is_the_line_sharing_most_words_with_the_answer() -> None:
    evidence = "Quy định kho.\nNhân viên kho mặc áo phản quang. Kho mở cửa lúc 7 giờ."
    sentence = supporting_sentence(answer="Nhân viên kho mặc áo phản quang.", evidence=evidence)
    assert sentence == "Nhân viên kho mặc áo phản quang."
    assert supporting_sentence(answer="xyz", evidence=evidence) is None


def test_refusal_phrases_come_in_accented_generated_unaccented_and_english_forms() -> None:
    accented = [p for p in REFUSAL_PHRASES if fold_text(p) != p]
    assert {"không được nêu", "chưa quy định", "không có thông tin"} <= set(accented)
    assert all(fold_text(p) in REFUSAL_PHRASES for p in accented)
    assert {"not specified", "does not mention"} <= set(REFUSAL_PHRASES)
