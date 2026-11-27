"""Demo data (DEMO.md). Run by `deploy/demo/demo.ps1 seed` inside the API container's network,
with the repository mounted read-only at /src.

1. UAT Corpus v2 (eval-data/corpus-v2) through scripts/eval/bootstrap_corpus_v2.py, with the
   DRAFT document as in eval.
2. The RBAC dev documents (tests/acceptance/rbac_dev_v1.yaml) and the operations staff account.
   For the demo RBAC-REV-001 is a DEPARTMENT document of UAT-KNOWLEDGE (in the dev set it is
   PRIVATE with a grant that the run revokes), so each visibility has a document per department.

Idempotent: documents and accounts that exist are kept. Passwords come from the environment
and are never printed.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/src")
from scripts.eval import run_rbac_dev as rbac  # noqa: E402

BASE = "http://127.0.0.1:8000"  # the API container's own network: Host is in TRUSTED_HOSTS
DEPARTMENT_OVERRIDE = {"RBAC-REV-001": "UAT-KNOWLEDGE"}

subprocess.run(
    [
        sys.executable,
        "/src/scripts/eval/bootstrap_corpus_v2.py",
        "/src",
        BASE,
        "/tmp/runtime-manifest.json",
    ],
    check=True,
)

admin = rbac._Admin(BASE, os.environ["UAT_ADMIN_PASSWORD"])
ops_department = admin.ensure_ops_account(os.environ["DEMO_OPS_PASSWORD"])
departments = {d["code"]: d["id"] for d in admin.get("/api/v1/departments?page_size=100")}
with tempfile.TemporaryDirectory() as folder:
    for document in rbac.load_set()["documents"]:
        department = ops_department
        if document["code"] in DEPARTMENT_OVERRIDE:
            document = {**document, "scope": "DEPARTMENT"}
            department = departments[DEPARTMENT_OVERRIDE[document["code"]]]
        document_id = admin.ensure_document(document, Path(folder), department)
        for role in document.get("grants", []):
            admin.grant(document_id, role)
        print(f"{document['code']}: READY {document['scope']}", flush=True)
