from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.main import create_app
from app.schemas.admin_monitoring import AdminComponentCheck
from app.services import admin_monitoring_service as monitoring
from app.services.admin_monitoring_service import AdminMonitoringService


class FakeSession:
    pass


def make_service(settings: Settings | None = None) -> AdminMonitoringService:
    resolved_settings = settings or Settings(_env_file=None)
    return AdminMonitoringService(
        session=FakeSession(),  # type: ignore[arg-type]
        application=create_app(resolved_settings),
        settings=resolved_settings,
    )


def test_provider_statuses_are_safe_when_disabled() -> None:
    service = make_service(Settings(_env_file=None, llm_enabled=False, web_search_enabled=False))

    providers = service.get_providers()
    payload = providers.model_dump_json().lower()

    assert providers.llm.status == "disabled"
    assert providers.web_search.status == "disabled"
    assert "api_key" not in payload
    assert "password" not in payload
    assert "redis://" not in payload
    assert "postgresql" not in payload


def test_overall_health_marks_critical_worker_failure_unhealthy() -> None:
    checks = [
        AdminComponentCheck(name="api", status="ok"),
        AdminComponentCheck(name="postgres", status="ok"),
        AdminComponentCheck(name="redis", status="ok"),
        AdminComponentCheck(name="worker", status="unavailable"),
    ]

    assert monitoring._overall_health_status(checks) == "unhealthy"


def test_overall_health_treats_disabled_optional_providers_as_healthy() -> None:
    checks = [
        AdminComponentCheck(name="api", status="ok"),
        AdminComponentCheck(name="postgres", status="ok"),
        AdminComponentCheck(name="redis", status="ok"),
        AdminComponentCheck(name="worker", status="ok"),
        AdminComponentCheck(name="llm", status="disabled"),
        AdminComponentCheck(name="web_search", status="disabled"),
    ]

    assert monitoring._overall_health_status(checks) == "healthy"


def test_queue_status_reports_internal_ocr_and_embedding_without_new_queues(
    monkeypatch,
) -> None:  # noqa: ANN001
    async def fake_redis_llen(url: str, queue_name: str, *, settings: Settings) -> int:
        assert queue_name == settings.celery_document_queue
        return 7

    monkeypatch.setattr(monitoring, "_redis_llen", fake_redis_llen)
    service = make_service()

    queues = asyncio.run(service.get_queues())
    by_kind = {queue.kind: queue for queue in queues.queues}

    assert queues.status == "healthy"
    assert by_kind["document"].pending == 7
    assert by_kind["ocr"].status == "not_configured"
    assert by_kind["embedding"].status == "not_configured"
    assert by_kind["retry"].status == "not_configured"
    assert by_kind["dead_letter"].status == "not_configured"


def test_route_registered_handles_included_fastapi_routers() -> None:
    app = create_app(Settings(_env_file=None))

    assert monitoring._route_registered(
        app,
        "/api/v1/chat/sessions/{session_id}/messages/stream",
    )
