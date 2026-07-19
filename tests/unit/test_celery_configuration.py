from __future__ import annotations

from app.core.config import get_settings
from app.workers.celery_app import celery_app
from app.workers.document_tasks import process_document, worker_ping


def test_celery_uses_configured_broker() -> None:
    settings = get_settings()

    assert celery_app.conf.broker_url == settings.celery_broker_url


def test_celery_uses_configured_result_backend() -> None:
    settings = get_settings()

    assert celery_app.conf.result_backend == settings.celery_result_backend


def test_celery_accepts_json_only() -> None:
    assert list(celery_app.conf.accept_content) == ["json"]


def test_celery_serializes_tasks_as_json() -> None:
    assert celery_app.conf.task_serializer == "json"


def test_celery_serializes_results_as_json() -> None:
    assert celery_app.conf.result_serializer == "json"


def test_celery_uses_utc() -> None:
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True


def test_document_task_is_routed_to_document_queue() -> None:
    settings = get_settings()

    route = celery_app.conf.task_routes["documents.process_document"]

    assert route["queue"] == settings.celery_document_queue
    assert worker_ping.name == "system.worker_ping"
    assert process_document.name == "documents.process_document"


def test_worker_prefetch_multiplier_is_configured() -> None:
    settings = get_settings()

    assert celery_app.conf.worker_prefetch_multiplier == settings.celery_worker_prefetch_multiplier


def test_task_retries_are_bounded() -> None:
    settings = get_settings()

    assert settings.celery_task_max_retries >= 0
    assert process_document.max_retries == settings.celery_task_max_retries
