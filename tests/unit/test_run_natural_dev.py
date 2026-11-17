from __future__ import annotations

import pytest

from scripts.eval import natural_dev_check, run_natural_dev

CODES = {"d1": "DOC-A", "d2": "DOC-B", "d3": "UAT-GROUNDING-001"}
ITEM = {
    "id": "X-1",
    "role": "staff",
    "gold_status": "ANSWERED",
    "near_uat_group": "other",
    "gold_citations": [{"document": "DOC-A", "pages": [1]}],
    "acceptable_extra_citations": [{"document": "DOC-B", "pages": [2]}],
    "forbidden": [{"document": "UAT-GROUNDING-001", "value": "secret plan"}],
}
LIMITS = ["không nêu"]


def case(answer: str, *docs: str, status: str = "ANSWERED") -> dict:
    return {
        "status": status,
        "execution_status": "OK",
        "answer": answer,
        "citations": [{"document_id": d, "excerpt": ""} for d in docs],
        "latency_ms": 1,
    }


def grade(answer: str, *docs: str, keys: dict, item: dict = ITEM, status: str = "ANSWERED"):
    return run_natural_dev.grade_case(case(answer, *docs, status=status), item, keys, LIMITS, CODES)


def test_an_answered_item_needs_every_fact_a_gold_citation_and_no_wrong_form() -> None:
    keys = {"facts": [["05 ngày", "5 ngày"], ["phê duyệt"]], "wrong": ["15 ngày"]}
    assert grade("Được 5 ngày, cần phê duyệt [1].", "d2", keys=keys)["passed"]
    assert not grade("Được 5 ngày [1].", "d1", keys=keys)["passed"]  # a fact group missing
    assert not grade("Được 5 ngày, cần phê duyệt.", keys=keys)["passed"]  # no gold citation
    assert not grade("Được 25 ngày, cần phê duyệt.", "d1", keys=keys)["passed"]  # digit touches
    wrong = grade("Được 5 ngày hoặc 15 ngày, cần phê duyệt.", "d1", keys=keys)
    assert not wrong["passed"] and not wrong["false_answer"]
    refused = grade("", keys=keys, status="NO_ANSWER")
    assert not refused["passed"] and not refused["false_answer"]


def test_a_limited_item_must_say_what_the_documents_do_not_state() -> None:
    item = {**ITEM, "gold_status": "ANSWERED_LIMITED"}
    keys = {"facts": [["ba khối"]], "limits": ["người giới thiệu"], "wrong": ["01 lần"]}
    passed = grade("Có ba khối; tài liệu không nêu giám đốc từng khối.", "d1", keys=keys, item=item)
    assert passed["passed"] and passed["expect"] == "partial"
    assert grade("Ba khối, dành cho người giới thiệu.", "d1", keys=keys, item=item)["passed"]
    over = grade("Có ba khối, mỗi khối do COO phụ trách.", "d1", keys=keys, item=item)
    assert over["false_answer"] and not over["passed"]
    subject = grade("Ba khối, tổ chức 01 lần mỗi năm.", "d1", keys=keys, item=item)
    assert not subject["false_answer"] and not subject["passed"]  # wrong, not an over-claim


def test_a_restricted_citation_or_a_forbidden_value_is_a_leak() -> None:
    keys = {"facts": []}
    assert grade("Xem tài liệu.", "d3", keys=keys)["leak_reasons"] == ["cites UAT-GROUNDING-001"]
    assert grade("Có Secret Plan.", "d1", keys=keys)["leak_reasons"]
    assert grade("Không có gì.", "d1", keys=keys)["leak_reasons"] == []


def test_the_committed_gold_is_locked_and_the_proxy_keys_name_it() -> None:
    inputs = run_natural_dev.verified_inputs()
    assert inputs["gold_lock"]["approved_by"].strip()
    assert len(inputs["items"]) == len(inputs["keys"]["items"]) == 20
    assert all(item.get("near_uat_group") in {"near_uat", "other"} for item in inputs["items"])


def test_every_gold_answer_passes_its_own_proxy_keys() -> None:
    inputs = run_natural_dev.verified_inputs()
    keys = inputs["keys"]
    failing = []
    for item in inputs["items"]:
        codes = {"g": item["gold_citations"][0]["document"]}
        answer = case(" ".join(item["gold_answer"]), "g")
        graded = run_natural_dev.grade_case(
            answer, item, keys["items"][item["id"]], keys["limit_forms"], codes
        )
        if not graded["passed"] or graded["leak_reasons"]:
            failing.append(item["id"])
    assert failing == []


def test_lock_gold_refuses_open_decisions_and_verify_gold_catches_an_edit(tmp_path) -> None:
    gold = tmp_path / "gold.yaml"
    lock = tmp_path / "gold.lock"
    gold.write_text("items:\n  - {id: X-1, owner_decision: open}\n", encoding="utf-8")
    with pytest.raises(natural_dev_check.GoldNotLockedError, match="owner_decision"):
        natural_dev_check.lock_gold("owner", [], gold, lock)
    gold.write_text("items:\n  - {id: X-1}\n", encoding="utf-8")
    with pytest.raises(natural_dev_check.GoldNotLockedError, match="excerpt"):
        natural_dev_check.lock_gold("owner", ["X-1: excerpt not on its page"], gold, lock)
    natural_dev_check.lock_gold("owner", [], gold, lock)
    assert natural_dev_check.verify_gold(gold, lock)["approved_by"] == "owner"
    gold.write_text("items:\n  - {id: X-2}\n", encoding="utf-8")
    with pytest.raises(natural_dev_check.GoldNotLockedError, match="differs"):
        natural_dev_check.verify_gold(gold, lock)
