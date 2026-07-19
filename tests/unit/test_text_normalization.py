from __future__ import annotations

from app.document_processing.normalization import (
    count_usable_characters,
    normalize_extracted_text,
)


def test_normalization_converts_crlf_to_lf() -> None:
    assert normalize_extracted_text("Line 1\r\nLine 2") == "Line 1\nLine 2"


def test_normalization_converts_cr_to_lf() -> None:
    assert normalize_extracted_text("Line 1\rLine 2") == "Line 1\nLine 2"


def test_normalization_removes_null_characters() -> None:
    assert normalize_extracted_text("a\x00b") == "ab"


def test_normalization_applies_unicode_nfc() -> None:
    source = "Cafe\u0301"

    assert normalize_extracted_text(source) == "Caf\u00e9"


def test_normalization_collapses_horizontal_whitespace() -> None:
    assert normalize_extracted_text("A\t  B\u00a0 C") == "A B C"


def test_normalization_preserves_paragraph_breaks() -> None:
    assert normalize_extracted_text("Paragraph 1\n\nParagraph 2") == "Paragraph 1\n\nParagraph 2"


def test_normalization_collapses_excess_blank_lines() -> None:
    assert normalize_extracted_text("A\n\n\n\nB") == "A\n\nB"


def test_normalization_trims_trailing_spaces() -> None:
    assert normalize_extracted_text("A   \nB   ") == "A\nB"


def test_normalization_preserves_vietnamese_diacritics() -> None:
    text = "Ti\u1ebfng Vi\u1ec7t c\u00f3 d\u1ea5u: C\u1ed9ng h\u00f2a x\u00e3 h\u1ed9i."

    assert normalize_extracted_text(text) == text


def test_normalization_preserves_numbers_and_currency() -> None:
    text = "Contract A-102 costs $1,234.56 on 2026-07-16."

    assert normalize_extracted_text(text) == text


def test_normalization_does_not_lowercase_text() -> None:
    assert normalize_extracted_text("ABC Def") == "ABC Def"


def test_count_usable_characters_ignores_whitespace_and_controls() -> None:
    assert count_usable_characters(" A\nB\t\x00C ") == 3
