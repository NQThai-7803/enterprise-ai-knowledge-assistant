"""DEC-037 owner grading policy in the UAT grader, on invented references and documents."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.eval import grade_proxy

MANIFEST = {
    "documents": [
        {"id": "a", "code": "HR-A"},
        {"id": "b", "code": "HR-B"},
        {"id": "t", "code": "TEMPLATE-1"},
    ]
}
DRAFTS = frozenset({"TEMPLATE-1"})


def _grade(reference: dict, answer: str, cited: list[str]) -> dict:
    case = {
        "id": "X1",
        "status": "ANSWERED",
        "execution_status": "OK",
        "question": "Mỗi ngày làm mấy giờ?",
        "answer": answer,
        "citations": [{"document_id": d} for d in cited],
    }
    ref = {"id": "X1", "grounding_status": "ANSWERED", "answer": "Làm 08 giờ/ngày. [1]",
           "citation_ids": [{"document_id": "a"}], **reference}  # fmt: skip
    (row,) = grade_proxy.grade({"cases": [ref]}, MANIFEST, MANIFEST, {"cases": [case]}, DRAFTS)[
        "cases"
    ]
    return row


def test_a_template_citation_never_matches() -> None:
    row = _grade({"accepted_sources": ["HR-A", "TEMPLATE-1"]}, "Làm 8 giờ/ngày [1].", ["t"])
    assert row["template_cited"] == ["TEMPLATE-1"]
    assert (row["proxy_match"], row["value_match"]) == (False, False)


def test_another_accepted_source_with_the_same_value_matches() -> None:
    accepted = {"accepted_sources": ["HR-A", "HR-B"]}
    assert _grade(accepted, "Làm 8 giờ/ngày [1].", ["b"])["value_match"] is True
    assert _grade({}, "Làm 8 giờ/ngày [1].", ["b"])["value_match"] is False  # no list: exact docs
    assert _grade(accepted, "Làm 9 giờ/ngày [1].", ["b"])["value_match"] is False  # wrong value


def test_on_a_conflict_only_the_winning_document_matches() -> None:
    winner = {"accepted_sources": ["HR-A"]}
    assert _grade(winner, "Làm 08 giờ/ngày [1].", ["a"])["value_match"] is True
    assert _grade(winner, "Làm 08 giờ/ngày [1].", ["b"])["value_match"] is False
    assert _grade(winner, "Làm 08 giờ/ngày [1].", ["a", "b"])["value_match"] is False


def test_the_drafts_come_from_the_corpus_metadata(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"documents": [{"code": "D1", "lifecycle_status": "DRAFT"}, {"code": "D2"}]}),
        "utf-8",
    )
    assert grade_proxy.draft_codes(manifest) == {"D1"}
    assert "UAT-LEAVE-AUTHORITY-001" in grade_proxy.draft_codes()
