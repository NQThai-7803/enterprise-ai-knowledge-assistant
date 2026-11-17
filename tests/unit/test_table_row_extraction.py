"""Table rows as text units (DOCUMENT_TABLE_ROW_CHUNKING_ENABLED), on made-up PDFs."""

from __future__ import annotations

import pymupdf
import pytest

from app.core.config import Settings
from app.document_processing.chunking.page_aware_chunker import PageAwareTokenChunker
from app.document_processing.extraction_router import create_extraction_router
from app.document_processing.extractors.pymupdf_extractor import (
    PyMuPDFTextExtractor,
    create_pdf_text_extractor,
)
from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter

ROW = 22.0


def _table(
    page: pymupdf.Page,
    top: float,
    widths: list[float],
    rows: list[list[str | None]],
    *,
    bold_header: bool = True,
    merge_down: set[tuple[int, int]] = frozenset(),
    merge_right: set[tuple[int, int]] = frozenset(),
) -> float:
    """Draw a ruled table; (r, c) in merge_down joins cell r,c with the cell below, in merge_right
    with the cell to its right (no rule between them). Returns the bottom of the table."""
    left = 50.0
    xs = [left]
    for width in widths:
        xs.append(xs[-1] + width)
    bottom = top + ROW * len(rows)
    for r in range(len(rows) + 1):  # horizontal rules, cut where a cell merges down
        y = top + r * ROW
        for c in range(len(widths)):
            if r == 0 or r == len(rows) or (r - 1, c) not in merge_down:
                page.draw_line((xs[c], y), (xs[c + 1], y))
    for c in range(len(widths) + 1):  # vertical rules, cut where a cell merges right
        for r in range(len(rows)):
            if c == 0 or c == len(widths) or (r, c - 1) not in merge_right:
                page.draw_line((xs[c], top + r * ROW), (xs[c], top + (r + 1) * ROW))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text:
                font = "hebo" if r == 0 and bold_header else "helv"
                page.insert_text((xs[c] + 3, top + r * ROW + 15), text, fontname=font, fontsize=9)
    return bottom


def _pdf(build) -> bytes:
    document = pymupdf.open()
    build(document)
    data = document.tobytes()
    document.close()
    return data


def _text(data: bytes, table_rows: bool = True) -> list[str]:
    extractor = PyMuPDFTextExtractor(max_pages=50, min_usable_characters=0, table_rows=table_rows)
    return [page.text for page in extractor.extract(data).pages]


HEADER = ["Plan", "Limit per year", "Main condition"]
BODY = [
    ["Inpatient", "150 million", "After probation"],
    ["Outpatient", "12 million", "At most 1.2 million per visit"],
    ["Dental", "3 million", "Basic care"],
]


def _benefits_page(document: pymupdf.Document) -> None:
    page = document.new_page()
    page.insert_text((50, 60), "Intro text before the table.", fontname="helv", fontsize=10)
    page.insert_text((50, 100), "2. Health insurance plan", fontname="hebo", fontsize=11)
    bottom = _table(page, 110, [120, 120, 220], [HEADER, *BODY])
    page.insert_text(
        (50, bottom + 30), "Closing text after the table.", fontname="helv", fontsize=10
    )


def test_a_page_without_a_data_table_is_unchanged() -> None:
    def build(document: pymupdf.Document) -> None:
        page = document.new_page()
        page.insert_text((50, 60), "Plain policy text.", fontname="helv", fontsize=10)
        page.insert_text((50, 80), "Second line of text.", fontname="helv", fontsize=10)
        _table(page, 120, [200, 200], [["Only one row", "of a box"]], bold_header=False)

    data = _pdf(build)
    assert _text(data, table_rows=True) == _text(data, table_rows=False)


def test_each_row_carries_the_table_title_and_column_names_in_reading_order() -> None:
    text = _text(_pdf(_benefits_page))[0]
    rows = [line for line in text.split("\n") if " | " in line]
    assert rows == [
        "2. Health insurance plan | Plan: Inpatient; Limit per year: 150 million; "
        "Main condition: After probation",
        "2. Health insurance plan | Plan: Outpatient; Limit per year: 12 million; "
        "Main condition: At most 1.2 million per visit",
        "2. Health insurance plan | Plan: Dental; Limit per year: 3 million; "
        "Main condition: Basic care",
    ]
    order = [
        text.index(s) for s in ("Intro text", "2. Health insurance plan\n", rows[0], "Closing")
    ]
    assert order == sorted(order)
    assert "\n\n" + rows[0] + "\n\n" in text  # each row is its own paragraph


