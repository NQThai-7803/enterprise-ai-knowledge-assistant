"""BR-3 segments: the displayed answer cut as s1 cuts a draft. Invented text only."""

from __future__ import annotations

import pytest

from app.chat.models import GroundingStatus
from app.services.grounded_answer_service import answer_segments
from tests.unit.test_simple_answer_mode import GOOD, QUESTION, _ask

UNVERIFIED = "Chưa xác minh được từ tài liệu bạn được phép truy cập: hạn kiểm định xe tải."


def test_an_answer_without_an_unverified_part_is_one_verified_segment_per_sentence() -> None:
    content = "Xe tải chở được 2.500 kg. [1] Dây cáp được kiểm tra 2 lần mỗi quý. [2]"
    assert answer_segments(content, question=QUESTION, citation_ids=[1, 2]) == [
        {"kind": "verified", "text": "Xe tải chở được 2.500 kg.", "citation_ids": [1]},
        {"kind": "verified", "text": "Dây cáp được kiểm tra 2 lần mỗi quý.", "citation_ids": [2]},
    ]


def test_a_sentence_naming_an_unverified_part_is_an_unverified_segment() -> None:
    content = f"Xe tải chở được 2.500 kg. [1] {UNVERIFIED}"
    assert answer_segments(content, question=QUESTION, citation_ids=[1]) == [
        {"kind": "verified", "text": "Xe tải chở được 2.500 kg.", "citation_ids": [1]},
        {"kind": "unverified", "text": UNVERIFIED, "citation_ids": []},
    ]


@pytest.mark.parametrize(
    ("sentence", "kind"),
    [
        ("Could not be verified from the documents you can access: the inspection date.",
         "unverified"),
        ("Không xác minh được ngày kiểm định.", "unverified"),
        # as in s1: a number the question does not hold may carry a fact, so it stays verified
        ("Chưa xác minh được, nhưng hạn là 30 ngày.", "verified"),
    ],
)  # fmt: skip
def test_the_rule_is_the_one_s1_applies(sentence: str, kind: str) -> None:
    assert answer_segments(sentence, question=QUESTION, citation_ids=[])[0]["kind"] == kind


def test_a_bracketed_number_that_is_no_citation_stays_in_the_text() -> None:
    segments = answer_segments("Xem mục [7] của quy định. [1]", question=QUESTION, citation_ids=[1])
    assert segments == [
        {"kind": "verified", "text": "Xem mục [7] của quy định.", "citation_ids": [1]}
    ]


def test_a_stored_simple_answer_keeps_its_content_and_carries_its_segments() -> None:
    result, _ = _ask(
        f"{GOOD} {UNVERIFIED}",
        rag_simple_absence_sentences_enabled=True,
    )
    assert result.grounding_status == GroundingStatus.ANSWERED
    message = result.assistant_message
    assert UNVERIFIED in message.content
    assert [(s["kind"], s["citation_ids"]) for s in message.segments] == [
        ("verified", [1]),
        ("unverified", []),
    ]


def test_a_refusal_has_no_segments() -> None:
    result, _ = _ask("__NO_ANSWER__")
    assert result.grounding_status == GroundingStatus.NO_ANSWER
    assert result.assistant_message.segments is None
