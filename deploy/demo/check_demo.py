"""Demo checks through the nginx on 127.0.0.1:18480 (DEMO.md). Stdlib only; run on the host.

Prints ids, codes, statuses and times only, never a password, token or answer text.
Passwords: user environment variables EAKA_DEMO_{ADMIN,MANAGER,STAFF,OPS}_PASSWORD.
The questions are dev-set ids; their text is read from the repository (UAT Q001-Q100 in
eval-data/uat/questions.json, RBAC dev in tests/acceptance/rbac_dev_v1.yaml).
Also checks the Host handling of the nginx (TC-SEC-08) and, through `docker exec`, the
deployment profile of the API (deploy/demo/check_profile.py).
usage: python deploy/demo/check_demo.py [--matrix]
"""

import http.client
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:18480"
API_CONTAINER = f"{os.environ.get('EAKA_DEMO_PROJECT') or 'eaka-demo'}-api-1"
ACCOUNTS = {
    "admin": "admin.uat@example.test",
    "manager": "manager.uat@example.test",
    "staff": "staff.uat@example.test",
    "ops": "ops-staff.rbac@example.test",
}
# (dev-set id, document the answer must not cite for a role that cannot see it)
QUESTIONS = [
    ("Q016", None),
    ("Q043", None),
    ("Q084", None),
    ("RBD-01", "RBAC-MGR-001"),
    ("RBD-13", "RBAC-REV-001"),
    ("RBD-07", "RBAC-OPS-001"),
]
# What demo.ps1 seed loads: UAT Corpus v2 (uat/corpus-v2/manifest.json) and the RBAC dev documents.
DEMO_DOCUMENTS = {
    *(f"ND-HR-00{n}" for n in range(2, 7)),
    "ND-CORP-001",
    "UAT-LEAVE-AUTHORITY-001",
    "UAT-GROUNDING-001",
    "UAT-SHARED-001",
    "RBAC-MGR-001",
    "RBAC-OPS-001",
    "RBAC-REV-001",
    "RBAC-ORG-001",
}
RESULTS = []


def dev_questions():
    """Question text by id, from the dev sets in the repository."""
    uat = json.loads((ROOT / "eval-data/uat/questions.json").read_text(encoding="utf-8"))
    text = {item["id"]: item["question"] for item in uat["items"]}
    rbac = (ROOT / "tests/acceptance/rbac_dev_v1.yaml").read_text(encoding="utf-8")
    text.update(re.findall(r'\{id: (RBD-\d+),.*\bquestion: "([^"]*)"', rbac))
    return text


def raw_get(path, host):
    """(status, Location) of one GET with this Host header, redirects not followed;
    (None, None) when nginx closes the connection without an answer (444)."""
    connection = http.client.HTTPConnection("127.0.0.1", 18480, timeout=30)
    try:
        connection.request("GET", path, headers={"Host": host})
        response = connection.getresponse()
        return response.status, response.getheader("Location")
    except (http.client.RemoteDisconnected, ConnectionResetError):
        return None, None
    finally:
        connection.close()


def check_host_handling():
    """TC-SEC-08: a forged Host gets no answer; a redirect never names a host or a port."""
    for path in ("/", "/assets", "/api", "/health/live", "/api/v1/auth/me"):
        status, location = raw_get(path, "evil.example")
        check(f"Host evil.example {path}: no answer (444)", status is None, f"{status} {location}")
    for host in ("127.0.0.1:18480", "localhost:18480"):
        for path in ("/assets", "/api"):
            status, location = raw_get(path, host)
            check(
                f"Host {host} {path}: relative redirect",
                status == 301 and location == f"{path}/",
                f"{status} Location={location}",
            )


def expected_model():
    """LLM_OLLAMA_MODEL of .env.example: main's deployment default (DEC-040)."""
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    return re.search(r"(?m)^LLM_OLLAMA_MODEL=(\S+)", example).group(1)


