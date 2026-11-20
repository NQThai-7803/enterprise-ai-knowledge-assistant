"""route_matrix.py: categories, route matrix and hybrid's losses from three configurations."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.eval import route_matrix


def _case(case_id: str, passed: bool, route: str, status: str = "ANSWERED") -> dict:
    return {"id": case_id, "expect": "answer", "status": status, "passed": passed,
            "false_answer": False, "answer_route": route, "latency_ms": 10}  # fmt: skip


def _batch(tmp_path: Path) -> Path:
    batch = tmp_path / "eval-natural-1"
    runs = {
        "legacy": [_case("A", True, "det_x"), _case("B", False, "llm_legacy", "NO_ANSWER"),
                   _case("C", True, "repair_y")],
        "s3t": [_case("A", False, "llm_simple"), _case("B", True, "llm_simple"),
                _case("C", True, "llm_simple")],
        "hybrid": [_case("A", True, "det_x"), _case("B", True, "llm_simple"),
                   _case("C", False, "refusal_gate", "NO_ANSWER")],
    }  # fmt: skip
    for name, cases in runs.items():
        run = batch / name / "run1"
        run.mkdir(parents=True)
        (run / "results.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
        (run / "timing.txt").write_text("seconds=42\n", encoding="utf-8")
    (batch / "batch.json").write_text(json.dumps({"set": "natural", "git_sha": "abc"}))
    return batch


def test_the_matrix_counts_routes_and_lists_hybrid_losses(tmp_path: Path) -> None:
    summary = route_matrix.summarize(_batch(tmp_path))
    legacy = summary["configs"]["legacy"]
    assert (legacy["correct"], legacy["false_refusal"], legacy["seconds"]) == (2, 1, 42)
    assert legacy["routes"] == {"det": 1, "none": 1, "repair": 1}
    assert summary["matrix"] == [
        {"legacy_route": "det", "legacy_correct": True, "s3t_correct": False, "items": 1},
        {"legacy_route": "none", "legacy_correct": False, "s3t_correct": True, "items": 1},
        {"legacy_route": "repair", "legacy_correct": True, "s3t_correct": True, "items": 1},
    ]
    assert summary["route_fired"]["hybrid"] == {"items": 1, "correct": 1, "ids": ["A"]}
    assert summary["hybrid_loses_to_s3t"] == ["C"]
    assert summary["hybrid_loses_to_legacy"] == ["C"]
    assert summary["route_mismatch"] == []


def test_the_markdown_has_ids_and_counts_only(tmp_path: Path) -> None:
    out = tmp_path / "summary.md"
    assert route_matrix.main([str(_batch(tmp_path)), "--md", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "| natural (3) | hybrid | 2 | 1 | 0 | 0 | 0 | 0 | 42 | 10 | 1 / 0 / 2 |" in text
    assert "| natural | 1 | 1 | 1 | 1 | C | C | - |" in text
