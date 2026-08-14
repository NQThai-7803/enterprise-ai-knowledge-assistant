from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.document_processing.ocr.models import OCRHealthResult
from app.models import (
    AuditLog,
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    Document,
    DocumentAccessScope,
    DocumentStatus,
    Feedback,
    FeedbackRating,
    User,
    UserRole,
)
from app.services import admin_monitoring_service as monitoring

pytestmark = pytest.mark.integration


ADMIN_ENDPOINTS = (
    "/api/v1/admin/system",
    "/api/v1/admin/health",
    "/api/v1/admin/providers",
    "/api/v1/admin/workers",
    "/api/v1/admin/statistics",
    "/api/v1/admin/queues",
    "/api/v1/admin/version",
)


class FakeOCRProvider:
    async def health_check(self) -> OCRHealthResult:
        return OCRHealthResult(
            available=True,
            engine="tesseract",
            version="tesseract 5",
            languages=("eng", "vie"),
        )


def install_fast_monitoring(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_redis_ping(url: str, *, settings) -> bool:  # noqa: ANN001
        return True

    async def fake_redis_llen(url: str, queue_name: str, *, settings) -> int:  # noqa: ANN001
        return 2 if queue_name == settings.celery_document_queue else 0

    async def fake_celery_inspect(function):  # noqa: ANN001
        if function.__name__ == "_inspect_worker_ping":
            return {"worker@test": {"ok": "pong"}}
        return {
            "ping": {"worker@test": {"ok": "pong"}},
            "stats": {"worker@test": {"pool": {"implementation": "prefork"}}},
            "registered": {"worker@test": ["documents.process_document", "system.worker_ping"]},
            "active_queues": {
                "worker@test": [
                    {"name": "default"},
                    {"name": "documents"},
                ]
            },
        }

    monkeypatch.setattr(monitoring, "_redis_ping", fake_redis_ping)
    monkeypatch.setattr(monitoring, "_redis_llen", fake_redis_llen)
    monkeypatch.setattr(monitoring, "_call_celery_inspect", fake_celery_inspect)
    monkeypatch.setattr(
        monitoring,
        "create_tesseract_ocr_provider",
        lambda settings: FakeOCRProvider(),
    )


async def seed_monitoring_rows(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    admin: User,
    staff: User,
) -> None:
    async with session_factory() as session:
        document = Document(
            title="Monitoring Test Document",
            description=None,
            original_filename="monitoring.pdf",
            storage_key=f"tests/{uuid.uuid4()}.pdf",
            mime_type="application/pdf",
            file_size=128,
            checksum_sha256="a" * 64,
            status=DocumentStatus.READY,
            access_scope=DocumentAccessScope.PRIVATE,
            department_id=None,
            uploaded_by=admin.id,
            is_deleted=False,
        )
        chat_session = ChatSession(user_id=staff.id, title="Monitoring Test")
        assistant_message = ChatMessage(
            session=chat_session,
            role=ChatMessageRole.ASSISTANT,
            content="Safe aggregate test answer.",
        )
        feedback = Feedback(
            message=assistant_message,
            user_id=staff.id,
            rating=FeedbackRating.HELPFUL,
        )
        audit_log = AuditLog(
            user_id=admin.id,
            action="ADMIN_MONITORING_TEST",
            outcome="SUCCESS",
            entity_type="SYSTEM",
            metadata_json={},
        )
        session.add_all([document, chat_session, assistant_message, feedback, audit_log])
        await session.commit()


def test_admin_monitoring_endpoints_are_admin_only(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fast_monitoring(monkeypatch)
    staff = make_user(role=UserRole.STAFF)
    admin = make_user(role=UserRole.ADMIN)

    for path in ADMIN_ENDPOINTS:
        forbidden = api_client.get(path, headers=make_auth_headers(staff))
        allowed = api_client.get(path, headers=make_auth_headers(admin))

        assert forbidden.status_code == 403
        assert allowed.status_code == 200
        assert "data" in allowed.json()


def test_admin_statistics_returns_safe_aggregate_counts(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fast_monitoring(monkeypatch)
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF)
    asyncio.run(
        seed_monitoring_rows(
            async_session_factory_for_tests,
            admin=admin,
            staff=staff,
        )
    )

    response = api_client.get(
        "/api/v1/admin/statistics",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["documents"]["total"] == 1
    assert data["documents"]["by_status"]["READY"] == 1
    assert data["users"]["total"] == 2
    assert data["users"]["by_role"]["ADMIN"] == 1
    assert data["users"]["by_role"]["STAFF"] == 1
    assert data["chat_sessions"]["total"] == 1
    assert data["messages"]["by_role"]["ASSISTANT"] == 1
    assert data["feedback"]["by_rating"]["HELPFUL"] == 1
    assert data["audit_logs"]["total"] == 1
    assert "Safe aggregate test answer" not in response.text


def test_admin_system_response_does_not_expose_secrets_or_content(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fast_monitoring(monkeypatch)
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get("/api/v1/admin/system", headers=make_auth_headers(admin))

    assert response.status_code == 200
    payload = response.text.lower()
    forbidden_terms = (
        "api_key",
        "authorization",
        "bearer",
        "database_url",
        "postgresql+asyncpg",
        "redis://",
        "password",
        "secret_key",
        "storage_key",
        "prompt",
        "context",
        "excerpt",
    )
    for term in forbidden_terms:
        assert term not in payload

    data = response.json()["data"]
    assert data["health"]["status"] in {"healthy", "degraded", "unhealthy"}
    assert data["providers"]["llm"]["provider"]
    assert data["workers"]["active_worker_count"] == 1
    assert data["queues"]["queues"][0]["kind"] == "document"
    assert data["version"]["migration_head"] == "20260803_0010"


def test_admin_health_covers_required_subsystems(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fast_monitoring(monkeypatch)
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get("/api/v1/admin/health", headers=make_auth_headers(admin))

    assert response.status_code == 200
    names = {check["name"] for check in response.json()["data"]["checks"]}
    assert {
        "api",
        "postgres",
        "redis",
        "worker",
        "ocr",
        "embedding",
        "llm",
        "web_search",
        "streaming",
        "conversation",
    }.issubset(names)
