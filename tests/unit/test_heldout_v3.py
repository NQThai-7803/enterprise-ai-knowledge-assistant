"""Held-out v3 import: a made-up workbook goes to YAML word for word; source references parse."""

from __future__ import annotations

import zipfile
from pathlib import Path

import yaml

from scripts.eval import heldout_v3

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
REL_NS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
HEADER = [
    "#",
    "Nhóm",
    "Câu hỏi",
    "Tài khoản test",
    "Đáp án kỳ vọng",
    "Nguồn trích dẫn kỳ vọng",
    "Kết quả thực tế",
    "Pass/Fail",
    "Ghi chú",
]


def _cell(ref: str, value: str | int) -> str:
    if isinstance(value, int):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = value.replace("&", "&amp;").replace("<", "&lt;")
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _workbook(path: Path, rows: list[list[str | int]]) -> Path:
    body = "".join(
        f'<row r="{n}">'
        + "".join(_cell(f"{chr(65 + i)}{n}", v) for i, v in enumerate(row) if v != "")
        + "</row>"
        for n, row in enumerate(rows, start=1)
    )
    with zipfile.ZipFile(path, "w") as book:
        book.writestr(
            "xl/workbook.xml",
            f"<workbook {NS} {REL_NS}><sheets>"
            '<sheet name="Tổng hợp" sheetId="2" r:id="rId2"/>'
            '<sheet name="Held-out" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        book.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>',
        )
        book.writestr(
            "xl/worksheets/sheet1.xml", f"<worksheet {NS}><sheetData>{body}</sheetData></worksheet>"
        )
        book.writestr("xl/worksheets/sheet2.xml", f"<worksheet {NS}><sheetData/></worksheet>")
    return path


def test_workbook_cells_reach_yaml_word_for_word(tmp_path: Path) -> None:
    question = "Câu hỏi mẫu  có hai dấu cách,\nxuống dòng và dấu cách cuối "
    rows = [
        ["Tiêu đề bộ câu hỏi"],
        [],
        HEADER,
        [1, "Nhóm A", question, "Bất kỳ", "Đáp án: 12 ngày & hơn", "DOC-AB-001 Mục 2", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        [2, "Nhóm B", "Hỏi thứ hai?", "Tài khoản khác", "Không có", "DOC-AB-002", "", "", ""],
    ]
    source = _workbook(tmp_path / "book.xlsx", rows)
    items, filled = heldout_v3.items_from_rows(heldout_v3.read_sheet(source, "Held-out"))
    assert [item["id"] for item in items] == ["HO3-01", "HO3-02"]
    assert items[0]["question"] == question
    assert items[0]["expected_answer"] == "Đáp án: 12 ngày & hơn"
    assert items[1]["test_account"] == "Tài khoản khác"
    assert filled == {"Kết quả thực tế": 0, "Pass/Fail": 0, "Ghi chú": 0}
    loaded = yaml.safe_load(heldout_v3.render_yaml(items, source, "sha"))
    assert loaded["items"] == items
    assert loaded["author"].startswith("a member of the project team")


def test_source_column_splits_into_codes_and_references() -> None:
    segments = heldout_v3.source_segments("DOC-AB-004 Mục 2; DOC-AB-006 Điều 33")
    assert [(code, ref.strip(" ;")) for code, ref in segments] == [
        ("DOC-AB-004", "Mục 2"),
        ("DOC-AB-006", "Điều 33"),
    ]
    assert heldout_v3.source_segments("không có mã") == []


def test_reference_is_found_as_phrase_words_or_not_at_all() -> None:
    doc = "dieu 33 nghi phep nam muc 2 quy dinh chung"
    assert heldout_v3.reference_found(" Điều 33", doc) == "phrase"
    assert heldout_v3.reference_found("Quy định Điều 33", doc) == "words"
    assert heldout_v3.reference_found("Phụ lục 9", doc) == "none"
    assert heldout_v3.reference_found(" ; ", doc) == "empty"


def test_item_check_flags_missing_document_and_account() -> None:
    item = {
        "test_account": "Tài khoản Phòng X",
        "expected_sources": "DOC-AB-001 Mục 2, DOC-AB-009",
        "expected_answer": "Có 12 ngày và 3 lần",
    }
    found = heldout_v3.check_item(item, {"DOC-AB-001": "muc 2 co 12 ngay"})
    assert found["documents_not_in_corpus"] == ["DOC-AB-009"]
    assert found["account"] is None
    assert found["answer_numbers_not_in_cited_documents"] == ["3"]
    assert [r["found"] for r in found["references"]] == ["phrase", "no document"]
