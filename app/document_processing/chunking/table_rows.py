"""TABLE_ROW chunks after the page-text chunks (DEC-034, DOCUMENT_TABLE_ROW_CHUNKING_ENABLED)."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable, Sequence

from app.document_processing.chunking.models import ChunkingResult, TextChunk
from app.document_processing.models import ExtractionResult, TableRow


def _fold(text: str) -> str:
    return " ".join(text.casefold().split())


def parent_index(
    chunks: Sequence[TextChunk], page_number: int, rows: Sequence[TableRow]
) -> int | None:
    """The TEXT chunk of the page that holds the most of the table's cells; the first on a tie,
    None when the page has no text chunk."""
    cells = {_fold(cell) for row in rows for cell in row.cells if len(cell.strip()) >= 2}
    best, best_hits = None, -1
    for chunk in chunks:
        if chunk.kind != "TEXT" or page_number not in chunk.page_numbers:
            continue
        text = _fold(chunk.text)
        hits = sum(cell in text for cell in cells)
        if hits > best_hits:
            best, best_hits = chunk.chunk_index, hits
    return best


def with_table_row_chunks(
    result: ChunkingResult, extraction: ExtractionResult, count: Callable[[str], int]
) -> ChunkingResult:
    """The chunking result with one TABLE_ROW chunk per extracted table row appended; unchanged
    when no page has table rows."""
    tables: dict[tuple[int, int], list[TableRow]] = defaultdict(list)
    for page in extraction.pages:
        for row in page.table_rows:
            tables[(page.page_number, row.table)].append(row)
    if not tables:
        return result
    chunks = list(result.chunks)
    for (page_number, _), rows in sorted(tables.items()):
        parent = parent_index(result.chunks, page_number, rows)
        for row in rows:
            chunks.append(
                TextChunk(
                    chunk_index=len(chunks),
                    text=row.text,
                    token_count=max(1, count(row.text)),
                    character_count=len(row.text),
                    page_numbers=(page_number,),
                    start_page=page_number,
                    end_page=page_number,
                    overlap_token_count=0,
                    content_sha256=hashlib.sha256(row.text.encode("utf-8")).hexdigest(),
                    kind="TABLE_ROW",
                    search_text=row.search_text,
                    parent_index=parent,
                )
            )
    pages = tuple(sorted({page for chunk in chunks for page in chunk.page_numbers}))
    return ChunkingResult(
        chunks=tuple(chunks),
        chunk_count=len(chunks),
        total_tokens=sum(chunk.token_count for chunk in chunks),
        total_unique_source_pages=len(pages),
        source_page_numbers=pages,
    )
