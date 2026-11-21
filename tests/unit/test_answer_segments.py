"""BR-3 segments: the displayed answer cut as s1 cuts a draft. Invented text only."""

from __future__ import annotations

import re

import pytest

from app.chat.models import GroundingStatus
from app.services.grounded_answer_service import answer_segments
from tests.unit.test_simple_answer_mode import GOOD, QUESTION, _ask

UNVERIFIED = "Chưa xác minh được từ tài liệu bạn được phép truy cập: hạn kiểm định xe tải."


def segment(kind: str, text: str, ids: list[int], break_after: str = "none") -> dict:
    return {"kind": kind, "text": text, "citation_ids": ids, "break_after": break_after}


def test_an_answer_without_an_unverified_part_is_one_verified_segment_per_sentence() -> None:
    content = "Xe tải chở được 2.500 kg. [1] Dây cáp được kiểm tra 2 lần mỗi quý. [2]"
    assert answer_segments(content, question=QUESTION, citation_ids=[1, 2]) == [
        segment("verified", "Xe tải chở được 2.500 kg.", [1]),
        segment("verified", "Dây cáp được kiểm tra 2 lần mỗi quý.", [2]),
    ]


def test_a_sentence_naming_an_unverified_part_is_an_unverified_segment() -> None:
    content = f"Xe tải chở được 2.500 kg. [1] {UNVERIFIED}"
    assert answer_segments(content, question=QUESTION, citation_ids=[1]) == [
        segment("verified", "Xe tải chở được 2.500 kg.", [1]),
        segment("unverified", UNVERIFIED, []),
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
    assert segments == [segment("verified", "Xem mục [7] của quy định.", [1])]


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


SEPARATORS = {"none": " ", "line": "\n", "paragraph": "\n\n"}


def rebuilt(segments: list[dict]) -> str:
    """BR-12: the texts joined by their break_after, the last one's ignored."""
    return "".join(
        s["text"] + (SEPARATORS[s["break_after"]] if i < len(segments) - 1 else "")
        for i, s in enumerate(segments)
    )


BULLETS = (
    "Quy trình gồm:\n- Bước 1: nộp đơn. [1]\n- Bước 2: trưởng phòng duyệt. [2]\n\n" + UNVERIFIED
)
PARAGRAPHS = "Xe tải chở được 2.500 kg. Dây cáp kiểm tra mỗi quý. [1]\n\nXe con chở 5 người. [2]"


@pytest.mark.parametrize(
    ("content", "breaks"),
    [
        (BULLETS, ["line", "line", "paragraph", "none"]),  # a bulleted list, then a paragraph
        (PARAGRAPHS, ["none", "paragraph", "none"]),  # two paragraphs, the first of 2 sentences
        ("Xe tải chở được 2.500 kg. [1]", ["none"]),  # one sentence
    ],
)
def test_break_after_rebuilds_the_line_structure_of_the_content(
    content: str, breaks: list[str]
) -> None:
    segments = answer_segments(content, question=QUESTION, citation_ids=[1, 2])
    assert [s["break_after"] for s in segments] == breaks
    assert rebuilt(segments) == re.sub(r" ?\[[12]\]", "", content)


def test_citation_numbers_alone_on_a_line_join_the_line_before() -> None:
    segments = answer_segments(
        "Xe tải chở 2.500 kg.\n[1]\nXe con chở 5 người.", question=QUESTION, citation_ids=[1]
    )
    assert [(s["text"], s["citation_ids"], s["break_after"]) for s in segments] == [
        ("Xe tải chở 2.500 kg.", [1], "paragraph"),
        ("Xe con chở 5 người.", [], "none"),
    ]
