"""RAG_UNITLESS_EVIDENCE_NUMBERS_ENABLED: the simple mode number check against bare table cells
and words that are not units. Made-up text only."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.retrieval.question_analysis import fold_text
from app.services import claim_evidence_validation_service as validation

# A table whose unit is given once, above it; its cells are bare numbers.
TABLE = (
    "2. Bang muc phi\nDon vi: trieu dong/thang, ap dung tu 01/03/2031.\n"
    "Hang Vi du Muc thap Muc giua Muc cao\n"
    "H1 Goi co ban 8 11 14\nH2 Goi tieu chuan 28 38 48\nH3 Goi nang cao 42 56 70\n"
)


def _contradicted(monkeypatch: pytest.MonkeyPatch, answer: str, evidence: str, **flags) -> bool:
    monkeypatch.setattr(validation, "get_settings", lambda: Settings(_env_file=None, **flags))
    with validation.number_normalization():
        return validation._numbers_are_contradicted(fold_text(answer), fold_text(evidence))


ON = {"rag_unitless_evidence_numbers_enabled": True}


def test_off_by_default_and_a_bare_table_cell_still_contradicts(monkeypatch) -> None:
    assert Settings.model_fields["rag_unitless_evidence_numbers_enabled"].default is False
    answer = "Goi H2 co muc thap 28 trieu dong/thang, muc cao 48 trieu dong/thang."
    assert _contradicted(monkeypatch, answer, TABLE)


def test_a_bare_table_cell_supports_the_value_with_the_header_unit(monkeypatch) -> None:
    answer = "Goi H2 co muc thap 28 trieu dong/thang, muc cao 48 trieu dong/thang."
    assert not _contradicted(monkeypatch, answer, TABLE, **ON)


def test_a_word_after_a_number_is_not_its_unit(monkeypatch) -> None:
    evidence = "Ma so noi bo cua chuong trinh: KH-2031-\n B4. Chuong trinh nam 2031 tai ba khu."
    answer = "Chuong trinh nam 2031 co ma noi bo la KH-2031-B4."
    assert _contradicted(monkeypatch, answer, evidence)  # "2031 co" against "2031 tai"
    assert not _contradicted(monkeypatch, answer, evidence, **ON)


@pytest.mark.parametrize(
    ("answer", "evidence"),
    [
        ("Thoi han la 12 ngay.", "Thoi han la 12 thang ke tu ngay ky."),  # another unit
        ("Thoi han la 15 ngay.", "Thoi han la 12 ngay ke tu ngay ky."),  # another value
        ("Muc thap cua goi H2 la 30 trieu dong.", TABLE),  # not in the table
    ],
)
def test_a_value_the_evidence_does_not_give_still_contradicts(
    monkeypatch, answer: str, evidence: str
) -> None:
    assert _contradicted(monkeypatch, answer, evidence, **ON)


def test_one_supported_value_is_enough_as_before(monkeypatch) -> None:
    evidence = "Nghi le gom 1 ngay Tet duong lich, 5 ngay Tet am lich va 2 ngay Quoc khanh."
    answer = "Nghi le gom 1 ngay Tet duong lich, 5 ngay Tet am lich va 9 ngay khac."
    assert not _contradicted(monkeypatch, answer, evidence)
    assert not _contradicted(monkeypatch, answer, evidence, **ON)