def test_a_table_continued_on_the_next_page_keeps_title_and_columns() -> None:
    def build(document: pymupdf.Document, repeat_header: bool) -> None:
        first = document.new_page()
        first.insert_text((50, 640), "3. Event support", fontname="hebo", fontsize=11)
        _table(first, 650, [150, 150, 150], [["Event", "Amount", "Papers"], *[
            [f"Event {n}", f"{n} million", "Form"] for n in range(1, 7)
        ]])  # fmt: skip
        second = document.new_page()
        rest = [[f"Event {n}", f"{n} million", "Form"] for n in range(7, 10)]
        if repeat_header:
            rest = [["Event", "Amount", "Papers"], *rest]
        _table(second, 60, [150, 150, 150], rest, bold_header=repeat_header)

    for repeat_header in (False, True):
        text = _text(_pdf(lambda document, r=repeat_header: build(document, r)))[1]
        rows = [line for line in text.split("\n") if " | " in line]
        assert rows == [
            f"3. Event support | Event: Event {n}; Amount: {n} million; Papers: Form"
            for n in range(7, 10)
        ]


def test_merged_cells_fill_down_and_are_written_once_across() -> None:
    def build(document: pymupdf.Document) -> None:
        page = document.new_page()
        page.insert_text((50, 100), "Leave by group", fontname="hebo", fontsize=11)
        rows = [
            ["Group", "Case", "Days"],
            ["Family", "Own wedding", "3 days"],
            [None, "Child wedding", "1 day"],
            ["Other", "Unpaid leave by agreement", None],
        ]
        _table(page, 110, [120, 160, 120], rows, merge_down={(1, 0)}, merge_right={(3, 1)})

    rows = [line for line in _text(_pdf(build))[0].split("\n") if " | " in line]
    assert rows == [
        "Leave by group | Group: Family; Case: Own wedding; Days: 3 days",
        "Leave by group | Group: Family; Case: Child wedding; Days: 1 day",
        "Leave by group | Group: Other; Case: Unpaid leave by agreement",
    ]


def test_a_table_without_a_bold_header_is_written_key_value() -> None:
    def build(document: pymupdf.Document) -> None:
        page = document.new_page()
        page.insert_text((50, 100), "Document control", fontname="hebo", fontsize=11)
        rows = [["Code", "HR-007"], ["Version", "1.0"], ["Owner", "People team"]]
        _table(page, 110, [150, 200], rows, bold_header=False)

    rows = [line for line in _text(_pdf(build))[0].split("\n") if " | " in line]
    assert rows == [
        "Document control | Code: HR-007",
        "Document control | Version: 1.0",
        "Document control | Owner: People team",
    ]


def test_a_chunk_boundary_never_cuts_a_row() -> None:
    def build(document: pymupdf.Document) -> None:
        page = document.new_page()
        page.insert_text((50, 60), "Long table", fontname="hebo", fontsize=11)
        rows = [["Item", "Rule", "Note"]] + [
            [f"Item {n}", f"Rule number {n} applies", f"Note {n} for staff"] for n in range(30)
        ]
        _table(page, 70, [100, 200, 160], rows)

    extraction = PyMuPDFTextExtractor(max_pages=5, min_usable_characters=0, table_rows=True)
    result = extraction.extract(_pdf(build))
    chunker = PageAwareTokenChunker(
        token_counter=TiktokenTokenCounter("cl100k_base"),
        target_tokens=120,
        max_tokens=160,
        overlap_tokens=20,
        min_tokens=10,
    )
    chunks = [chunk.text for chunk in chunker.chunk(result).chunks]
    rows = [line for line in result.pages[0].text.split("\n") if " | " in line]
    assert len(rows) == 30 and len(chunks) > 1
    assert all(any(row in chunk for chunk in chunks) for row in rows)


@pytest.mark.parametrize("enabled", [False, True])
def test_the_flag_reaches_both_extractors_and_is_off_by_default(enabled: bool) -> None:
    assert Settings.model_fields["document_table_row_chunking_enabled"].default is False
    settings = Settings(document_table_row_chunking_enabled=enabled)
    assert create_pdf_text_extractor(settings).table_rows is enabled
    assert create_extraction_router(settings).native_pdf_extractor.table_rows is enabled
