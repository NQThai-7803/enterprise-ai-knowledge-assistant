"""Held-out v3 measurement tooling (DEC-035/036), on invented items only: no test reads
docs/eval/heldout-v3.yaml."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.eval import heldout_v3_release as release

ITEMS = [
    {"id": "X-01", "group": "A", "question": "Phí làm thẻ là bao nhiêu?", "test_account": "Bất kỳ",
     "expected_answer": "Phí là 50.000 đồng.", "expected_sources": "DOC-AA-001 mục 2", "number": 1},
    {"id": "X-02", "group": "B", "question": "Ai duyệt bí mật?", "test_account": "Bất kỳ",
     "expected_answer": "Không có thông tin.", "expected_sources": "", "number": 2},
    {"id": "X-03", "group": "C", "question": "Câu cho phòng riêng?", "test_account": "Phòng X",
     "expected_answer": "3 ngày.", "expected_sources": "DOC-AA-001", "number": 3},
]  # fmt: skip
CODES = {"d1": "DOC-AA-001", "d2": "UAT-GROUNDING-001"}


def _frozen(tmp_path: Path) -> tuple[Path, Path]:
    heldout, lock = tmp_path / "v3.yaml", tmp_path / "v3.lock"
    heldout.write_text(yaml.safe_dump({"version": "heldout_v3", "items": ITEMS}), "utf-8")
    digest = hashlib.sha256(heldout.read_bytes()).hexdigest()
    lock.write_text(json.dumps({"version": "heldout_v3", "sha256": digest}), "utf-8")
    return heldout, lock


def _case(status: str, answer: str = "", docs: tuple[str, ...] = ()) -> dict:
    return {
        "status": status,
        "execution_status": "OK",
        "answer": answer,
        "citations": [{"document_id": d} for d in docs],
        "latency_ms": 10,
    }


def test_the_gate_refuses_a_changed_file(tmp_path: Path) -> None:
    heldout, lock = _frozen(tmp_path)
    assert len(release.gate(heldout, lock)["items"]) == 3
    heldout.write_text(heldout.read_text("utf-8") + "\n# edited", "utf-8")
    with pytest.raises(release.GateRefusedError):
        release.gate(heldout, lock)


def test_an_item_whose_account_maps_to_no_seeded_user_is_not_asked() -> None:
    asked, not_run = release.plan(ITEMS)
    assert [(i["id"], i["role"]) for i in asked] == [("X-01", "staff"), ("X-02", "staff")]
    assert list(not_run) == ["X-03"]


def test_grading_needs_an_expected_document_and_the_values() -> None:
    asked, _ = release.plan(ITEMS)
    item, refuse = asked
    right = release.grade_case(_case("ANSWERED", "Phí là 50.000 đ [1].", ("d1",)), item, CODES)
    value = release.grade_case(_case("ANSWERED", "Phí là 500.000 đ [1].", ("d1",)), item, CODES)
    other = release.grade_case(_case("ANSWERED", "Phí là 50.000 đ [1].", ("d2",)), item, CODES)
    assert (right["expect"], right["passed"]) == ("answer", True)
    assert value["passed"] is False and value["values"]["missing"]
    assert other["passed"] is False and other["leak_reasons"] == ["cites UAT-GROUNDING-001"]
    refused = release.grade_case(_case("NO_ANSWER"), refuse, CODES)
    answered = release.grade_case(_case("ANSWERED", "Có [1].", ("d1",)), refuse, CODES)
    assert (refused["expect"], refused["passed"]) == ("refuse", True)
    assert answered["false_answer"] is True


def _counts(base: list[tuple[int, int]], cand: list[tuple[int, int]], leaks: int = 0) -> dict:
    def side(pairs: list[tuple[int, int]], leak: int) -> dict:
        return {
            f"run{n}": {
                "correct": 0,
                "false_refusal": fr,
                "false_answer": 0,
                "wrong": faw,
                "infra": 0,
                "leaks": leak,
            }  # fmt: skip
            for n, (faw, fr) in enumerate(pairs, 1)
        }

    return {release.BASELINE: side(base, 0), release.CANDIDATE: side(cand, leaks)}


def test_the_verdict_follows_dec_035() -> None:
    lower = _counts([(8, 2), (7, 2)], [(4, 3), (5, 3)])
    assert release.verdict(lower)["winner"] == release.CANDIDATE
    tie_then_fr = _counts([(5, 4), (6, 4)], [(5, 2), (6, 2)])
    assert release.verdict(tie_then_fr)["winner"] == release.CANDIDATE
    noisy = _counts([(5, 3), (8, 3)], [(4, 3), (6, 3)])  # lower in both runs, not beyond the spread
    assert release.verdict(noisy)["winner"] == release.BASELINE
    assert release.verdict(_counts([(8, 2), (7, 2)], [(1, 0), (1, 0)], leaks=1))["winner"] == (
        release.BASELINE
    )


def test_the_summary_carries_no_text_and_the_owner_tables_do(tmp_path: Path) -> None:
    asked, not_run = release.plan(ITEMS)
    answers = {
        "X-01": _case("ANSWERED", "Phí là 50.000 đ [1].", ("d1",)),
        "X-02": _case("NO_ANSWER"),
    }
    results = {
        "not_run": not_run,
        "cases": [release.grade_case(answers[i["id"]], i, CODES) for i in asked],
    }
    runs = {
        cfg: {"run1": results, "run2": results} for cfg in (release.BASELINE, release.CANDIDATE)
    }
    outcome, md, rows, summary = release.build(runs, ITEMS)
    assert outcome["verdict"]["winner"] == release.BASELINE  # identical sides: the default stays
    assert outcome["counts"][release.CANDIDATE]["run1"]["correct"] == 2
    for item in ITEMS:
        for field in ("question", "expected_answer"):
            assert item[field] not in summary
    assert ITEMS[0]["question"] in md and "X-03" in summary
    assert {r["id"] for r in rows} == {"X-01", "X-02"} and all(r["label"] == "" for r in rows)


@pytest.mark.repo_layout(".github/workflows/heldout-v3.yml")
def test_the_workflow_is_gated_and_runs_both_configurations_twice() -> None:
    path = release.ROOT / ".github" / "workflows" / "heldout-v3.yml"
    text = path.read_text(encoding="utf-8")
    job = yaml.safe_load(text)["jobs"]["heldout-v3"]
    assert job["environment"] == "heldout-v3-release"
    assert "refs/heads/main" in text and "DEC-035 held-out v3 run approved by the owner" in text
    names = [step["name"] for step in job["steps"]]
    assert names.index("Gate (held-out v3 matches its lock)") < names.index(
        "Run held-out v3, two runs, both configurations interleaved"
    )
    assert 'ci_batch.sh heldout_v3 "$CONFIGS" 2' in text
    assert job["env"]["CONFIGS"].startswith(release.BASELINE + ";" + release.CANDIDATE + ":")
