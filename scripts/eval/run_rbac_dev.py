"""Run the RBAC dev set against the isolated stack eaka-rbac-dev.

usage (repo root, host venv, stack up):
  EVAL_PASSWORD_ADMIN=... EVAL_PASSWORD_MANAGER=... EVAL_PASSWORD_STAFF=... EVAL_PASSWORD_OPS=... \
  python scripts/eval/run_rbac_dev.py --output artifacts/rbac-dev/run1/runtime_results.json

It builds PDFs from tests/acceptance/rbac_dev_v1.yaml, uploads them through the API, creates one
account in another department, and then asks in a fixed order: every control first, then revokes
the grant, then every negative question. Passwords come from the environment and are not stored.

A leak is a citation of the forbidden document or its text reaching the answer or citation:
the document's canary or the question's fact. A negative whose control failed is inconclusive.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import branch_counters, reranker_check  # noqa: E402
from scripts.eval.eval_client import INFRA_ERROR, EvalClient, EvalInfraError, extract  # noqa: E402

SOURCE = ROOT / "tests" / "acceptance" / "rbac_dev_v1.yaml"
FONT_CANDIDATES = (
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
OPERATIONS_DEPARTMENT_CODE = "UAT-OPS"
ACCOUNTS = {
    "admin": "admin.uat@example.test",
    "manager": "manager.uat@example.test",
    "staff": "staff.uat@example.test",
    "ops": "ops-staff.rbac@example.test",
}
NEGATIVE = "negative"
CONTROL = "control"


def load_set(path: Path = SOURCE) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


# PDF extraction can turn "-" into a soft hyphen, which would hide a canary from the check.
_HYPHENS = str.maketrans(dict.fromkeys("\u00ad\u2010\u2011\u2012\u2013\u2014", "-"))


def _fold(text: str) -> str:
    text = text.translate(_HYPHENS)
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(stripped.casefold().split())


def _surface(case: Mapping[str, Any]) -> str:
    parts = [case.get("answer") or ""]
    for citation in case.get("citations", []):
        parts += [
            str(citation.get(k) or "") for k in ("document_title", "excerpt", "evidence_text")
        ]
    return _fold(" ".join(parts))


def cited_codes(case: Mapping[str, Any], codes: Mapping[str, str]) -> list[str]:
    return sorted({codes.get(c.get("document_id"), "?") for c in case.get("citations", [])})


def leak_reasons(
    case: Mapping[str, Any],
    item: Mapping[str, Any],
    document: Mapping[str, Any],
    codes: Mapping[str, str],
) -> list[str]:
    """Why a negative case exposed the forbidden document. No answer text is recorded."""
    reasons = []
    if item["document"] in cited_codes(case, codes):
        reasons.append(f"forbidden_document:{item['document']}")
    surface = _surface(case)
    if _fold(document["canary"]) in surface:
        reasons.append("canary")
    if _fold(item["fact"]) in surface:
        reasons.append("fact")
    return reasons


def control_passed(
    case: Mapping[str, Any], item: Mapping[str, Any], codes: Mapping[str, str]
) -> bool:
    return (
        case.get("status") == "ANSWERED"
        and item["document"] in cited_codes(case, codes)
        and _fold(item["fact"]) in _fold(case.get("answer") or "")
    )


def run_cases(
    items: Sequence[Mapping[str, Any]],
    ask: Callable[[str, str], dict[str, Any]],
    revoke: Callable[[], None],
) -> list[dict[str, Any]]:
    """Controls, then the revoke, then negatives. The order is what makes revoked_grant valid."""
    cases = []
    for item in items:
        cases.append({**ask(item["control"], item["question"]), "id": item["id"], "kind": CONTROL})
    revoke()
    for item in items:
        cases.append({**ask(item["account"], item["question"]), "id": item["id"], "kind": NEGATIVE})
    return cases


def grade_cases(
    cases: Iterable[Mapping[str, Any]], data: Mapping[str, Any], codes: Mapping[str, str]
) -> list[dict[str, Any]]:
    items = {item["id"]: item for item in data["items"]}
    documents = {doc["code"]: doc for doc in data["documents"]}
    graded = []
    for case in cases:
        item = items[case["id"]]
        row = {
            "id": case["id"],
            "kind": case["kind"],
            "scenario": item["scenario"],
            "account": item["account"] if case["kind"] == NEGATIVE else item["control"],
            "document": item["document"],
            "status": case["status"],
            "execution_status": case.get("execution_status"),
            "cited_codes": cited_codes(case, codes),
            "latency_ms": case.get("latency_ms"),
            "answer": case.get("answer"),
        }
        if case["kind"] == NEGATIVE:
            row["leak_reasons"] = leak_reasons(case, item, documents[item["document"]], codes)
        else:
            row["control_passed"] = control_passed(case, item, codes)
        graded.append(row)
    return graded


def _render_pdf(document: Mapping[str, Any], folder: Path) -> Path:
    import pymupdf

    font = next((path for path in FONT_CANDIDATES if Path(path).is_file()), None)
    if font is None:
        raise SystemExit("no font with Vietnamese glyphs found")
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_textbox(
        pymupdf.Rect(50, 50, 545, 790),
        document["text"],
        fontname="body",
        fontfile=font,
        fontsize=11,
    )
    path = folder / f"{document['code']}.pdf"
    pdf.save(path)
    pdf.close()
    return path


class _Admin:
    """The few admin calls setup needs."""

    def __init__(self, base_url: str, password: str) -> None:
        import httpx

        self.http = httpx.Client(base_url=base_url, timeout=300, trust_env=False)
        self.password = password
        self._login()

    def _login(self) -> None:
        response = self.http.post(
            "/api/v1/auth/login", json={"email": ACCOUNTS["admin"], "password": self.password}
        )
        response.raise_for_status()
        token = response.json()["data"]["access_token"]
        self.http.headers["Authorization"] = f"Bearer {token}"

    def _send(self, method: str, path: str, **kwargs: Any) -> Any:
        # Setup can outlive the 15-minute access token (uploads wait for READY): log in again once.
        response = self.http.request(method, path, **kwargs)
        if response.status_code == 401:
            self._login()
            response = self.http.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    def get(self, path: str) -> Any:
        return self._send("GET", path).json()["data"]

    def post(self, path: str, **kwargs: Any) -> Any:
        return self._send("POST", path, **kwargs).json()["data"]

    def ensure_ops_account(self, password: str) -> str:
        departments = self.get("/api/v1/departments?page_size=100")
        department = next(d for d in departments if d["code"] == OPERATIONS_DEPARTMENT_CODE)
        users = self.get("/api/v1/users?page_size=100")
        known = {user["email"]: user for user in users}
        if ACCOUNTS["ops"] not in known:
            self.post(
                "/api/v1/users",
                json={
                    "email": ACCOUNTS["ops"],
                    "full_name": "RBAC Dev Operations Staff",
                    "password": password,
                    "role": "STAFF",
                    "department_id": department["id"],
                },
            )
        return department["id"]

    def user_id(self, role: str) -> str:
        users = self.get("/api/v1/users?page_size=100")
        return next(user["id"] for user in users if user["email"] == ACCOUNTS[role])

    def ensure_document(
        self,
        document: Mapping[str, Any],
        folder: Path,
        department_id: str,
        version: str = "rbac-dev-v1",
    ) -> str:
        existing = {d.get("document_code"): d for d in self.get("/api/v1/documents?page_size=100")}
        runtime = existing.get(document["code"])
        if runtime is None:
            fields = {
                "title": document["title"],
                "access_scope": document["scope"],
                "document_code": document["code"],
                "document_version": version,
                "description": f"{version} fixture",
            }
            if document["scope"] == "DEPARTMENT":
                fields["department_id"] = department_id
            path = _render_pdf(document, folder)
            with path.open("rb") as handle:
                runtime = self.post(
                    "/api/v1/documents/upload",
                    data=fields,
                    files={"file": (path.name, handle, "application/pdf")},
                )
        deadline = time.time() + 900
        while True:
            state = self.get(f"/api/v1/documents/{runtime['id']}/status")["status"]
            if state == "READY":
                return runtime["id"]
            if state == "FAILED" or time.time() > deadline:
                raise SystemExit(f"{document['code']} is {state}")
            time.sleep(3)

    def permissions(self, document_id: str) -> list[dict[str, Any]]:
        return self.get(f"/api/v1/documents/{document_id}/permissions")

    def grant(self, document_id: str, role: str) -> None:
        user_id = self.user_id(role)
        if not any(p.get("user_id") == user_id for p in self.permissions(document_id)):
            self.post(
                f"/api/v1/documents/{document_id}/permissions",
                json={"user_id": user_id, "permission": "VIEW"},
            )

    def revoke(self, document_id: str, role: str) -> None:
        user_id = self.user_id(role)
        for permission in self.permissions(document_id):
            if permission.get("user_id") == user_id:
                self._send(
                    "DELETE", f"/api/v1/documents/{document_id}/permissions/{permission['id']}"
                )


def _asker(base_url: str, passwords: Mapping[str, str]) -> Callable[[str, str], dict[str, Any]]:
    clients: dict[str, EvalClient] = {}

    def ask(role: str, question: str) -> dict[str, Any]:
        client = clients.setdefault(
            role, EvalClient(base_url, email=ACCOUNTS[role], password=passwords[role])
        )
        result: dict[str, Any] = {}
        for _ in range(2):
            try:
                session_id = client.create_session("RBAC dev")
                result = extract(client.ask(session_id, question))
            except EvalInfraError:
                result = {
                    "status": INFRA_ERROR,
                    "execution_status": INFRA_ERROR,
                    "answer": "",
                    "citations": [],
                }
            if result["execution_status"] != INFRA_ERROR:
                break
        return result

    return ask


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    reranker_check.add_arguments(parser)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    passwords = {}
    for role in ACCOUNTS:
        value = os.environ.get(f"EVAL_PASSWORD_{role.upper()}")
        if not value:
            parser.error(f"set EVAL_PASSWORD_{role.upper()}")
        passwords[role] = value
    base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
    try:
        reranker = reranker_check.guard(args, base_url)
    except reranker_check.RerankerModeRefusedError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    data = load_set()
    admin = _Admin(base_url, passwords["admin"])
    department_id = admin.ensure_ops_account(passwords["ops"])
    ids: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as folder:
        for document in data["documents"]:
            ids[document["code"]] = admin.ensure_document(document, Path(folder), department_id)
            for role in document.get("grants", []):
                admin.grant(ids[document["code"]], role)
    revocable = next(d for d in data["documents"] if d.get("revocable_grant"))
    role = revocable["revocable_grant"]
    admin.grant(ids[revocable["code"]], role)
    codes = {document_id: code for code, document_id in ids.items()}

    started_at = datetime.now(UTC).isoformat()
    counters_start = branch_counters.read(base_url)
    cases = run_cases(
        data["items"],
        _asker(base_url, passwords),
        lambda: admin.revoke(ids[revocable["code"]], role),
    )
    graded = grade_cases(cases, data, codes)
    payload = {
        "version": data["version"],
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        **reranker,
        "branch_counters": branch_counters.delta(counters_start, branch_counters.read(base_url)),
        "cases": graded,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"cases: {len(graded)}")
    return reranker_check.finish(args.output, reranker, base_url, 0)


if __name__ == "__main__":
    raise SystemExit(main())
