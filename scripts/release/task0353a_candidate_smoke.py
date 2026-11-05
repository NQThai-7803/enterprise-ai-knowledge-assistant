"""Bounded synthetic API/worker/RAG smoke for the isolated TASK-035.3A project.

The endpoint and credentials must be supplied via environment variables. This
script never targets the protected V2 service and never writes a source PDF to
the repository; the PDF is generated in memory and uploaded through the API.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
import pymupdf


def require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value


def synthetic_pdf() -> bytes:
    pdf = pymupdf.open()
    page = pdf.new_page()
    for index, line in enumerate(
        (
            "PRIVATE SYNTHETIC POLICY FOR ISOLATED CANDIDATE QUALIFICATION.",
            "The policy code is ZEPHYR-42.",
            "The policy owner is the Test Team.",
            "Employees report a test incident within three days.",
        )
    ):
        page.insert_text((72, 72 + index * 24), line, fontsize=12)
    result = pdf.tobytes()
    pdf.close()
    return result


def assert_status(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise RuntimeError(f"{label}: expected HTTP {expected}, got {response.status_code}")


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert_status(response, 200, "login")
    return str(response.json()["data"]["access_token"])


def authorized(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def ask(client: httpx.Client, token: str, question: str) -> dict[str, object]:
    session = client.post(
        "/api/v1/chat/sessions",
        headers=authorized(token),
        json={"title": "Isolated candidate smoke"},
    )
    assert_status(session, 201, "create chat session")
    session_id = session.json()["data"]["id"]
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=authorized(token),
        json={"content": question},
        timeout=240,
    )
    assert_status(response, 201, "chat answer")
    data = response.json()["data"]
    assistant = data["assistant_message"]
    return {
        "grounding_status": data["grounding_status"],
        "retrieved_chunk_count": data["retrieved_chunk_count"],
        "answer": assistant["content"],
        "citations": assistant.get("citations", []),
    }


def main() -> None:
    base_url = require("TASK0353A_API_URL").rstrip("/")
    if base_url != "http://127.0.0.1:18035":
        raise RuntimeError("Refusing API URL outside the isolated candidate port 18035")
    evidence_path = Path(require("TASK0353A_EVIDENCE_PATH"))
    if evidence_path.exists():
        raise RuntimeError("Evidence path already exists; refusing overwrite")
    admin_email = require("TASK0353A_ADMIN_EMAIL")
    admin_password = require("TASK0353A_ADMIN_PASSWORD")
    staff_email = "staff.task0353a@example.test"
    staff_password = "Task0353aSyntheticStaff2026!"

    with httpx.Client(base_url=base_url, timeout=30) as client:
        admin_token = login(client, admin_email, admin_password)
        me = client.get("/api/v1/auth/me", headers=authorized(admin_token))
        assert_status(me, 200, "admin me")
        department = client.post(
            "/api/v1/departments",
            headers=authorized(admin_token),
            json={"name": "Synthetic Candidate Department", "code": "TASK0353A"},
        )
        assert_status(department, 201, "create synthetic department")
        department_id = department.json()["data"]["id"]
        staff_created = client.post(
            "/api/v1/users",
            headers=authorized(admin_token),
            json={
                "email": staff_email,
                "full_name": "Synthetic Isolated Staff",
                "password": staff_password,
                "role": "STAFF",
                "department_id": department_id,
            },
        )
        assert_status(staff_created, 201, "create staff")
        staff_token = login(client, staff_email, staff_password)
        upload = client.post(
            "/api/v1/documents/upload",
            headers=authorized(admin_token),
            data={"title": "Synthetic Isolated Candidate Policy", "access_scope": "PRIVATE"},
            files={"file": ("synthetic-candidate-policy.pdf", synthetic_pdf(), "application/pdf")},
        )
        assert_status(upload, 202, "document upload")
        document_id = upload.json()["data"]["id"]
        state = ""
        for _ in range(90):
            response = client.get(
                f"/api/v1/documents/{document_id}/status", headers=authorized(admin_token)
            )
            assert_status(response, 200, "document status")
            state = response.json()["data"]["status"]
            if state in {"READY", "FAILED"}:
                break
            time.sleep(2)
        if state != "READY":
            raise RuntimeError(f"Document processing did not reach READY; final state={state}")

        owner_detail = client.get(
            f"/api/v1/documents/{document_id}", headers=authorized(admin_token)
        )
        assert_status(owner_detail, 200, "owner document detail")
        denied_detail = client.get(
            f"/api/v1/documents/{document_id}", headers=authorized(staff_token)
        )
        assert_status(denied_detail, 404, "staff private document denial")

        question = "What is the code in the Synthetic Isolated Candidate Policy?"
        owner_answer = ask(client, admin_token, question)
        denied_answer = ask(client, staff_token, question)

    owner_supported = (
        owner_answer["grounding_status"] == "ANSWERED"
        and "ZEPHYR-42" in str(owner_answer["answer"])
        and bool(owner_answer["citations"])
    )
    denied_safe = (
        denied_answer["grounding_status"] == "NO_ANSWER"
        and not denied_answer["citations"]
        and "ZEPHYR-42" not in str(denied_answer["answer"])
    )
    result = {
        "scope": "isolated synthetic TASK-035.3A runtime",
        "document_id": document_id,
        "document_status": state,
        "admin_me_http": me.status_code,
        "staff_private_detail_http": denied_detail.status_code,
        "owner_answer": owner_answer,
        "staff_answer": denied_answer,
        "owner_supported": owner_supported,
        "staff_denied_safely": denied_safe,
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "document_id": document_id,
                "document_status": state,
                "staff_private_detail_http": denied_detail.status_code,
                "owner_supported": owner_supported,
                "staff_denied_safely": denied_safe,
                "owner_citations": len(owner_answer["citations"]),
            }
        )
    )
    if not owner_supported or not denied_safe:
        raise RuntimeError("Grounding or permission safety smoke did not pass")


if __name__ == "__main__":
    main()
