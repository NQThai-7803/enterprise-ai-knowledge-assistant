"""Held-out v2 checks on made-up items: no real question or gold here."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval import heldout_v2_check as check


def _item(status: str = "ANSWERED", **overrides: object) -> dict:
    limited = status == "ANSWERED_LIMITED"
    answered = status != "NO_ANSWER"
    return {
        "id": "X-1",
        "question": "alpha beta?",
        "gold_status": status,
        "gold_answer": ["a"] if answered else [],
        "gold_citations": [{"document": "DOC", "pages": [1]}] if answered else [],
        "missing_points": ["m"] if status != "ANSWERED" else [],
        "limited_pass": "p" if limited else None,
        "fail_examples": ["f"] if limited else None,
        "forbidden": [{"type": "document", "value": "R"}],
        "source_excerpt": [{"document": "DOC", "page": 1, "text": "t"}],
        **overrides,
    }


FROZEN = {"X-1": "alpha beta?"}


@pytest.mark.parametrize("status", ["ANSWERED", "NO_ANSWER", "ANSWERED_LIMITED"])
def test_valid_items_have_no_problems(status: str) -> None:
    assert check.gold_problems([_item(status)], FROZEN) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"question": "changed"}, "differs from the frozen text"),
        ({"gold_status": "MAYBE"}, "bad gold_status"),
        ({"gold_answer": []}, "gold_answer"),
        ({"gold_citations": []}, "gold_citations"),
        ({"gold_citations": [{"document": "UAT-GROUNDING-001", "pages": [1]}]}, "restricted"),
        ({"source_excerpt": []}, "no source excerpt"),
        ({"forbidden": []}, "forbidden"),
    ],
)
def test_broken_items_are_reported(overrides: dict, expected: str) -> None:
    assert any(expected in p for p in check.gold_problems([_item(**overrides)], FROZEN))


def test_limited_needs_the_missing_points_and_the_pass_rule() -> None:
    problems = check.gold_problems(
        [_item("ANSWERED_LIMITED", missing_points=[], limited_pass=None)], FROZEN
    )
    assert any("missing_points" in p for p in problems)
    assert any("limited_pass" in p for p in problems)


def test_gold_with_other_ids_is_reported() -> None:
    assert check.gold_problems([_item(id="X-2")], FROZEN)[0].startswith("gold ids differ")


def test_a_changed_question_file_is_refused(tmp_path: Path) -> None:
    source = tmp_path / "q.yaml"
    source.write_text("a", encoding="utf-8")
    lock = tmp_path / "q.lock"
    lock.write_text(json.dumps({"sha256": "other"}), encoding="utf-8")
    with pytest.raises(check.FrozenSetChangedError):
        check.verify_frozen(source, lock)
    with pytest.raises(check.FrozenSetChangedError):
        check.verify_frozen(source, tmp_path / "absent.lock")


def test_overlap_finds_the_nearest_question() -> None:
    row = check.overlap("một hai ba bốn năm", {"A": "một hai ba bốn năm", "B": "khác hẳn"})
    assert (row["trigram_nearest"], row["word4_nearest"], row["word4_max"]) == ("A", "A", 1.0)