def check_profile():
    """M1/L3: the API runs main's defaults for every RAG_* flag, with the default model."""
    try:
        run = subprocess.run(
            ["docker", "exec", "-i", API_CONTAINER, "python", "-"],
            input=(ROOT / "deploy/demo/check_profile.py").read_bytes(),
            capture_output=True,
            timeout=120,
        )
        profile = json.loads(run.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        check(f"profile of {API_CONTAINER}", False, f"{type(exc).__name__}")
        return
    differs = profile["rag_differs"]
    check(
        "profile: every RAG_* flag at main's default",
        not differs,
        f"{profile['rag_flags']} flags" + (f", differ: {sorted(differs)}" if differs else ""),
    )
    model = expected_model()
    check(
        "profile: simple mode on the default model",
        profile["rag_answer_mode"] == "simple"
        and profile["llm_enabled"]
        and profile["llm_ollama_model"] == model,
        f"{profile['rag_answer_mode']} {profile['llm_provider']} {profile['llm_ollama_model']}"
        f" (expected {model})",
    )


def password(role):
    value = os.environ.get(f"EAKA_DEMO_{role.upper()}_PASSWORD")
    if not value and os.name == "nt":  # a shell started before the variables existed
        value = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"[Environment]::GetEnvironmentVariable('EAKA_DEMO_{role.upper()}_PASSWORD','User')",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    if not value:
        raise SystemExit(f"EAKA_DEMO_{role.upper()}_PASSWORD is not set")
    return value


def call(
    method,
    path,
    token=None,
    payload=None,
    accept="application/json",
    timeout=300,
    base=None,
    origin=None,
):
    headers = {"Accept": accept}
    if origin:
        headers["Origin"] = origin  # what a browser sends on a same-origin POST
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    try:
        response = urlopen(
            Request((base or BASE) + path, data=data, headers=headers, method=method),
            timeout=timeout,
        )
    except HTTPError as exc:
        return exc.code, exc.headers, exc.read()
    with response:
        return response.status, response.headers, response.read()


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}".rstrip(), flush=True)


