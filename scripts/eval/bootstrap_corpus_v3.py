"""Load corpus v3 (eval-data/corpus-v3: Nova Digital, 14 PDFs) through the normal API, by its
manifest, then check who sees what.

Run inside the API container's network, with the repository mounted read-only at /src, and the
passwords V3_<KEY>_PASSWORD of every key in ACCOUNTS plus UAT_ADMIN_PASSWORD in the environment:

    docker run --rm --network container:<project>-api-1 -v <repo>:/src:ro \
      -e UAT_ADMIN_PASSWORD -e V3_HR_PASSWORD ... -e V3_CHRO_PASSWORD \
      --entrypoint python <backend image> /src/scripts/eval/bootstrap_corpus_v3.py

1. Every file is checked against SHA256SUMS.
2. The departments and accounts below are created when missing; passwords are never printed.
3. Each manifest document is uploaded once, keyed by code and version, with its code, version,
   effective dates, lifecycle status, visibility and department. `supersedes` links the version
   it names when that version is in the corpus (ND-HR-003 2.1 -> 2.0). A document already there
   whose metadata differs from the manifest is updated to it. Then the VIEW grants: every account
   that holds one of the document's manifest `grants` labels.
4. Check: the 14 documents are READY with the manifest's metadata, the stack holds no other
   document, and every account's document list is exactly what the manifest gives it and what
   ND-ORG-001 section 7 ("Người được đọc") names its groups for. Exit 1 otherwise.

Never load it with corpus V2 on one stack (manifest notes): both use the same document codes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORPUS = ROOT / "eval-data" / "corpus-v3"
BASE = "http://127.0.0.1:8000"  # the API container's own network: Host is in TRUSTED_HOSTS

# code -> name, as in ND-ORG-001 sections 3 and 4
DEPARTMENTS = {
    "V3-HR": "Phòng Nhân sự và Hành chính",
    "V3-ENG": "Khối Kỹ thuật Phần mềm",
    "V3-SALES": "Khối Kinh doanh và Marketing",
    "V3-FINLEGAL": "Phòng Tài chính và Pháp chế",
    "V3-QC": "Phòng Chất lượng và Tuân thủ",
    "V3-CEO": "Văn phòng Tổng Giám đốc và PMO",
}
EVERYONE = ("Mọi người", "Toàn bộ nhân viên")
# groups: the ND-ORG-001 section 7 readers the account belongs to, besides EVERYONE.
# holds: the manifest `grants` labels the account is named under (owner's seed, 2026-11-28).
ACCOUNTS: dict[str, dict[str, Any]] = {
    "hr": {
        "email": "hr.v3@example.test",
        "name": "Corpus v3 HR Compensation Staff",
        "role": "STAFF",
        "department": "V3-HR",
        "groups": ("Phòng Nhân sự", "HR Compensation"),
        "holds": ("HR Compensation",),
    },
    "manager": {
        "email": "manager.n5.v3@example.test",
        "name": "Corpus v3 Engineering Manager (N5)",
        "role": "MANAGER",
        "department": "V3-ENG",
        "groups": ("Quản lý cấp N5 trở lên",),
        "holds": ("quản lý cấp N5 trở lên",),
    },
    "staff": {
        "email": "staff.v3@example.test",
        "name": "Corpus v3 Engineering Staff",
        "role": "STAFF",
        "department": "V3-ENG",
        "groups": (),
        "holds": (),
    },
    "other": {
        "email": "sales.v3@example.test",
        "name": "Corpus v3 Sales Staff",
        "role": "STAFF",
        "department": "V3-SALES",
        "groups": (),
        "holds": (),
    },
    "legal": {
        "email": "legal.v3@example.test",
        "name": "Corpus v3 Legal Counsel",
        "role": "STAFF",
        "department": "V3-FINLEGAL",
        "groups": ("Pháp chế",),
        "holds": ("Pháp chế",),
    },
    "ceo": {
        "email": "ceo.v3@example.test",
        "name": "Corpus v3 CEO",
        "role": "MANAGER",  # not ADMIN: an admin sees every document
        "department": "V3-CEO",
        "groups": ("Ban Điều hành", "Hội đồng Nhân sự", "Quản lý cấp N5 trở lên"),
        "holds": ("CEO", "thành viên Ban Điều hành", "Hội đồng Nhân sự"),
    },
    "payroll": {
        "email": "payroll.v3@example.test",
        "name": "Corpus v3 Payroll Specialist",
        "role": "STAFF",
        "department": "V3-FINLEGAL",  # with Legal: so ND-COMP-001 is granted per user only
        "groups": ("Payroll",),
        "holds": ("Payroll (Phòng Tài chính)",),
    },
    "hiring": {
        "email": "hiring.v3@example.test",
        "name": "Corpus v3 Hiring Manager",
        "role": "MANAGER",
        "department": "V3-ENG",
        "groups": ("Quản lý tuyển dụng",),
        "holds": ("quản lý tuyển dụng (theo vị trí)",),
    },
    "investigator": {
        "email": "investigator.v3@example.test",
        "name": "Corpus v3 Investigator",
        "role": "STAFF",
        "department": "V3-QC",
        "groups": ("Người được giao điều tra",),
        "holds": ("người được giao điều tra (theo vụ việc)",),
    },
    "chro": {
        "email": "chro.v3@example.test",
        "name": "Corpus v3 CHRO",
        "role": "MANAGER",
        "department": "V3-HR",
        "groups": (
            "CHRO",
            "Phòng Nhân sự",
            "Ban Điều hành",
            "Hội đồng Nhân sự",
            "Quản lý cấp N5 trở lên",
        ),
        "holds": ("CHRO", "thành viên Ban Điều hành", "Hội đồng Nhân sự"),
    },
}
_SUPERSEDES = re.compile(r"(ND-[A-Z]+-\d+) phiên bản (\d+(?:\.\d+)*)")
_METADATA = (
    "access_scope",
    "department_id",
    "lifecycle_status",
    "effective_from",
    "effective_to",
    "supersedes_document_id",
)


def load_manifest(corpus: Path = CORPUS) -> list[dict[str, Any]]:
    return json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))["documents"]


def check_sums(corpus: Path = CORPUS) -> list[str]:
    """Names listed in SHA256SUMS; SystemExit on any mismatch or on a manifest file not listed."""
    names = []
    for line in (corpus / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if hashlib.sha256((corpus / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"hash mismatch: {name}")
        names.append(name)
    missing = {d["file"] for d in load_manifest(corpus)} - set(names)
    if missing:
        raise SystemExit(f"not in SHA256SUMS: {sorted(missing)}")
    return names


def readers_by_code(org_markdown: str) -> dict[str, set[str]]:
    """ND-ORG-001 section 7 table: document code -> its readers ("Người được đọc")."""
    section = org_markdown.split("## 7.", 1)[1].split("\n## ", 1)[0]
    readers = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].startswith("ND-"):
            readers[cells[0]] = {reader.strip() for reader in cells[3].split(",")}
    return readers


def expected_codes(readers: Mapping[str, set[str]], groups: Iterable[str]) -> set[str]:
    """The codes ND-ORG-001 section 7 lets an account with these groups read."""
    member = set(EVERYONE) | set(groups)
    return {code for code, names in readers.items() if names & member}


def grant_keys(doc: Mapping[str, Any]) -> list[str]:
    """Accounts named by one of the document's manifest grants (none for ORGANIZATION)."""
    if doc["visibility"] == "ORGANIZATION":
        return []
    labels = set(doc.get("grants") or ())
    return [key for key, account in ACCOUNTS.items() if labels & set(account["holds"])]


