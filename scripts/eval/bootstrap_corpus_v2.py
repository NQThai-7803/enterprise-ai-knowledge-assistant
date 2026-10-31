"""Upload UAT Corpus v2 into the PROMPT 3d stack through the normal API.

Same steps as scripts/uat/bootstrap_corpus_v2.ps1 (hash check, upload missing documents,
wait for READY, create grants) but it writes its runtime manifest to the path given on the
command line, so artifacts/uat-corpus-v2/runtime-manifest.json (V2 evidence) is untouched.
"""

import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(sys.argv[1])
BASE = sys.argv[2]
OUT = Path(sys.argv[3])
# Local UAT fixture defaults, the same as compose.uat-corpus-v2.yaml; override through the env.
PASSWORDS = {
    "admin": os.environ.get("UAT_ADMIN_PASSWORD", "LocalUatAdmin!2026"),
    "manager": os.environ.get("UAT_MANAGER_PASSWORD", "LocalUatManager!2026"),
}


def call(method, path, token=None, payload=None, body=None, content_type=None, timeout=120):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    elif body is not None:
        data = body
        headers["Content-Type"] = content_type
    try:
        with urlopen(
            Request(BASE + path, data=data, headers=headers, method=method), timeout=timeout
        ) as r:
            return r.status, json.loads(r.read().decode())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def login(email, password):
    status, body = call(
        "POST", "/api/v1/auth/login", payload={"email": email, "password": password}
    )
    assert status == 200, (status, body)
    return body["data"]


def multipart(fields, file_path):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        header = f'Content-Disposition: form-data; name="{name}"'
        parts.append(f"--{boundary}\r\n{header}\r\n\r\n{value}\r\n".encode())
    file_header = f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'
    parts.append(
        f"--{boundary}\r\n{file_header}\r\nContent-Type: application/pdf\r\n\r\n".encode()
        + file_path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def main():
    manifest = json.loads((ROOT / "uat/corpus-v2/manifest.json").read_text(encoding="utf-8"))
    admin = login("admin.uat@example.test", PASSWORDS["admin"])["access_token"]
    manager_id = login("manager.uat@example.test", PASSWORDS["manager"])["user"]["id"]
    users = {"manager.uat@example.test": manager_id}
    status, body = call("GET", "/api/v1/documents?page_size=100", admin)
    existing = {d.get("document_code"): d for d in body["data"]}
    runtime_docs = []
    for doc in manifest["documents"]:
        source = ROOT / doc["source"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != doc["sha256"]:
            raise SystemExit(f"hash mismatch {doc['code']}: {digest}")
        runtime = existing.get(doc["code"])
        if runtime is None:
            body_bytes, ctype = multipart(
                {
                    "title": doc["title"],
                    "access_scope": doc["visibility"],
                    "document_code": doc["code"],
                    "document_version": manifest["corpus_version"],
                    "description": f"UAT Corpus v2: {doc['category']}",
                },
                source,
            )
            status, body = call(
                "POST",
                "/api/v1/documents/upload",
                admin,
                body=body_bytes,
                content_type=ctype,
                timeout=300,
            )
            assert status in (200, 201, 202), (doc["code"], status, body)
            runtime = body["data"]
        deadline = time.time() + 1800
        while True:
            status, body = call("GET", f"/api/v1/documents/{runtime['id']}/status", admin)
            state = body["data"]["status"]
            if state == "READY":
                break
            if state == "FAILED" or time.time() > deadline:
                raise SystemExit(f"{doc['code']} not READY: {body}")
            time.sleep(5)
        for grant in doc["required_grants"]:
            status, body = call("GET", f"/api/v1/documents/{runtime['id']}/permissions", admin)
            if not any(p.get("user_id") == users[grant["user"]] for p in body["data"]):
                status, body = call(
                    "POST",
                    f"/api/v1/documents/{runtime['id']}/permissions",
                    admin,
                    payload={"user_id": users[grant["user"]], "permission": grant["permission"]},
                )
                assert status in (200, 201), (doc["code"], status, body)
        runtime_docs.append(
            {"code": doc["code"], "id": runtime["id"], "sha256": doc["sha256"], "status": "READY"}
        )
        print(f"{doc['code']}: READY ({runtime['id']})", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "corpus_version": manifest["corpus_version"],
                "api_url": BASE,
                "documents": runtime_docs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(OUT)


main()
