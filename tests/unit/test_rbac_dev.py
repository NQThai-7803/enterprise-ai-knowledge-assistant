"""RBAC dev set: the set's shape, leak signals, run order and its score."""

from __future__ import annotations

from collections import Counter

from scripts.diagnostics import rbac_retrieval_check
from scripts.eval import metrics, run_rbac_dev

CODES = {"d-mgr": "RBAC-MGR-001", "d-org": "RBAC-ORG-001"}
ITEM = {
    "id": "RBD-X",
    "scenario": "staff_vs_manager_doc",
    "account": "staff",
    "control": "manager",
    "document": "RBAC-MGR-001",
    "fact": "47 triệu",
    "question": "Q?",
}
DOCUMENT = {"code": "RBAC-MGR-001", "canary": "RBAC-CANARY-MGR-7Q4K"}
DATA = {"items": [ITEM], "documents": [DOCUMENT]}


def _case(status: str = "NO_ANSWER", answer: str = "", citations: list | None = None) -> dict:
    return {"status": status, "answer": answer, "citations": citations or []}


def test_set_has_18_questions_split_evenly_with_facts_from_their_documents() -> None:
    data = run_rbac_dev.load_set()
    assert len(data["items"]) == 18
    assert set(Counter(item["scenario"] for item in data["items"]).values()) == {6}
    documents = {doc["code"]: doc for doc in data["documents"]}
    for item in data["items"]:
        assert item["fact"] in documents[item["document"]]["text"]
        assert item["account"] in run_rbac_dev.ACCOUNTS
        assert item["control"] in run_rbac_dev.ACCOUNTS
    for doc in data["documents"]:
        assert doc["canary"] in doc["text"] or doc.get("public")


def test_revoked_scenario_uses_the_same_account_before_and_after() -> None:
    data = run_rbac_dev.load_set()
    for item in data["items"]:
        if item["scenario"] == "revoked_grant":
            assert item["account"] == item["control"]
        else:
            assert item["account"] != item["control"]


def test_clean_refusal_is_no_leak() -> None:
    assert run_rbac_dev.leak_reasons(_case(), ITEM, DOCUMENT, CODES) == []


def test_answer_from_a_visible_document_is_not_a_leak() -> None:
    case = _case("ANSWERED", "Báo cho lễ tân.", [{"document_id": "d-org", "excerpt": "lễ tân"}])
    assert run_rbac_dev.leak_reasons(case, ITEM, DOCUMENT, CODES) == []


def test_each_leak_signal_is_reported() -> None:
    cited = _case("ANSWERED", "x", [{"document_id": "d-mgr"}])
    assert run_rbac_dev.leak_reasons(cited, ITEM, DOCUMENT, CODES) == [
        "forbidden_document:RBAC-MGR-001"
    ]
    fact = _case("ANSWERED", "Hạn mức là 47 TRIEU đồng.")
    assert run_rbac_dev.leak_reasons(fact, ITEM, DOCUMENT, CODES) == ["fact"]
    canary = _case("ANSWERED", "y", [{"document_id": "d-org", "excerpt": "rbac-canary-mgr-7q4k"}])
    assert run_rbac_dev.leak_reasons(canary, ITEM, DOCUMENT, CODES) == ["canary"]


def test_soft_hyphen_from_pdf_extraction_does_not_hide_a_canary() -> None:
    case = _case("ANSWERED", "Ma: RBAC\u00adCANARY\u00adMGR\u00ad7Q4K")
    assert run_rbac_dev.leak_reasons(case, ITEM, DOCUMENT, CODES) == ["canary"]


def test_control_needs_status_citation_and_fact() -> None:
    good = _case("ANSWERED", "47 triệu đồng", [{"document_id": "d-mgr"}])
    assert run_rbac_dev.control_passed(good, ITEM, CODES) is True
    assert run_rbac_dev.control_passed(_case(), ITEM, CODES) is False
    other_doc = _case("ANSWERED", "47 triệu", [{"document_id": "d-org"}])
    assert run_rbac_dev.control_passed(other_doc, ITEM, CODES) is False
    no_fact = _case("ANSWERED", "khác", [{"document_id": "d-mgr"}])
    assert run_rbac_dev.control_passed(no_fact, ITEM, CODES) is False


def test_controls_run_before_the_revoke_and_negatives_after() -> None:
    log = []

    def ask(role: str, question: str) -> dict:
        log.append(("ask", role))
        return _case()

    cases = run_rbac_dev.run_cases([ITEM], ask, lambda: log.append(("revoke", "")))
    assert log == [("ask", "manager"), ("revoke", ""), ("ask", "staff")]
    assert [case["kind"] for case in cases] == ["control", "negative"]


def _graded(negative: dict, control: dict) -> dict:
    cases = [
        {**control, "id": "RBD-X", "kind": "control"},
        {**negative, "id": "RBD-X", "kind": "negative"},
    ]
    return {"cases": run_rbac_dev.grade_cases(cases, DATA, CODES)}


def test_score_counts_leaks_and_marks_inconclusive_negatives() -> None:
    answered = _case("ANSWERED", "47 triệu", [{"document_id": "d-mgr"}])
    result = metrics.rbac_results(_graded(_case(), answered))
    assert result["negative"]["grade_source"] == "proxy"
    assert result["negative"]["permission_leak_count"] == 0
    assert result["negative"]["answer_accuracy"]["value"] == 1.0
    assert result["control"]["answer_accuracy"]["value"] == 1.0
    assert result["inconclusive_negatives"] == []

    leaked = metrics.rbac_results(_graded(answered, answered))
    assert leaked["negative"]["permission_leak_count"] == 1
    assert leaked["negative"]["false_answer_rate"]["ids"] == ["RBD-X"]

    failed_control = metrics.rbac_results(_graded(_case(), _case()))
    assert failed_control["inconclusive_negatives"] == ["RBD-X"]
    assert failed_control["control"]["false_refusal_rate"]["value"] == 1.0


def test_retrieval_check_needs_the_control_to_see_the_chunk() -> None:
    result = rbac_retrieval_check.verdicts(
        {"A": ["retrieve"], "B": [], "C": ["retrieve"]},
        {"A": [], "B": [], "C": ["sources"]},
    )
    assert result["A"]["conclusive"] is True
    assert result["B"]["conclusive"] is False
    assert result["B"]["leak"] is False
    assert result["C"]["leak"] is True


def test_retrieval_check_reads_every_layer() -> None:
    entry = {"cut_chunks": ["c1"]}
    empty = {"cut_chunks": []}
    result = {
        "gold_chunks": {"chunks": ["c1"]},
        "trace": {
            "retrieve": [entry],
            "semantic": [empty],
            "keyword": [empty],
            "prepared": [empty],
            "rerank": [{"output": empty}],
            "sources": [{"chunk": "c1"}],
        },
    }
    assert rbac_retrieval_check.seen_at(result) == ["retrieve", "sources"]


def test_route_names_the_answering_branch_only_for_the_deterministic_route() -> None:
    hits = [{"branch": "_structured_a"}, {"branch": "_structured_b"}]
    route = rbac_retrieval_check.route_of(
        {"route": "deterministic", "trace": {"structured_hits": hits}}
    )
    assert route == {"route": "deterministic", "branch": "_structured_b"}
    llm = rbac_retrieval_check.route_of({"route": "llm", "trace": {"structured_hits": hits}})
    assert llm == {"route": "llm", "branch": None}