def manifest_codes(documents: Iterable[Mapping[str, Any]], key: str) -> set[str]:
    """The codes the manifest gives `key` under the RBAC.md view policy (no uploader, no admin)."""
    department = DEPARTMENTS[ACCOUNTS[key]["department"]]
    return {
        doc["code"]
        for doc in documents
        if doc["visibility"] == "ORGANIZATION"
        or (doc["visibility"] == "DEPARTMENT" and doc["department"] == department)
        or key in grant_keys(doc)
    }


def superseded_key(text: str | None) -> tuple[str, str] | None:
    match = _SUPERSEDES.match(text or "")
    return (match.group(1), match.group(2)) if match else None


def upload_fields(
    doc: Mapping[str, Any],
    department_ids: Mapping[str, str],
    uploaded: Mapping[tuple[str, str], str],
    corpus_keys: set[tuple[str, str]],
) -> dict[str, str]:
    """Form fields of one upload. `uploaded`: (code, version) -> id of documents already there."""
    fields = {
        "title": doc["title"],
        "description": f"Nova Digital corpus v3, {doc['classification']}",
        "access_scope": doc["visibility"],
        "document_code": doc["code"],
        "document_version": doc["version"],
        "lifecycle_status": doc["lifecycle_status"],
        "effective_from": doc["effective_from"],
    }
    if doc.get("effective_to"):
        fields["effective_to"] = doc["effective_to"]
    if doc["visibility"] == "DEPARTMENT":
        names = {name: code for code, name in DEPARTMENTS.items()}
        fields["department_id"] = department_ids[names[doc["department"]]]
    previous = superseded_key(doc.get("supersedes"))
    if previous in corpus_keys:  # a version outside the corpus (1.0) is only named in the PDF
        if previous not in uploaded:
            raise SystemExit(f"{doc['code']} {doc['version']}: upload {previous} first")
        fields["supersedes_document_id"] = uploaded[previous]
    return fields


