from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.document_processing.models import ExtractedPage, ExtractionResult

SECRET_TEXT = "CONFIDENTIAL_TEST_MARKER"


def make_page(page_number: int = 1, text: str = "hello") -> ExtractedPage:
    return ExtractedPage(
        page_number=page_number,
        text=text,
        raw_character_count=len(text),
        normalized_character_count=len(text),
        usable_character_count=len(text.replace(" ", "")),
    )


def make_result() -> ExtractionResult:
    pages = (make_page(1, SECRET_TEXT), make_page(2, ""))
    return ExtractionResult(
        page_count=2,
        pages=pages,
        pages_with_usable_text=1,
        total_raw_characters=sum(page.raw_character_count for page in pages),
        total_normalized_characters=sum(page.normalized_character_count for page in pages),
        total_usable_characters=sum(page.usable_character_count for page in pages),
    )


def test_extracted_page_uses_one_based_page_number() -> None:
    with pytest.raises(ValueError, match="1-based"):
        make_page(0)


def test_extracted_page_is_immutable() -> None:
    page = make_page()

    with pytest.raises(FrozenInstanceError):
        page.page_number = 2  # type: ignore[misc]


def test_extraction_result_is_immutable() -> None:
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.page_count = 3  # type: ignore[misc]


def test_extracted_page_repr_does_not_include_text() -> None:
    assert SECRET_TEXT not in repr(make_page(text=SECRET_TEXT))


def test_extraction_result_repr_does_not_include_page_text() -> None:
    assert SECRET_TEXT not in repr(make_result())


def test_extraction_result_counts_are_consistent() -> None:
    result = make_result()

    assert result.page_count == 2
    assert result.pages_with_usable_text == 1
    assert result.total_raw_characters == sum(page.raw_character_count for page in result.pages)
    assert result.total_normalized_characters == sum(
        page.normalized_character_count for page in result.pages
    )
    assert result.total_usable_characters == sum(
        page.usable_character_count for page in result.pages
    )


def test_extraction_result_rejects_inconsistent_counts() -> None:
    page = make_page()

    with pytest.raises(ValueError, match="total_raw_characters"):
        ExtractionResult(
            page_count=1,
            pages=(page,),
            pages_with_usable_text=1,
            total_raw_characters=0,
            total_normalized_characters=page.normalized_character_count,
            total_usable_characters=page.usable_character_count,
        )
