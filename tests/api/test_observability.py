from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.document_processing.ocr.models import OCRHealthResult
from app.main import create_app
from app.models import User, UserRole
from app.observability.metrics import GLOBAL_METRICS
from app.services import admin_monitoring_service as monitoring


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
        return 3 if queue_name == settings.celery_document_queue else 0

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


def test_request_observability_adds_request_id_and_safe_log(caplog) -> None:  # noqa: ANN001
    GLOBAL_METRICS.reset()
    settings = Settings(
        _env_file=None,
        trusted_hosts=["testserver"],
        metrics_include_subsystem_health=False,
        request_log_enabled=True,
    )
    client = TestClient(create_app(settings))

    with caplog.at_level(logging.INFO, logger="app.core.middleware"):
        response = client.get(
            "/health/live?prompt=SECRET",
            headers={
                "X-Request-ID": "task034-req",
                "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
            },
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "task034-req"
    record = [item for item in caplog.records if item.name == "app.core.middleware"][-1]
    assert record.request_id == "task034-req"
    assert record.route == "/health/live"
    assert record.status_code == 200
    assert record.trace_present is True
    assert "SECRET" not in caplog.text
    assert "prompt" not in caplog.text


def test_invalid_request_id_is_replaced() -> None:
    settings = Settings(
        _env_file=None,
        trusted_hosts=["testserver"],
        metrics_include_subsystem_health=False,
    )
    client = TestClient(create_app(settings))

    response = client.get("/health/live", headers={"X-Request-ID": "bad id with spaces"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "bad id with spaces"
    assert len(response.headers["x-request-id"]) == 32


def test_metrics_endpoint_can_be_disabled() -> None:
    settings = Settings(
        _env_file=None,
        trusted_hosts=["testserver"],
        metrics_enabled=False,
        metrics_include_subsystem_health=False,
    )
    client = TestClient(create_app(settings))

    response = client.get("/metrics")

    assert response.status_code == 404


@pytest.mark.integration
def test_metrics_endpoint_exposes_safe_runtime_metrics(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = make_auth_headers(make_user(role=UserRole.ADMIN))
    GLOBAL_METRICS.reset()
    install_fast_monitoring(monkeypatch)

    health = api_client.get("/health/live", headers={"X-Request-ID": "task034-metrics"})
    response = api_client.get("/metrics")

    assert health.status_code == 200
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert (
        'enterprise_ai_http_requests_total{method="GET",route="/health/live",status="200"}' in body
    )
    for component in (
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
    ):
        assert f'component="{component}"' in body
    assert "enterprise_ai_worker_active_count" in body
    assert 'enterprise_ai_queue_pending{kind="document",queue="documents"} 3' in body
    assert 'provider_type="llm"' in body
    assert 'provider_type="web_search"' in body


@pytest.mark.integration
def test_metrics_endpoint_does_not_expose_sensitive_values(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    GLOBAL_METRICS.reset()
    install_fast_monitoring(monkeypatch)

    response = api_client.get("/metrics")

    payload = response.text.lower()
    forbidden = (
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
        "citation_excerpt",
        "feedback_reason",
    )
    assert response.status_code == 200
    for marker in forbidden:
        assert marker not in payload
