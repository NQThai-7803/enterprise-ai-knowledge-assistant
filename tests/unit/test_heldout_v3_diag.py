"""heldout_v3_diag.py prints ids, counts, codes and flags only, on invented results: no test reads
the held-out files under docs/eval or a real run."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.eval import heldout_v3_diag as diag
from scripts.eval import heldout_v3_release

ANSWER, QUESTION = "Phí là 50.000 đồng theo quy định", "Phí làm thẻ là bao nhiêu"


def _values(missing: int = 0, conflicting: int = 0) -> dict:
    pair = ["50.000", "dong"]
    return {"required": [pair, pair], "missing": [pair] * missing,
            "conflicting": [pair] * conflicting, "ok": not missing and not conflicting}  # fmt: skip


def _graded(case_id: str, status: str, cited: list[str], **extra) -> dict:
    return {
        "id": case_id, "role": "staff", "expect": "answer", "expected_codes": ["ND-HR-002"],
        "status": status, "execution_status": "OK", "cited_codes": cited, "latency_ms": 1200,
        "answer": ANSWER, "passed": False, "other_source_same_values": False,
        "false_answer": False, "leak_reasons": [], "values": _values(), **extra,
    }  # fmt: skip


def _raw(case_id: str, citations: int, http: int = 200) -> dict:
    return {"id": case_id, "http": http, "question": QUESTION, "answer": ANSWER, "retrieved": 5,
            "citations": [{"document_id": "d1", "excerpt": ANSWER}] * citations}  # fmt: skip


def _write(folder: Path, config: str, run: str, graded: list, raw: list) -> None:
    run_dir = folder / config / run
    run_dir.mkdir(parents=True)
    (run_dir / "results.json").write_text(json.dumps({"cases": graded}), "utf-8")
    (run_dir / "answers.json").write_text(json.dumps({"cases": raw}), "utf-8")


def test_the_table_names_each_failure_and_prints_no_text(tmp_path: Path, capsys) -> None:
    graded = [
        _graded("X-01", "ANSWERED", ["ND-HR-002"], passed=True),
        _graded("X-02", "NO_ANSWER", [], values=_values(missing=2)),
        _graded("X-03", "ANSWERED", ["ND-HR-005"], values=_values(missing=1, conflicting=1)),
        _graded("X-04", "ANSWERED", ["ND-HR-005"], other_source_same_values=True),
        _graded("X-05", "INFRA_ERROR", [], execution_status="INFRA_ERROR", values=None),
        {**_graded("X-06", "ANSWERED", ["UAT-GROUNDING-001"]), "expect": "refuse",
         "expected_codes": [], "values": None},
    ]  # fmt: skip
    raw = [_raw("X-01", 2), _raw("X-02", 0), _raw("X-03", 1), _raw("X-04", 1),
           _raw("X-05", 0, http=0), _raw("X-06", 1)]  # fmt: skip
    _write(tmp_path, "legacy", "run1", graded, raw)
    assert diag.main(["table", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    rows = {line.split(" | ")[2]: line.strip("| ").split(" | ") for line in out.splitlines()
            if line.startswith("| legacy | run1 | X-")}  # fmt: skip
    status, cites_gold, values_found, reason = (
        {i: r[diag.COLUMNS.index(c)] for i, r in rows.items()}
        for c in ("answer_status", "cites_gold", "values_found", "fail_reason")
    )
    assert reason == {
        "X-01": "PASS",
        "X-02": "REFUSED",
        "X-03": "NOT_GOLD_DOCUMENT+VALUES_MISSING_1_OF_2+VALUES_CONFLICTING_1",
        "X-04": "NOT_GOLD_DOCUMENT+OTHER_SOURCE_SAME_VALUES",
        "X-05": "INFRA_ERROR",
        "X-06": "FALSE_ANSWER",
    }
    assert status["X-02"] == "REFUSED" and status["X-05"] == "ERROR"
    assert (cites_gold["X-01"], cites_gold["X-03"], values_found["X-02"]) == ("Y", "N", "N")
    assert rows["X-01"][3:9] == ["200", "1200", "unrecorded", "ANSWERED", "5", "2"]
    assert "| legacy | run1 | REFUSED | 1 |" in out
    for text in (ANSWER, QUESTION, "50.000", "Phí"):
        assert text not in out


def test_a_field_that_is_not_a_name_or_a_code_is_redacted() -> None:
    assert diag._safe("ND-HR-002 UAT-SHARED-001") == "ND-HR-002 UAT-SHARED-001"
    assert diag._safe("legacy") == "legacy" and diag._safe(True) == "Y" and diag._safe(None) == "-"
    assert diag._safe("Phí là 50.000 đồng") == "<redacted>"
    assert diag._safe("the fee is fifty") == "<redacted>"  # ascii words are text too


def test_access_flags_private_draft_and_missing_gold_documents(tmp_path: Path, monkeypatch) -> None:
    items = [
        {"id": "X-01", "status": "ACTIVE", "test_account": "Bất kỳ",
         "expected_sources": "ND-HR-002 mục 2, UAT-GROUNDING-001"},
        {"id": "X-02", "status": "ACTIVE", "test_account": "Bất kỳ",
         "expected_sources": "UAT-LEAVE-AUTHORITY-001; ND-ZZ-009"},
        {"id": "X-03", "status": "ACTIVE", "test_account": "Bất kỳ", "expected_sources": ""},
        {"id": "X-04", "status": "EXCLUDED", "test_account": "Bất kỳ", "expected_sources": ""},
    ]  # fmt: skip
    monkeypatch.setattr(heldout_v3_release, "gate", lambda: {"items": items})
    manifest = tmp_path / "manifest.json"
    owner = "admin.uat@example.test"
    manifest.write_text(json.dumps({"documents": [
        {"code": "ND-HR-002", "visibility": "ORGANIZATION", "owner": owner, "required_grants": []},
        {"code": "UAT-GROUNDING-001", "visibility": "PRIVATE", "owner": owner,
         "required_grants": [{"user": "manager.uat@example.test", "permission": "VIEW"}]},
        {"code": "UAT-LEAVE-AUTHORITY-001", "visibility": "ORGANIZATION", "owner": owner,
         "required_grants": [], "lifecycle_status": "DRAFT"},
    ]}), "utf-8")  # fmt: skip
    rows, skipped = diag.access(manifest)
    found = {(r["id"], r["gold_code"]): (r.get("can_view"), r.get("draft_excluded")) for r in rows}
    assert found == {
        ("X-01", "ND-HR-002"): (True, False),
        ("X-01", "UAT-GROUNDING-001"): (False, False),  # PRIVATE, granted to the manager only
        ("X-02", "UAT-LEAVE-AUTHORITY-001"): (True, True),
        ("X-02", "ND-ZZ-009"): ("NOT_IN_CORPUS", None),
        ("X-03", "NONE"): (None, None),
    }
    assert {r["role"] for r in rows} == {"staff"} and skipped == ["X-04"]
