"""PROMPT 6 batch summary: case categories and stable changes (invented results)."""

from __future__ import annotations

from scripts.diagnostics.summarize_ablation import categories, route_counts, stable_changes


def test_categories_follow_each_set_kind() -> None:
    relevance = {"cases": [
        {"id": "a", "expect": "answer", "status": "ANSWERED", "passed": True},
        {"id": "b", "expect": "answer", "status": "NO_ANSWER", "passed": False},
        {"id": "c", "expect": "refuse", "status": "ANSWERED", "passed": False},
        {"id": "d", "expect": "answer", "status": "ANSWERED", "passed": False},
    ]}  # fmt: skip
    assert categories("relevance", relevance) == {
        "a": "correct", "b": "false_refusal", "c": "false_answer", "d": "wrong",
    }  # fmt: skip
    uat = {"cases": [
        {"id": "q", "proxy_match": False, "reference_status": "ANSWERED",
         "grounding_status": "NO_ANSWER"},
    ]}  # fmt: skip
    assert categories("uat", uat) == {"q": "false_refusal"}
    rbac = {"cases": [
        {"id": "r", "kind": "negative", "status": "ANSWERED", "leak_reasons": []},
        {"id": "r", "kind": "control", "status": "ANSWERED", "control_passed": True},
    ]}  # fmt: skip
    assert categories("rbac", rbac) == {"rnegative": "false_answer", "rcontrol": "correct"}


def test_a_change_counts_only_when_both_sides_agree_with_themselves() -> None:
    base = [{"x": "false_refusal", "y": "correct"}, {"x": "false_refusal", "y": "wrong"}]
    flag = [{"x": "correct", "y": "correct"}, {"x": "correct", "y": "correct"}]
    assert stable_changes(base, flag) == [("x", "false_refusal", "correct")]


def test_uat_categories_are_split_by_answer_route() -> None:
    uat = {"cases": [
        {"id": "q1", "proxy_match": True, "answer_route": "deterministic"},
        {"id": "q2", "proxy_match": False, "reference_status": "ANSWERED",
         "grounding_status": "NO_ANSWER", "answer_route": "llm"},
        {"id": "q3", "proxy_match": True, "answer_route": "llm"},
    ]}  # fmt: skip
    assert route_counts("uat", uat, categories("uat", uat)) == {
        "deterministic": {"correct": 1},
        "llm": {"false_refusal": 1, "correct": 1},
    }
    assert route_counts("relevance", uat, {}) is None
    no_route = {"cases": [{"id": "q", "proxy_match": True}]}
    assert route_counts("uat", no_route, categories("uat", no_route)) is None
