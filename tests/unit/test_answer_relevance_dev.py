"""Answer relevance dev set: the set's shape, its lock, grading and the two-run comparison."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

import pytest

from scripts.eval import compare_flag_runs as compare
from scripts.eval import run_answer_relevance_dev as relevance
from scripts.eval import run_rbac_dev

CODES = {"d-1": "DOC-1"}
ITEM = {"id": "R", "group": 1, "expect": "answer", "document": "DOC-1", "fact": "7 ngày"}


def _case(status: str, answer: str = "", cited: bool = False) -> dict:
    citations = [{"document_id": "d-1"}] if cited else []
    return {"status": status, "answer": answer, "citations": citations}


def test_each_group_has_refusals_and_similar_answers_with_facts_from_their_documents() -> None:
    data = run_rbac_dev.load_set(relevance.SOURCE)
    documents = {doc["code"]: doc["text"] for doc in data["documents"]}
    counts = Counter((item["group"], item["expect"]) for item in data["items"])
    for group in (1, 2, 3, 4):
        assert counts[(group, "refuse")] >= 3
        assert counts[(group, "answer")] >= 3
    for item in data["items"]:
        if item["expect"] == "answer":
            assert item["fact"] in documents[item["document"]]


def test_the_set_matches_its_lock() -> None:
    assert relevance.verify_frozen()["items"] == len(
        run_rbac_dev.load_set(relevance.SOURCE)["items"]
    )


def test_a_changed_set_is_refused(tmp_path) -> None:
    source = tmp_path / "set.yaml"
    source.write_text("changed", encoding="utf-8")
    lock = tmp_path / "set.lock"
    lock.write_text(json.dumps({"sha256": hashlib.sha256(b"frozen").hexdigest()}), encoding="utf-8")
    with pytest.raises(relevance.SetChangedError):
        relevance.verify_frozen(source, lock)


def test_answer_item_needs_status_document_and_fact() -> None:
    assert relevance.grade_case(_case("ANSWERED", "Trong 7 ngày.", True), ITEM, CODES)["passed"]
    assert not relevance.grade_case(_case("ANSWERED", "Trong 9 ngày.", True), ITEM, CODES)["passed"]
    assert not relevance.grade_case(_case("ANSWERED", "Trong 7 ngày."), ITEM, CODES)["passed"]
    assert not relevance.grade_case(_case("NO_ANSWER"), ITEM, CODES)["passed"]


FR_ITEM = {
    "id": "FR",
    "group": "N",
    "expect": "answer",
    "document": "DOC-1",
    "fact": "07 ngày",
    "fact_alternatives": ["7 ngày", "bảy ngày"],
}


@pytest.mark.parametrize(
    ("answer", "passed"),
    [
        ("Trong 07 ngày làm việc.", True),
        ("Trong 7 ngày làm việc.", True),
        ("Trong bảy ngày làm việc.", True),
        ("Trong 17 ngày làm việc.", False),
        ("Trong 70 ngày làm việc.", False),
        ("Trong 5 ngày làm việc.", False),
    ],
)
def test_answer_item_accepts_any_listed_form_of_the_fact(answer: str, passed: bool) -> None:
    case = _case("ANSWERED", answer, True)
    assert relevance.grade_case(case, FR_ITEM, CODES)["passed"] is passed


def test_a_number_fact_does_not_match_inside_a_longer_number() -> None:
    item = {**ITEM, "fact": "300.000", "fact_alternatives": ["300 nghìn"]}
    assert relevance.states_fact(item, "300.000 đồng mỗi ngày")
    assert relevance.states_fact(item, "300 nghìn đồng")
    assert not relevance.states_fact(item, "1.300.000 đồng")
    assert not relevance.states_fact(item, "3.300 nghìn đồng")


def test_false_refusal_set_matches_its_lock_and_its_facts_are_in_the_documents() -> None:
    source = relevance.ROOT / "tests" / "acceptance" / "false_refusal_dev_v1.yaml"
    lock = relevance.verify_frozen(source, source.with_suffix(".lock"))
    data = run_rbac_dev.load_set(source)
    assert lock["items"] == len(data["items"]) == 20
    documents = {doc["code"]: doc["text"] for doc in data["documents"]}
    for item in data["items"]:
        if item["expect"] == "answer":
            assert relevance.states_fact(item, documents[item["document"]]), item["id"]


def test_refuse_item_counts_any_answer_as_false() -> None:
    item = {"id": "R", "group": 1, "expect": "refuse"}
    refused = relevance.grade_case(_case("NO_ANSWER"), item, CODES)
    answered = relevance.grade_case(_case("ANSWERED", "Không có.", True), item, CODES)
    assert refused["passed"] and not refused["false_answer"]
    assert answered["false_answer"] and not answered["passed"]


def test_only_a_change_seen_in_both_runs_counts() -> None:
    base = [{"A": "false_answer", "B": "correct", "C": "correct"}] * 2
    flag = [
        {"A": "correct", "B": "wrong", "C": "correct"},
        {"A": "correct", "B": "correct", "C": "correct"},
    ]
    result = compare.compare(base, flag)
    assert result["changed_in_both_runs"] == [
        {"id": "A", "base": "false_answer", "flag": "correct"}
    ]
    assert result["unstable"] == ["B"]
    assert result["base_runs"][0]["false_answer"] == 1


def test_noise_in_the_baseline_is_not_a_change() -> None:
    base = [{"A": "correct"}, {"A": "wrong"}]
    flag = [{"A": "wrong"}, {"A": "wrong"}]
    result = compare.compare(base, flag)
    assert result["changed_in_both_runs"] == []
    assert result["unstable"] == ["A"]


def test_false_refusal_v2_matches_its_lock_and_every_fact_is_in_its_document() -> None:
    source = relevance.ROOT / "tests" / "acceptance" / "false_refusal_dev_v2.yaml"
    lock = relevance.verify_frozen(source, source.with_suffix(".lock"))
    data = run_rbac_dev.load_set(source)
    assert lock["items"] == len(data["items"]) == 24
    documents = {doc["code"]: doc["text"] for doc in data["documents"]}
    for group in "LFCE":
        expects = [item["expect"] for item in data["items"] if item["group"] == group]
        assert sorted(expects) == ["answer"] * 4 + ["refuse"] * 2, group
    for item in data["items"]:
        if item["expect"] == "answer":
            assert relevance.states_fact(item, documents[item["document"]]), item["id"]


def test_every_also_fact_must_be_in_the_answer() -> None:
    item = {
        "fact": "40 giờ",
        "also_facts": [{"fact": "6 tháng", "fact_alternatives": ["06 tháng"]}],
    }
    assert relevance.states_fact(item, "Khóa học 40 giờ, cần làm việc từ 06 tháng.")
    assert not relevance.states_fact(item, "Khóa học kéo dài 40 giờ.")