def sse(token, session_id, question):
    """POST the stream endpoint; return (events in order, completed payload, headers, seconds)."""
    request = Request(
        f"{BASE}/api/v1/chat/sessions/{session_id}/messages/stream",
        data=json.dumps({"content": question}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    started = time.monotonic()
    events, completed, event, data = [], None, None, []
    with urlopen(request, timeout=300) as response:
        headers = response.headers
        for raw in response:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
            elif not line and event:
                events.append(event)
                if event == "message.completed":
                    completed = json.loads("\n".join(data))
                event, data = None, []
    return events, completed, headers, time.monotonic() - started


def main():
    text = dev_questions()
    status, headers, body = call("GET", "/health/live")
    check("api /health/live via nginx", status == 200, str(status))
    status, headers, body = call("GET", "/", accept="text/html")
    check(
        "frontend / (index.html)",
        status == 200 and b'<div id="root"' in body,
        f"{status} {headers.get('Content-Type')} cache={headers.get('Cache-Control')}",
    )
    status, headers, body = call("GET", "/chat/some-session", accept="text/html")
    check("SPA fallback for an app route", status == 200 and b'<div id="root"' in body, str(status))
    check_host_handling()
    check_profile()

    tokens = {}
    for role, email in ACCOUNTS.items():
        status, _, body = call(
            "POST", "/api/v1/auth/login", payload={"email": email, "password": password(role)}
        )
        ok = status == 200
        if ok:
            data = json.loads(body)["data"]
            tokens[role] = data["access_token"]
            user = data["user"]
            detail = f"{user['role']} department={str(user.get('department_id'))[:8]}"
        else:
            detail = str(status)
        check(f"login {role} via /api", ok, detail)

    # BR-13: the bundle names no API origin, so the page calls its own host, whichever it is.
    _, _, index = call("GET", "/", accept="text/html")
    script = index.decode().split('src="', 1)[1].split('"', 1)[0]
    bundle = call("GET", script, accept="*/*")[2].decode("utf-8", "replace")
    check(
        "bundle has no hard-coded API origin",
        "127.0.0.1:18480" not in bundle and "127.0.0.1:8000" not in bundle,
        script,
    )
    for host in ("http://localhost:18480", "http://127.0.0.1:18480"):
        status, headers, body = call(
            "POST",
            "/api/v1/auth/login",
            base=host,
            origin=host,
            payload={"email": ACCOUNTS["staff"], "password": password("staff")},
        )
        check(f"same-origin login at {host}", status == 200, str(status))

    status, _, body = call("GET", "/api/v1/documents?page_size=100", tokens["admin"])
    documents = json.loads(body)["data"]
    code_of = {d["id"]: d["document_code"] for d in documents}
    id_of = {v: k for k, v in code_of.items()}
    ready = {d["document_code"] for d in documents if d.get("status") == "READY"}
    check(
        "the 13 demo documents are READY",
        ready >= DEMO_DOCUMENTS,
        f"missing: {sorted(DEMO_DOCUMENTS - ready)}" if DEMO_DOCUMENTS - ready else "13",
    )
    others = [d for d in documents if d["document_code"] not in DEMO_DOCUMENTS]
    check(
        "no other document (else: demo.ps1 reset)",
        not others,
        f"{len(others)} other: {[d.get('original_filename') for d in others]}" if others else "",
    )
    for d in documents:
        print(
            f"      {str(d['document_code']):<24} {d.get('access_scope')}"
            f" {d.get('lifecycle_status')} {d.get('status')}"
        )

    session = json.loads(
        call("POST", "/api/v1/chat/sessions", tokens["staff"], {"title": "check SSE"})[2]
    )["data"]["id"]
    events, completed, headers, seconds = sse(tokens["staff"], session, text[QUESTIONS[0][0]])
    message = (completed or {}).get("message") or completed or {}
    check(
        "SSE via nginx reaches message.completed",
        bool(events) and events[0] == "stream.started" and events[-1] == "message.completed",
        f"{seconds:.1f}s events={','.join(dict.fromkeys(events))}",
    )
    check(
        "SSE headers: event-stream, not compressed",
        headers.get("Content-Type", "").startswith("text/event-stream")
        and not headers.get("Content-Encoding"),
        f"{headers.get('Content-Type')} encoding={headers.get('Content-Encoding')}",
    )
    keys = sorted(completed or {})
    has = lambda k: k in (completed or {}) or k in message  # noqa: E731
    check(
        "message.completed has segments and grounding_status",
        has("segments") and has("grounding_status"),
        f"keys={keys}",
    )
    call("DELETE", f"/api/v1/chat/sessions/{session}", tokens["staff"])

    status, headers, body = call(
        "GET",
        f"/api/v1/documents/{id_of['ND-HR-002']}/preview",
        tokens["staff"],
        accept="application/pdf",
    )
    check(
        "PDF preview via nginx",
        status == 200
        and headers.get("Content-Disposition", "").startswith("inline")
        and body[:5] == b"%PDF-",
        f"{status} {headers.get('Content-Type')} {headers.get('Content-Disposition', '')[:6]}"
        f" {len(body)} bytes",
    )

    def visible(role):
        status, _, body = call("GET", "/api/v1/documents?page_size=100", tokens[role])
        return {d["document_code"] for d in json.loads(body)["data"]}

    seen = {role: visible(role) for role in tokens}
    for role in tokens:
        print(f"      {role:<8} sees {len(seen[role])}: {sorted(seen[role], key=str)}")
    rev, ops_doc = id_of["RBAC-REV-001"], id_of["RBAC-OPS-001"]
    check(
        "ops staff does not see UAT-KNOWLEDGE's DEPARTMENT document",
        "RBAC-REV-001" not in seen["ops"]
        and call("GET", f"/api/v1/documents/{rev}", tokens["ops"])[0] in (403, 404)
        and call("GET", f"/api/v1/documents/{rev}/preview", tokens["ops"])[0] in (403, 404),
        "list, detail, preview",
    )
    check(
        "knowledge staff does not see UAT-OPS's DEPARTMENT document",
        "RBAC-OPS-001" not in seen["staff"]
        and call("GET", f"/api/v1/documents/{ops_doc}/preview", tokens["staff"])[0] in (403, 404),
    )
    check(
        "staff does not see the manager's PRIVATE document",
        "RBAC-MGR-001" not in seen["staff"] and "RBAC-MGR-001" in seen["manager"],
    )

    if "--matrix" in sys.argv:
        print("\nquestion x role (grounding status, cited codes, seconds):")
        for item, forbidden_doc in QUESTIONS:
            row = []
            for role in tokens:
                sid = json.loads(
                    call("POST", "/api/v1/chat/sessions", tokens[role], {"title": "check"})[2]
                )["data"]["id"]
                started = time.monotonic()
                _, _, body = call(
                    "POST",
                    f"/api/v1/chat/sessions/{sid}/messages",
                    tokens[role],
                    {"content": text[item]},
                )
                seconds = time.monotonic() - started
                data = json.loads(body)["data"]
                citations = data["assistant_message"].get("citations") or []
                cited = sorted({code_of.get(c.get("document_id"), "?") for c in citations}, key=str)
                shown = " ".join(
                    (c.get("excerpt") or "") + (c.get("evidence_text") or "") for c in citations
                )
                RESULTS.append(not any("" <= ch <= "" for ch in shown))  # BR-14
                row.append(f"{role}={data['grounding_status']}{cited} {seconds:.0f}s")
                if forbidden_doc and forbidden_doc not in seen[role]:
                    RESULTS.append(forbidden_doc not in cited)  # a leak fails the run
                call("DELETE", f"/api/v1/chat/sessions/{sid}", tokens[role])
            print(f"  {item:<7} " + " | ".join(row), flush=True)

    print(f"\n{sum(RESULTS)}/{len(RESULTS)} checks passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
