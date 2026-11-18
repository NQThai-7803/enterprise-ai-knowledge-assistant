"""eval-data/ (the CI copy of corpus V2 and the UAT questions) matches its checksums."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "eval-data" / "corpus-v2"


@pytest.mark.repo_layout("eval-data/corpus-v2/SHA256SUMS", "uat/corpus-v2/manifest.json")
def test_corpus_pdfs_match_the_checksums_and_the_manifest() -> None:
    sums = {}
    for line in (CORPUS / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        sums[name] = digest
        assert hashlib.sha256((CORPUS / name).read_bytes()).hexdigest() == digest, name
    manifest = json.loads((ROOT / "uat/corpus-v2/manifest.json").read_text(encoding="utf-8"))
    assert sums == {Path(d["source"]).name: d["sha256"] for d in manifest["documents"]}


@pytest.mark.repo_layout("eval-data/uat/questions.json")
def test_uat_questions_are_q001_to_q100_without_a_password() -> None:
    data = json.loads((ROOT / "eval-data/uat/questions.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in data["items"]] == [f"Q{n:03d}" for n in range(1, 101)]
    assert "password" not in data
    assert all(item["question"].strip() for item in data["items"])


@pytest.mark.repo_layout("eval-data/uat/gold.lock")
def test_uat_gold_matches_its_lock_and_q044_cites_the_company_document() -> None:
    lock = json.loads((ROOT / "eval-data/uat/gold.lock").read_text(encoding="utf-8"))
    assert lock["approved_by"].strip()
    for name, digest in lock["files"].items():
        assert hashlib.sha256((ROOT / "eval-data/uat" / name).read_bytes()).hexdigest() == digest
    gold = json.loads((ROOT / "eval-data/uat/retrieval-gold.json").read_text(encoding="utf-8"))
    assert gold["items"]["Q044"] == [["ND-HR-004", 6]]  # DEC-033: not the template


@pytest.mark.repo_layout("uat/corpus-v2/manifest.json")
def test_only_the_template_is_marked_draft() -> None:
    manifest = json.loads((ROOT / "uat/corpus-v2/manifest.json").read_text(encoding="utf-8"))
    drafts = [d["code"] for d in manifest["documents"] if d.get("lifecycle_status") == "DRAFT"]
    assert drafts == ["UAT-LEAVE-AUTHORITY-001"]
