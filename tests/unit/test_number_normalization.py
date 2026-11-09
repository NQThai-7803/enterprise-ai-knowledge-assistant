"""FIX 3c F: numbers are compared once written one way. Invented texts only."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.retrieval.question_analysis import fold_text
from app.services import claim_evidence_validation_service as validation


@pytest.mark.parametrize(
    ("text", "pairs"),
    [
        ("01 lần/năm", (("1", "lan"),)),
        ("1 lần mỗi năm", (("1", "lan"),)),
        ("1.200.000 đ/người", (("1200000", "dong"),)),
        ("1,2 triệu đồng", (("1200000", "dong"),)),
        ("300 nghìn VND", (("300000", "dong"),)),
        ("2.500 kg", (("2500", "kg"),)),
        ("0,5 kg", (("0.5", "kg"),)),
        ("tỷ lệ 30%", (("30", "%"),)),
        ("5 tỷ đồng", (("5000000000", "dong"),)),
    ],
)
def test_one_value_has_one_written_form(text: str, pairs: tuple[tuple[str, str], ...]) -> None:
    assert validation.canonical_number_unit_pairs(fold_text(text)) == pairs


EVIDENCE = "Bao trì máy bơm 01 lần/năm; chi phí mỗi lần 1.200.000 đ; thời gian 03 giờ."


def _contradicted(answer: str, flag: bool, monkeypatch: pytest.MonkeyPatch) -> bool:
    monkeypatch.setattr(
        validation,
        "get_settings",
        lambda: SimpleNamespace(rag_number_normalization_enabled=flag),
    )
    return validation._numbers_are_contradicted(fold_text(answer), fold_text(EVIDENCE))


@pytest.mark.parametrize(
    "answer", ["Máy bơm được bảo trì 1 lần mỗi năm.", "Mỗi lần tốn 1,2 triệu đồng."]
)
def test_same_value_in_another_form_is_not_a_contradiction_with_the_flag(
    answer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _contradicted(answer, flag=True, monkeypatch=monkeypatch) is False


def test_without_the_flag_a_zero_padded_count_still_reads_as_contradicted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _contradicted("Máy bơm được bảo trì 1 lần mỗi năm.", flag=False, monkeypatch=monkeypatch)


@pytest.mark.parametrize("answer", ["Máy bơm được bảo trì 2 lần mỗi năm.", "Mỗi lần tốn 2 triệu."])
def test_a_different_value_is_still_contradicted_with_the_flag(
    answer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _contradicted(answer, flag=True, monkeypatch=monkeypatch) is True


def test_an_answer_without_numbers_is_never_contradicted_by_numbers() -> None:
    assert validation._numbers_are_contradicted("may bom duoc bao tri", EVIDENCE) is False
