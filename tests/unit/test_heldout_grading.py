"""Held-out grading sheet: automatic REVIEW flags and run validity (no labels)."""

from __future__ import annotations

from scripts.eval import heldout_grading as grading

FIXED = "Khong tim thay du thong tin."
CODES = {"d-org": "ND-HR-003", "d-restricted": "UAT-GROUNDING-001"}
ITEM = {
    "id": "HO-X",
    "role": "staff",
    "language": "vi",
    "gold_status": "NO_ANSWER",
    "forbidden": [
        {"type": "document", "value": "UAT-GROUNDING-001"},
        {"type": "content", "value": "manager approval before booking travel"},
    ],
    "absent_keywords": ["đặt vé"],
}


def _case(answer: str, citations: list[dict] | None = None, status: str = "ANSWERED") -> dict:
    return {
        "status": status,
        "execution_status": "OK",
        "answer": answer,
        "citations": citations or [],
        "latency_ms": 10,
    }


def test_restricted_citation_and_forbidden_string_are_flagged_not_labelled() -> None:
    case = _case(
        "The staff need manager approval before booking travel for the trip.",
        [{"document_id": "d-restricted", "evidence_text": "x"}],
    )
    flags = grading.case_flags(ITEM, case, CODES, FIXED)
    assert {"FORBIDDEN_HIT", "RESTRICTED_DOC_CITED", "LANGUAGE_MISMATCH"} <= set(flags)


def test_absent_keyword_empty_evidence_and_odd_glyph() -> None:
    case = _case("Cần đặt vé trước [1]", [{"document_id": "d-org", "evidence_text": ""}])
    flags = grading.case_flags(ITEM, case, CODES, FIXED)
    assert {"ABSENT_KEYWORD_HIT", "EVIDENCE_EMPTY", "ODD_GLYPH"} <= set(flags)


def test_fixed_no_answer_has_no_language_flag() -> None:
    english_item = {**ITEM, "language": "en"}
    assert grading.case_flags(english_item, _case(FIXED, status="NO_ANSWER"), CODES, FIXED) == []


def test_english_question_answered_in_vietnamese_is_flagged() -> None:
    english_item = {**ITEM, "language": "en", "absent_keywords": []}
    flags = grading.case_flags(english_item, _case("Ngân sách là một triệu hai."), CODES, FIXED)
    assert flags == ["LANGUAGE_MISMATCH"]


def _monitor(pid: int, up: bool = True) -> dict:
    return {"ollama_pids": [pid], "ollama_up": up, "available_mb": 1000, "pagefile_pct": 5}


def test_run_validity_rules() -> None:
    ok = {"cases": [{**_case("a"), "id": "1", "monitor": _monitor(7)}]}
    assert grading.run_validity(ok)["validity"] == "VALID"
    bad = {
        "cases": [
            {**_case("a"), "id": "1", "monitor": _monitor(7), "latency_ms": 130_000},
            {**_case("a"), "id": "2", "monitor": _monitor(8)},
            {**_case("a"), "id": "3", "monitor": _monitor(8), "execution_status": "INFRA_ERROR"},
        ]
    }
    result = grading.run_validity(bad)
    assert result["validity"] == "INVALID_RESOURCE_PRESSURE"
    rules = {v["rule"]: v for v in result["violations"]}
    assert rules["LATENCY_OVER_120S"]["items"] == ["1"]
    assert rules["INFRA_ERROR"]["items"] == ["3"]
    assert "OLLAMA_RESTARTED_OR_DOWN" in rules
