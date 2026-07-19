from __future__ import annotations

from collections.abc import Sequence

from app.document_processing.chunking.text_units import (
    TextUnit,
    TextUnitKind,
    split_paragraphs,
    split_sentences,
    split_text_unit_to_token_windows,
)


class CharacterTokenCounter:
    def count(self, text: str) -> int:
        return len(self.encode(text))

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(ord(character) for character in text)

    def decode(self, tokens: Sequence[int]) -> str:
        return "".join(chr(token) for token in tokens)


def test_paragraph_split_uses_blank_lines() -> None:
    units = split_paragraphs(1, "First paragraph\n\nSecond paragraph")

    assert [unit.text for unit in units] == ["First paragraph", "Second paragraph"]


def test_paragraph_split_removes_empty_units() -> None:
    units = split_paragraphs(1, "\n\nFirst\n\n\nSecond\n\n")

    assert [unit.text for unit in units] == ["First", "Second"]


def test_paragraph_split_preserves_bullets() -> None:
    units = split_paragraphs(1, "- Item A\n- Item B")

    assert units[0].text == "- Item A\n- Item B"


def test_paragraph_split_preserves_vietnamese() -> None:
    units = split_paragraphs(1, "Điều khoản thanh toán\n\nGiá trị hợp đồng")

    assert units[0].text == "Điều khoản thanh toán"
    assert units[1].text == "Giá trị hợp đồng"


def test_sentence_split_preserves_delimiters() -> None:
    unit = TextUnit(page_number=1, text="Alpha. Beta! Gamma? Delta; Epsilon:")

    assert [sentence.text[-1] for sentence in split_sentences(unit)] == [".", "!", "?", ";", ":"]


def test_sentence_split_preserves_order() -> None:
    unit = TextUnit(page_number=1, text="First sentence. Second sentence. Third sentence.")

    assert [sentence.text for sentence in split_sentences(unit)] == [
        "First sentence.",
        "Second sentence.",
        "Third sentence.",
    ]


def test_sentence_split_handles_text_without_punctuation() -> None:
    unit = TextUnit(page_number=1, text="No punctuation in this text")

    assert [sentence.text for sentence in split_sentences(unit)] == ["No punctuation in this text"]


def test_long_unit_falls_back_to_token_windows() -> None:
    unit = TextUnit(page_number=1, text="abcdefghij")

    windows = split_text_unit_to_token_windows(
        unit,
        CharacterTokenCounter(),
        max_tokens=4,
        overlap_tokens=1,
    )

    assert len(windows) > 1
    assert all(window.kind == TextUnitKind.TOKEN_WINDOW for window in windows)


def test_token_window_makes_progress() -> None:
    unit = TextUnit(page_number=1, text="abcdefghijklmnop")

    windows = split_text_unit_to_token_windows(
        unit,
        CharacterTokenCounter(),
        max_tokens=5,
        overlap_tokens=2,
    )

    assert [window.text for window in windows]
    assert len({window.text for window in windows}) == len(windows)


def test_token_window_never_exceeds_max_tokens() -> None:
    counter = CharacterTokenCounter()
    unit = TextUnit(page_number=1, text="a" * 25)

    windows = split_text_unit_to_token_windows(
        unit,
        counter,
        max_tokens=6,
        overlap_tokens=2,
    )

    assert windows
    assert all(counter.count(window.text) <= 6 for window in windows)
