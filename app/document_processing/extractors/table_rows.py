"""One text unit per table row (DOCUMENT_TABLE_ROW_CHUNKING_ENABLED, docs/design/table-chunking.md).

A page with no data table keeps the extractor's own text, byte for byte. On a page with one, the
lines inside each data table are replaced, at the table's place in reading order, by one paragraph
per body row:

    <table title> | <column 1>: <cell 1>; <column 2>: <cell 2>; ...

so every row carries its title and column names into whatever chunk it lands in, and a chunk
boundary can only fall between rows. A data table has at least 2 columns and 2 body rows; boxes,
notes and page headers or footers are left as they are.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# The title is the nearest line above the table, outside every table region, if it is this close
# (PDF points); it is cut to this many characters.
TITLE_MAX_GAP = 60.0
TITLE_MAX_CHARS = 160
# A column name is a short label: longer, or ending in a full stop, it is data.
HEADER_MAX_CHARS = 60
# A table may continue on the next page when it ends below this share of the page height and no
# body text follows it above the bottom margin.
CONTINUE_FROM = 0.75
BOTTOM_MARGIN = 0.92


@dataclass(frozen=True, slots=True)
class TableContext:
    """What a table that continues on the next page carries over."""

    title: str
    columns: tuple[str, ...]


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def is_data_table(table: Any) -> bool:
    """At least 2 columns and 3 rows: 2 body rows even when the first row is a header."""
    return table.col_count >= 2 and table.row_count >= 3


def _bold(page: Any, box: Any) -> bool | None:
    """Whether all text in a cell is bold; None for an empty or merged-away cell."""
    if box is None:
        return None
    spans = [
        span
        for block in page.get_text("dict", clip=box)["blocks"]
        if block.get("type") == 0
        for line in block["lines"]
        for span in line["spans"]
        if span["text"].strip()
    ]
    if not spans:
        return None
    return all(span["flags"] & 16 or "bold" in span["font"].lower() for span in spans)


def has_header(page: Any, table: Any, rows: list[list[str]]) -> bool:
    """The table's first row names the columns: at least two distinct short labels, every cell
    bold, and the next row not all bold. PyMuPDF's own header guess is not used: it may take the
    title line above the table as an external header."""
    named = [name for name in rows[0] if name]
    if len(named) < 2 or len(set(named)) < len(named):
        return False
    if any(len(name) > HEADER_MAX_CHARS or name.endswith(".") for name in named):
        return False
    first = [_bold(page, box) for box in table.rows[0].cells]
    second = [_bold(page, box) for box in table.rows[1].cells]
    return all(value is not False for value in first) and False in second


def filled_rows(table: Any) -> list[list[str]]:
    """Cell texts with merged cells resolved. A cell covered by a merged cell from above takes its
    text (vertical merge); one covered from its left stays empty, so the value is written once
    (horizontal merge)."""
    texts = table.extract()
    boxes = [row.cells for row in table.rows]
    filled: list[list[str]] = []
    for i, row in enumerate(texts):
        out = []
        for j, value in enumerate(row):
            if boxes[i][j] is not None or i == 0:
                out.append(_clean(value))
                continue
            row_mid = (table.rows[i].bbox[1] + table.rows[i].bbox[3]) / 2
            above = next((k for k in range(i - 1, -1, -1) if boxes[k][j] is not None), None)
            spans_down = above is not None and boxes[above][j][3] >= row_mid
            out.append(filled[above][j] if spans_down else "")
        filled.append(out)
    return filled


def header_and_body(
    page: Any, table: Any, rows: list[list[str]]
) -> tuple[list[str], list[list[str]]]:
    """Column names (empty without a header) and body rows. A header cell left empty by a merge
    takes the name to its left."""
    if not has_header(page, table, rows):
        return [""] * table.col_count, rows
    names = list(rows[0])
    for j in range(1, len(names)):
        if not names[j]:
            names[j] = names[j - 1]
    return names, rows[1:]


def render_rows(title: str, columns: list[str], body: list[list[str]]) -> list[str]:
    """One line per body row with text. Without column names (a key-value table) a row is written
    as 'first cell: other cells'."""
    lines = []
    for row in body:
        values = [value for value in row if value]
        if not values:
            continue
        if any(columns):
            text = "; ".join(
                f"{name}: {value}" if name else value
                for name, value in zip(columns, row, strict=False)
                if value
            )
        else:
            text = f"{values[0]}: {'; '.join(values[1:])}" if len(values) > 1 else values[0]
        lines.append(f"{title} | {text}" if title else text)
    return lines


def _inside(bbox: Any, rect: Any) -> bool:
    x, y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def page_text_with_table_rows(
    page: Any, carried: TableContext | None, *, sort: bool = True
) -> tuple[str, TableContext | None]:
    """The page's text with each data table written row by row, and the context of a data table
    that may continue on the next page (None when the page does not end in one)."""
    regions = page.find_tables().tables
    tables = sorted((t for t in regions if is_data_table(t)), key=lambda t: t.bbox[1])
    if not tables:
        return page.get_text("text", sort=sort) or "", None
    lines = [
        (line["bbox"], "".join(span["text"] for span in line["spans"]))
        for block in page.get_text("dict", sort=sort)["blocks"]
        if block.get("type") == 0
        for line in block["lines"]
    ]
    outside = [(b, s) for b, s in lines if not any(_inside(b, t.bbox) for t in regions)]
    rendered: dict[int, str] = {}
    context = None
    for n, table in enumerate(tables):
        above = [(b, s) for b, s in outside if b[3] <= table.bbox[1] + 1 and s.strip()]
        title = ""
        if above and table.bbox[1] - above[-1][0][3] <= TITLE_MAX_GAP:
            title = _clean(above[-1][1])[:TITLE_MAX_CHARS]
        rows = filled_rows(table)
        columns, body = header_and_body(page, table, rows)
        repeated = columns == list(carried.columns) if carried else False
        if (
            n == 0
            and not title
            and carried
            and len(carried.columns) == len(columns)
            and (repeated or not any(columns))
        ):
            # The table from the previous page goes on, with or without its header repeated.
            title, columns = carried.title, list(carried.columns)
        rendered[n] = "\n\n" + "\n\n".join(render_rows(title, columns, body)) + "\n\n"
        text_after = any(
            b[1] >= table.bbox[3] and b[1] < page.rect.height * BOTTOM_MARGIN and s.strip()
            for b, s in outside
        )
        low = table.bbox[3] >= page.rect.height * CONTINUE_FROM
        context = TableContext(title, tuple(columns)) if low and not text_after else None
    pieces: list[str] = []
    for bbox, text in lines:
        owner = next((n for n, t in enumerate(tables) if _inside(bbox, t.bbox)), None)
        for n in [n for n in rendered if n == owner or tables[n].bbox[3] <= bbox[1]]:
            pieces.append(rendered.pop(n))  # a table goes where its first line was
        if owner is None:
            pieces.append(text + "\n")
    pieces += rendered.values()
    return "".join(pieces), context
