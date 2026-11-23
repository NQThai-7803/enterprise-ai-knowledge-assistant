"""DEC-042 selection rule (scripts/diagnostics/dec042_table.py); invented categories only."""

from __future__ import annotations

from scripts.diagnostics.dec042_table import GAIN_SETS, GUARD_SETS, changes, verdict


def data_with(variant: dict[str, dict[str, str]], leaks: int = 0) -> dict:
    sets = {}
    for name in (*GUARD_SETS, *GAIN_SETS):
        base = {"X-1": "correct", "X-2": "false_refusal", "FR2-L01": "correct"}
        sets[name] = {
            "base": {"cats": base, "leaks": 0},
            "v2": {"cats": variant.get(name, base), "leaks": leaks},
        }
    return sets


def test_accepted_when_the_gain_sets_improve_and_the_guards_hold() -> None:
    fixed = {"X-1": "correct", "X-2": "correct", "FR2-L01": "correct"}
    result = verdict(data_with({"natural": fixed}), "v2")
    assert result == {"accepted": True, "natural_uat_gain": 1, "reasons": []}


def test_one_more_false_answer_on_a_guard_set_rejects() -> None:
    worse = {"X-1": "wrong", "X-2": "false_refusal", "FR2-L01": "correct"}
    fixed = {"X-1": "correct", "X-2": "correct", "FR2-L01": "correct"}
    result = verdict(data_with({"rbac": worse, "uat": fixed}), "v2")
    assert not result["accepted"]
    assert result["reasons"] == ["rbac: false answers + wrong values up"]


def test_the_order_dependent_items_are_not_counted() -> None:
    moved = {"X-1": "correct", "X-2": "false_refusal", "FR2-L01": "wrong"}
    fixed = {"X-1": "correct", "X-2": "correct", "FR2-L01": "correct"}
    result = verdict(data_with({"false_refusal_v2": moved, "uat": fixed}), "v2")
    assert result["accepted"]


def test_a_leak_or_no_gain_rejects() -> None:
    assert verdict(data_with({}, leaks=1), "v2")["reasons"] == ["leaks", "natural + UAT correct +0"]


def test_changes_name_fixed_and_broken_items_and_leave_out_infra() -> None:
    base = {"A": "false_refusal", "B": "correct", "C": "correct", "D": "infra"}
    flag = {"A": "correct", "B": "wrong", "C": "correct", "D": "correct"}
    assert changes(base, flag) == {
        "fixed": ["A"],
        "broken": ["B"],
        "new_fa_wrong": ["B"],
        "infra": ["D"],
    }
