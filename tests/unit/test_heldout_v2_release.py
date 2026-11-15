"""Held-out v2 release tooling: the gate, the gold lock, the grading split. Invented data only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.eval import heldout_v2_release as release

QUESTIONS = (
    'items:\n  - {id: H2-001, question: "Câu một?"}\n  - {id: H2-002, question: "Câu hai?"}\n'
)


def _gold_item(item_id: str, question: str, **extra: object) -> dict:
    return {
        "id": item_id,
        "question": question,
        "gold_status": "ANSWERED",
        "gold_answer": ["một ý"],
        "gold_citations": [{"document": "DOC-A", "pages": [1]}],
        "forbidden": [{"type": "content", "value": "bí mật"}],
        "source_excerpt": [{"document": "DOC-A", "page": 1, "text": "một ý"}],
        **extra,
    }


def _files(tmp_path: Path, *, decision: bool = False) -> dict[str, Path]:
    import yaml

    questions = tmp_path / "q.yaml"
    questions.write_text(QUESTIONS, encoding="utf-8")
    questions_lock = tmp_path / "q.lock"
    sha = hashlib.sha256(questions.read_bytes()).hexdigest()
    questions_lock.write_text(json.dumps({"version": "v2", "sha256": sha}), encoding="utf-8")
    gold = tmp_path / "gold.yaml"
    items = [
        _gold_item(
            "H2-001", "Câu một?", **({"owner_decision": "chọn A hay B"} if decision else {})
        ),
        _gold_item("H2-002", "Câu hai?", role="manager"),
    ]
    gold.write_text(yaml.safe_dump({"items": items}, allow_unicode=True), encoding="utf-8")
    return {
        "questions": questions,
        "questions_lock": questions_lock,
        "gold": gold,
        "gold_lock": tmp_path / "gold.lock",
    }


def test_the_gate_refuses_until_the_owner_has_locked_the_gold(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    with pytest.raises(release.GateRefusedError, match="not approved"):
        release.gate(**paths)
    with pytest.raises(release.GateRefusedError, match="approved_by"):
        release.lock_gold("  ", **paths)
    locked = release.lock_gold("owner, 2026-11-20", **paths)
    assert locked["items"] == 2
    assert release.gate(**paths)["gold"]["approved_by"] == "owner, 2026-11-20"
    paths["gold"].write_text(paths["gold"].read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(release.GateRefusedError, match="differs from its lock"):
        release.gate(**paths)


def test_an_open_owner_decision_blocks_the_gold_lock(tmp_path: Path) -> None:
    paths = _files(tmp_path, decision=True)
    with pytest.raises(release.GateRefusedError, match="owner_decision still open"):
        release.lock_gold("owner", **paths)
    assert not paths["gold_lock"].exists()


def test_changed_questions_close_the_gate(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    release.lock_gold("owner", **paths)
    paths["questions"].write_text(QUESTIONS.replace("một", "1"), encoding="utf-8")
    with pytest.raises(release.GateRefusedError):
        release.gate(**paths)


def test_items_take_their_role_from_the_gold_with_safe_defaults(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    items = {i["id"]: i for i in release.merged_items(paths["questions"], paths["gold"])}
    assert items["H2-001"]["role"] == "staff" and items["H2-002"]["role"] == "manager"
    assert items["H2-001"]["gold_status"] == "ANSWERED" and items["H2-001"]["language"] == "vi"


def test_near_uat_splits_at_the_e5_threshold() -> None:
    vectors = {"a": [1.0, 0.0], "b": [0.6, 0.8], "u1": [1.0, 0.0], "u2": [0.0, 1.0]}

    def embed(texts: list[str]) -> np.ndarray:
        return np.array([vectors[t] for t in texts])

    groups = release.near_uat({"H2-001": "a", "H2-002": "b"}, {"Q001": "u1", "Q002": "u2"}, embed)
    assert groups["H2-001"] == {"cosine_max": 1.0, "nearest": "Q001", "group": "near_uat"}
    assert groups["H2-002"]["group"] == "other" and groups["H2-002"]["nearest"] == "Q002"


def _case(item_id: str, status: str = "ANSWERED") -> dict:
    return {
        "id": item_id,
        "status": status,
        "execution_status": "OK",
        "answer": "một ý [1]",
        "latency_ms": 1000,
        "citations": [{"document_id": "d1", "page_number": 1, "evidence_text": "một ý"}],
    }


def test_the_grading_sheet_splits_the_groups_states_dec_022_and_leaves_labels_empty(
    tmp_path: Path,
) -> None:
    paths = _files(tmp_path)
    items = release.merged_items(paths["questions"], paths["gold"])
    runs = [{"cases": [_case("H2-001"), _case("H2-002", "NO_ANSWER")]}] * 2
    groups = {"H2-001": {"cosine_max": 0.93, "nearest": "Q005", "group": "near_uat"}}
    text, rows = release.build_grading(
        items, runs, {"d1": "DOC-A"}, groups, fixed_no_answer="Không tìm thấy"
    )
    assert "2026-11-11" in text and "DEC-022" in text
    assert text.index("Group 1: near UAT") < text.index("## H2-001") < text.index("Group 2")
    assert text.index("Group 2") < text.index("## H2-002")
    assert all(row["label_run1"] == row["label_run2"] == "" for row in rows)
    assert [row["near_uat_group"] for row in rows] == ["near_uat", "other"]


def test_the_report_needs_every_label_and_counts_each_group_apart() -> None:
    rows = [
        {"id": "H2-001", "near_uat_group": "near_uat", "gold_status": "ANSWERED",
         "run1_status": "ANSWERED", "run2_status": "ANSWERED",
         "label_run1": "PASS", "label_run2": "PASS"},
        {"id": "H2-002", "near_uat_group": "other", "gold_status": "NO_ANSWER",
         "run1_status": "ANSWERED", "run2_status": "NO_ANSWER",
         "label_run1": "FAIL", "label_run2": "pass"},
    ]  # fmt: skip
    counts = release.report(rows)
    assert counts["near_uat"]["run1"]["PASS"] == 1 and counts["other"]["run1"]["FAIL"] == 1
    assert counts["other"]["run1"]["false_answers"] == ["H2-002"]
    assert counts["all"]["run2"]["PASS"] == 2
    assert "DEC-022" in release.render_report(counts)
    rows[1]["label_run2"] = ""
    with pytest.raises(release.GateRefusedError, match="labels missing"):
        release.report(rows)


def test_a_gold_document_cited_only_off_its_gold_pages_gets_a_hint() -> None:
    item = {"gold_citations": [{"document": "DOC-A", "pages": [10]}]}
    on_page = {"status": "ANSWERED", "citations": [{"document_id": "d1", "page_number": 10}]}
    off_page = {"status": "ANSWERED", "citations": [{"document_id": "d1", "page_number": 12}]}
    codes = {"d1": "DOC-A"}
    assert release.page_hints(item, on_page, codes) == []
    assert release.page_hints(item, off_page, codes) == [
        "DOC-A cited on p.[12] but not on gold p.[10]"
    ]
    assert release.page_hints(item, {"status": "NO_ANSWER", "citations": []}, codes) == []


def test_report_notes_reach_the_report() -> None:
    row = {"id": "H2-001", "near_uat_group": "other", "gold_status": "ANSWERED",
           "run1_status": "ANSWERED", "run2_status": "ANSWERED", "label_run1": "PASS",
           "label_run2": "PASS",
           "report_note": "câu trùng câu hỏi gợi ý trong tài liệu"}  # fmt: skip
    counts = release.report([row])
    assert counts["report_notes"] == {"H2-001": "câu trùng câu hỏi gợi ý trong tài liệu"}
    assert "H2-001: câu trùng câu hỏi gợi ý" in release.render_report(counts)