def metadata_diff(found: Mapping[str, Any], want: Mapping[str, Any]) -> dict[str, Any]:
    """The checked fields where a document on the stack differs from its upload fields."""
    return {name: want.get(name) for name in _METADATA if found.get(name) != want.get(name)}


def _password(key: str) -> str:
    name = f"V3_{key.upper()}_PASSWORD"
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set")
    return value


def _ensure_accounts(admin: Any) -> tuple[dict[str, str], dict[str, str]]:
    departments = {d["code"]: d["id"] for d in admin.get("/api/v1/departments?page_size=100")}
    for code, name in DEPARTMENTS.items():
        if code not in departments:
            created = admin.post("/api/v1/departments", json={"code": code, "name": name})
            departments[code] = created["id"]
    users = {u["email"]: u["id"] for u in admin.get("/api/v1/users?page_size=100")}
    user_ids = {}
    for key, account in ACCOUNTS.items():
        if account["email"] not in users:
            created = admin.post(
                "/api/v1/users",
                json={
                    "email": account["email"],
                    "full_name": account["name"],
                    "password": _password(key),
                    "role": account["role"],
                    "department_id": departments[account["department"]],
                },
            )
            users[account["email"]] = created["id"]
        user_ids[key] = users[account["email"]]
    return departments, user_ids


def _wait_ready(admin: Any, document_id: str, label: str) -> None:
    deadline = time.time() + 1800
    while True:
        state = admin.get(f"/api/v1/documents/{document_id}/status")["status"]
        if state == "READY":
            return
        if state == "FAILED" or time.time() > deadline:
            raise SystemExit(f"{label} is {state}")
        time.sleep(5)


def _runtime(admin: Any) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (d.get("document_code"), d.get("document_version")): d
        for d in admin.get("/api/v1/documents?page_size=100")
    }


def _load(admin: Any, manifest: list[dict[str, Any]], departments: Mapping[str, str]) -> None:
    runtime = _runtime(admin)
    ids = {key: d["id"] for key, d in runtime.items()}
    corpus_keys = {(doc["code"], doc["version"]) for doc in manifest}
    for doc in manifest:
        key = (doc["code"], doc["version"])
        fields = upload_fields(doc, departments, ids, corpus_keys)
        if key not in ids:
            with (CORPUS / doc["file"]).open("rb") as handle:
                created = admin.post(
                    "/api/v1/documents/upload",
                    data=fields,
                    files={"file": (doc["file"], handle, "application/pdf")},
                )
            ids[key] = created["id"]
        elif changes := metadata_diff(runtime[key], fields):
            admin._send("PATCH", f"/api/v1/documents/{ids[key]}", json=changes)
            print(f"{doc['code']} {doc['version']}: updated {sorted(changes)}", flush=True)
        _wait_ready(admin, ids[key], f"{doc['code']} {doc['version']}")
        print(f"{doc['code']} {doc['version']}: READY {doc['visibility']}", flush=True)


def _grant(admin: Any, manifest: list[dict[str, Any]], user_ids: Mapping[str, str]) -> None:
    runtime = _runtime(admin)
    for doc in manifest:
        document_id = runtime[(doc["code"], doc["version"])]["id"]
        permissions = admin.get(f"/api/v1/documents/{document_id}/permissions")
        granted = {p.get("user_id") for p in permissions}
        for key in grant_keys(doc):
            if user_ids[key] not in granted:
                admin.post(
                    f"/api/v1/documents/{document_id}/permissions",
                    json={"user_id": user_ids[key], "permission": "VIEW"},
                )


