"""Candidate-only private-document and cross-user safety smoke."""

from __future__ import annotations

import argparse
import json
import os
import runpy
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "artifacts/rag-h5-1-stress-uat.py"
MANIFEST = ROOT / "artifacts/uat-corpus-v2/runtime-manifest.json"
DEFAULT_OUTPUT = ROOT / "artifacts/task-035-3b-20261013/permission-safety.json"
QUESTION = "What approval must staff obtain before booking travel?"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite: {args.output}")
    namespace = runpy.run_path(str(BENCHMARK))
    client_type = namespace["Client"]
    client_type.req.__globals__["BASE"] = os.environ.get(
        "RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18036"
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    private_id = next(
        row["id"] for row in manifest["documents"] if row["code"] == "UAT-GROUNDING-001"
    )

    staff = client_type()
    staff.login()
    manager = client_type()
    manager_login = manager.req(
        "POST",
        "/api/v1/auth/login",
        {
            "email": "manager.uat@example.test",
            "password": os.environ.get("UAT_MANAGER_PASSWORD", "LocalUatManager!2026"),
        },
        60,
    )
    if manager_login["http_status"] != 200:
        raise RuntimeError("Candidate manager fixture login failed")
    manager.token = manager_login["body"]["data"]["access_token"]
    manager.expires = time.time() + int(manager_login["body"]["data"].get("expires_in", 900))

    manager_detail = manager.req("GET", f"/api/v1/documents/{private_id}")
    staff_detail = staff.req("GET", f"/api/v1/documents/{private_id}")
    manager_session = manager.session("TASK-035.3B manager private-scope check")
    manager_answer = namespace["extract"](manager.ask(manager_session, QUESTION))
    staff_session = staff.session("TASK-035.3B staff private-scope check")
    staff_answer = namespace["extract"](staff.ask(staff_session, QUESTION))
    cross_user_session = staff.req("GET", f"/api/v1/chat/sessions/{manager_session}")

    checks = {
        "manager_private_detail": manager_detail["http_status"] == 200,
        "staff_private_detail_denied": staff_detail["http_status"] == 404,
        "manager_grounded_private_answer": (
            manager_answer["status"] == "ANSWERED"
            and "manager approval" in manager_answer["answer"].casefold()
            and any(
                citation.get("document_id") == private_id
                for citation in manager_answer["citations"]
            )
        ),
        "staff_private_retrieval_denied": (
            staff_answer["status"] == "NO_ANSWER"
            and not staff_answer["citations"]
            and "manager approval" not in staff_answer["answer"].casefold()
        ),
        "cross_user_chat_session_denied": cross_user_session["http_status"] == 404,
    }
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "project": "enterprise-ai-task0353b",
        "private_document_id": private_id,
        "manager_detail_http": manager_detail["http_status"],
        "staff_detail_http": staff_detail["http_status"],
        "cross_user_session_http": cross_user_session["http_status"],
        "manager_answer": manager_answer,
        "staff_answer": staff_answer,
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"permission_safety={payload['passed']}/{payload['total']}")
    for name, passed in checks.items():
        print(f"{name}={'PASS' if passed else 'FAIL'}")
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
