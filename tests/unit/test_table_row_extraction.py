"""Table rows as extra units (DOCUMENT_TABLE_ROW_CHUNKING_ENABLED, DEC-034), on made-up PDFs."""

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


def _pages(data: bytes, table_rows: bool = True):
    extractor = PyMuPDFTextExtractor(max_pages=50, min_usable_characters=0, table_rows=table_rows)
    return extractor.extract(data).pages


def _rows(data: bytes, page: int = 0) -> list[str]:
    return [row.text for row in _pages(data)[page].table_rows]


def _chunker() -> PageAwareTokenChunker:
    return PageAwareTokenChunker(
        token_counter=TiktokenTokenCounter("cl100k_base"),
        target_tokens=120,
        max_tokens=160,
        overlap_tokens=20,
        min_tokens=10,
    )


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


def test_the_page_text_is_the_same_with_the_flag() -> None:
    def build(document: pymupdf.Document) -> None:
        _benefits_page(document)
        page = document.new_page()
        page.insert_text((50, 60), "Plain policy text.", fontname="helv", fontsize=10)

    data = _pdf(build)
    on, off = _pages(data, table_rows=True), _pages(data, table_rows=False)
    assert [page.text for page in on] == [page.text for page in off]
    assert all(not page.table_rows for page in off)
    assert not on[1].table_rows


def test_each_row_carries_title_and_column_names_and_its_cells_as_keyword_text() -> None:
    rows = _pages(_pdf(_benefits_page))[0].table_rows
    assert [row.text for row in rows] == [
        "2. Health insurance plan | Plan: Inpatient; Limit per year: 150 million; "
        "Main condition: After probation",
        "2. Health insurance plan | Plan: Outpatient; Limit per year: 12 million; "
        "Main condition: At most 1.2 million per visit",
        "2. Health insurance plan | Plan: Dental; Limit per year: 3 million; "
        "Main condition: Basic care",
    ]
    assert rows[0].search_text == "Inpatient; 150 million; After probation"  # no labels
    assert {row.table for row in rows} == {0}


def test_a_two_column_table_gets_no_rows() -> None:
    def build(document: pymupdf.Document) -> None:
        page = document.new_page()
        page.insert_text((50, 100), "Document control", fontname="hebo", fontsize=11)
        rows = [["Code", "HR-007"], ["Version", "1.0"], ["Owner", "People team"]]
        _table(page, 110, [150, 200], rows, bold_header=False)

    assert _rows(_pdf(build)) == []


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
        rows = _rows(_pdf(lambda document, r=repeat_header: build(document, r)), page=1)
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

    assert _rows(_pdf(build)) == [
        "Leave by group | Group: Family; Case: Own wedding; Days: 3 days",
        "Leave by group | Group: Family; Case: Child wedding; Days: 1 day",
        "Leave by group | Group: Other; Case: Unpaid leave by agreement",
    ]


def test_row_chunks_follow_the_text_chunks_with_the_table_chunk_as_parent() -> None:
    def build(document: pymupdf.Document) -> None:
        page = document.new_page()
        page.insert_text((50, 60), "Long table", fontname="hebo", fontsize=11)
        rows = [["Item", "Rule", "Note"]] + [
            [f"Item {n}", f"Rule number {n} applies", f"Note {n} for staff"] for n in range(30)
        ]
        _table(page, 70, [100, 200, 160], rows)
        second = document.new_page()
        second.insert_text((50, 60), "Unrelated text on the next page.", fontsize=10)

    data = _pdf(build)
    extractor = PyMuPDFTextExtractor(max_pages=5, min_usable_characters=0, table_rows=True)
    with_rows = _chunker().chunk(extractor.extract(data))
    without = _chunker().chunk(
        PyMuPDFTextExtractor(max_pages=5, min_usable_characters=0).extract(data)
    )
    text_chunks = [c for c in with_rows.chunks if c.kind == "TEXT"]
    row_chunks = [c for c in with_rows.chunks if c.kind == "TABLE_ROW"]
    assert [c.text for c in text_chunks] == [c.text for c in without.chunks]  # page text as is
    assert len(row_chunks) == 30
    assert [c.chunk_index for c in with_rows.chunks] == list(range(len(with_rows.chunks)))
    assert row_chunks[0].chunk_index == len(text_chunks)
    assert {c.page_numbers for c in row_chunks} == {(1,)}
    parent = with_rows.chunks[row_chunks[0].parent_index]
    on_page = [c for c in text_chunks if 1 in c.page_numbers and "Rule number" in c.text]
    assert parent.kind == "TEXT" and len(on_page) > 1  # the table spans text chunks
    assert parent.text.count("Rule number") == max(c.text.count("Rule number") for c in on_page)
    assert {c.parent_index for c in row_chunks} == {row_chunks[0].parent_index}  # one table
    assert row_chunks[3].search_text == "Item 3; Rule number 3 applies; Note 3 for staff"
    assert with_rows.total_tokens == sum(c.token_count for c in with_rows.chunks)


def test_without_rows_the_chunking_result_is_unchanged() -> None:
    off = PyMuPDFTextExtractor(max_pages=5, min_usable_characters=0).extract(_pdf(_benefits_page))
    assert all(c.kind == "TEXT" and c.parent_index is None for c in _chunker().chunk(off).chunks)


@pytest.mark.parametrize("enabled", [False, True])
def test_the_flag_reaches_both_extractors_and_is_off_by_default(enabled: bool) -> None:
    assert Settings.model_fields["document_table_row_chunking_enabled"].default is False
    settings = Settings(document_table_row_chunking_enabled=enabled)
    assert create_pdf_text_extractor(settings).table_rows is enabled
    assert create_extraction_router(settings).native_pdf_extractor.table_rows is enabled