def _check_documents(
    manifest: list[dict[str, Any]], documents: list[dict[str, Any]], departments: Mapping[str, str]
) -> list[str]:
    problems = []
    runtime = {(d.get("document_code"), d.get("document_version")): d for d in documents}
    keys = {(doc["code"], doc["version"]) for doc in manifest}
    others = sorted(str(k) for k in runtime if k not in keys)
    if others:
        problems.append(f"documents outside corpus v3 on this stack: {others}")
    ids = {key: d["id"] for key, d in runtime.items()}
    ready = 0
    for doc in manifest:
        found = runtime.get((doc["code"], doc["version"]))
        if found is None:
            problems.append(f"{doc['code']} {doc['version']}: missing")
            continue
        ready += found["status"] == "READY"
        for name, value in metadata_diff(found, upload_fields(doc, departments, ids, keys)).items():
            problems.append(
                f"{doc['code']} {doc['version']}: {name}={found.get(name)}, not {value}"
            )
    print(f"READY: {ready}/{len(manifest)}")
    return problems


def _check_access(manifest: list[dict[str, Any]], documents: list[dict[str, Any]]) -> list[str]:
    import httpx

    readers = readers_by_code((CORPUS / "src" / "ND-ORG-001.md").read_text(encoding="utf-8"))
    codes = list(dict.fromkeys(doc["code"] for doc in manifest))
    if set(readers) != set(codes):
        raise SystemExit("ND-ORG-001 section 7 codes differ from the manifest")
    problems, seen = [], {}
    for key, account in ACCOUNTS.items():
        with httpx.Client(base_url=BASE, timeout=60, trust_env=False) as http:
            login = http.post(
                "/api/v1/auth/login", json={"email": account["email"], "password": _password(key)}
            )
            login.raise_for_status()
            http.headers["Authorization"] = f"Bearer {login.json()['data']['access_token']}"
            listed = http.get("/api/v1/documents?page_size=100").json()["data"]
            seen[key] = {d["document_code"] for d in listed}
            for source, expected in (
                ("manifest", manifest_codes(manifest, key)),
                ("ND-ORG-001 section 7", expected_codes(readers, account["groups"])),
            ):
                if seen[key] != expected:
                    problems.append(
                        f"{key} vs {source}: sees {sorted(seen[key] - expected)} extra, "
                        f"misses {sorted(expected - seen[key])}"
                    )
            for doc in documents:  # the API must refuse what the list hides
                if doc["document_code"] in seen[key]:
                    continue
                for path in (
                    f"/api/v1/documents/{doc['id']}",
                    f"/api/v1/documents/{doc['id']}/preview",
                ):
                    status = http.get(path).status_code
                    if status not in (403, 404):
                        problems.append(f"{key}: {path} returned {status}")
    header = " ".join(f"{key[:7]:>7}" for key in ACCOUNTS)
    print(f"\n{'code':<12} {header}   readers (ND-ORG-001 section 7)")
    for code in codes:
        cells = " ".join(f"{'x' if code in seen[key] else '.':>7}" for key in ACCOUNTS)
        print(f"{code:<12} {cells}   {', '.join(sorted(readers[code]))}")
    return problems


def _retrieval_as_of() -> str:
    """What the stack ranks document versions by (GET /health/ready), for the record."""
    from scripts.eval import reranker_check

    ready = reranker_check.read_ready(BASE) or {}
    return f"{ready.get('retrieval_as_of_date')} ({ready.get('retrieval_as_of_source')})"


def main() -> int:
    from scripts.eval import run_rbac_dev as rbac

    check_sums()
    manifest = load_manifest()
    admin = rbac._Admin(BASE, os.environ["UAT_ADMIN_PASSWORD"])
    departments, user_ids = _ensure_accounts(admin)
    _load(admin, manifest, departments)
    _grant(admin, manifest, user_ids)
    documents = admin.get("/api/v1/documents?page_size=100")
    problems = _check_documents(manifest, documents, departments)
    problems += _check_access(manifest, documents)
    print(f"retrieval as of: {_retrieval_as_of()}")
    for problem in problems:
        print(f"FAIL  {problem}")
    print("access matrix: OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
