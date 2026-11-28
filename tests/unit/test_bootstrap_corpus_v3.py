"""scripts/eval/bootstrap_corpus_v3.py: manifest -> upload fields, grants and the access matrix."""

from __future__ import annotations

import pytest

from scripts.eval import bootstrap_corpus_v3 as v3

DEPARTMENT_IDS = {code: f"id-{code}" for code in v3.DEPARTMENTS}
CORPUS_KEYS = {("ND-HR-003", "2.0"), ("ND-HR-003", "2.1"), ("ND-COMP-001", "1.0")}
ORGANIZATION_CODES = {
    "ND-CORP-001",
    "ND-ORG-001",
    "ND-HR-002",
    "ND-HR-003",
    "ND-HR-004",
    "ND-HR-005",
    "ND-HR-006",
    "ND-HR-011",
    "ND-IT-001",
}
# The owner's seed (2026-11-28): the codes each account reads besides the organization ones.
OWNER_MATRIX = {
    "hr": {"ND-HR-007", "ND-COMP-001"},
    "manager": {"ND-COMP-001"},
    "staff": set(),
    "other": set(),
    "legal": {"ND-HR-010"},
    "ceo": {"ND-EXEC-001", "ND-COMP-001"},
    "payroll": {"ND-COMP-001"},
    "hiring": {"ND-HR-007"},
    "investigator": {"ND-HR-010"},
    "chro": {"ND-HR-007", "ND-HR-010", "ND-EXEC-001", "ND-COMP-001"},
}


def _doc(**overrides):
    doc = {
        "code": "ND-HR-003",
        "version": "2.1",
        "title": "Chính sách thời giờ làm việc và chấm công",
        "file": "x.pdf",
        "classification": "INTERNAL",
        "visibility": "ORGANIZATION",
        "effective_from": "2027-01-01",
        "effective_to": None,
        "lifecycle_status": "ACTIVE",
        "supersedes": "ND-HR-003 phiên bản 2.0 (áp dụng từ 01/12/2026 đến hết 31/12/2026)",
    }
    return {**doc, **overrides}


def test_superseded_key_reads_code_and_version() -> None:
    assert v3.superseded_key("ND-HR-003 phiên bản 2.0 (áp dụng …)") == ("ND-HR-003", "2.0")
    assert v3.superseded_key("ND-CORP-001 phiên bản 1.0 (hiệu lực 01/08/2026)") == (
        "ND-CORP-001",
        "1.0",
    )
    assert v3.superseded_key(None) is None


def test_upload_fields_link_the_superseded_version_in_the_corpus() -> None:
    fields = v3.upload_fields(_doc(), DEPARTMENT_IDS, {("ND-HR-003", "2.0"): "old"}, CORPUS_KEYS)
    assert fields["access_scope"] == "ORGANIZATION"
    assert fields["supersedes_document_id"] == "old"
    assert (fields["document_code"], fields["document_version"]) == ("ND-HR-003", "2.1")
    assert fields["effective_from"] == "2027-01-01"
    assert "effective_to" not in fields and "department_id" not in fields


def test_upload_fields_refuse_a_superseded_version_not_uploaded_yet() -> None:
    with pytest.raises(SystemExit, match="upload"):
        v3.upload_fields(_doc(), DEPARTMENT_IDS, {}, CORPUS_KEYS)


def test_upload_fields_take_the_manifest_visibility() -> None:
    department = _doc(
        code="ND-HR-007",
        version="2.0",
        classification="CONFIDENTIAL",
        visibility="DEPARTMENT",
        department="Phòng Nhân sự và Hành chính",
        supersedes=None,
        effective_to="2027-12-31",
    )
    fields = v3.upload_fields(department, DEPARTMENT_IDS, {}, CORPUS_KEYS)
    assert (fields["access_scope"], fields["department_id"]) == ("DEPARTMENT", "id-V3-HR")
    assert fields["effective_to"] == "2027-12-31"
    private = _doc(
        code="ND-COMP-001",
        version="1.0",
        classification="CONFIDENTIAL",  # visibility decides, not the classification
        visibility="PRIVATE",
        supersedes="ND-COMP-001 phiên bản 0.9",  # not in the corpus: named in the PDF only
    )
    fields = v3.upload_fields(private, DEPARTMENT_IDS, {}, CORPUS_KEYS)
    assert fields["access_scope"] == "PRIVATE" and "department_id" not in fields
    assert "supersedes_document_id" not in fields


def test_metadata_diff_names_what_to_update() -> None:
    want = {"access_scope": "PRIVATE", "effective_from": "2026-12-01", "lifecycle_status": "ACTIVE"}
    found = {**want, "access_scope": "DEPARTMENT", "department_id": "id-V3-HR"}
    assert v3.metadata_diff(found, want) == {"access_scope": "PRIVATE", "department_id": None}
    assert v3.metadata_diff(want, want) == {}


def test_readers_by_code_reads_section_7_only() -> None:
    markdown = (
        "## 6. Liên hệ\n| ND-X-1 | a | b | Sai |\n"
        "## 7. Danh mục chính sách\n\n"
        "| Mã | Tên | Phân loại | Người được đọc |\n|---|---|---|---|\n"
        "| ND-HR-002 | Nội quy | INTERNAL | Toàn bộ nhân viên |\n"
        "| ND-HR-010 | Điều tra | RESTRICTED | Người được giao điều tra, CHRO, Pháp chế |\n"
        "\n## Phụ lục\n| ND-Y-2 | a | b | Sai |\n"
    )
    assert v3.readers_by_code(markdown) == {
        "ND-HR-002": {"Toàn bộ nhân viên"},
        "ND-HR-010": {"Người được giao điều tra", "CHRO", "Pháp chế"},
    }


def test_grant_keys_follow_the_labels_and_skip_organization_documents() -> None:
    assert v3.grant_keys(_doc(grants=["CHRO"])) == []  # ORGANIZATION: open to everyone
    private = _doc(visibility="PRIVATE", grants=["CHRO", "Pháp chế"])
    assert v3.grant_keys(private) == ["legal", "chro"]


@pytest.mark.repo_layout(
    "eval-data/corpus-v3/manifest.json", "eval-data/corpus-v3/src/ND-ORG-001.md"
)
def test_the_manifest_gives_each_account_the_owner_matrix_and_section_7() -> None:
    manifest = v3.load_manifest()
    readers = v3.readers_by_code((v3.CORPUS / "src" / "ND-ORG-001.md").read_text(encoding="utf-8"))
    assert set(readers) == {doc["code"] for doc in manifest}
    assert set(v3.ACCOUNTS) == set(OWNER_MATRIX)
    for key, account in v3.ACCOUNTS.items():
        expected = ORGANIZATION_CODES | OWNER_MATRIX[key]
        assert v3.manifest_codes(manifest, key) == expected, key
        assert v3.expected_codes(readers, account["groups"]) == expected, key
    comp = next(doc for doc in manifest if doc["code"] == "ND-COMP-001")
    assert comp["visibility"] == "PRIVATE"  # owner, 2026-11-28: not the whole HR department
    assert v3.grant_keys(comp) == ["hr", "manager", "ceo", "payroll", "chro"]


@pytest.mark.repo_layout("eval-data/corpus-v3/SHA256SUMS")
def test_corpus_v3_matches_its_checksums_and_manifest() -> None:
    names = v3.check_sums()
    manifest = v3.load_manifest()
    assert len(manifest) == 14
    assert sorted(names) == sorted([doc["file"] for doc in manifest] + ["manifest.json"])
    assert [doc["version"] for doc in manifest if doc["code"] == "ND-HR-003"] == ["2.0", "2.1"]
