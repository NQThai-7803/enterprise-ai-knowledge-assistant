from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.workers.celery_app import celery_app
from app.workers.document_tasks import process_document


def test_celery_json_only_security_settings() -> None:
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert list(celery_app.conf.accept_content) == ["json"]


def test_celery_reliability_settings_are_configured() -> None:
    settings = Settings(_env_file=None)

    assert celery_app.conf.task_acks_late == settings.celery_task_acks_late
    assert celery_app.conf.task_reject_on_worker_lost == settings.celery_task_reject_on_worker_lost
    assert celery_app.conf.worker_prefetch_multiplier == settings.celery_worker_prefetch_multiplier
    assert celery_app.conf.task_soft_time_limit == settings.celery_task_soft_time_limit_seconds
    assert celery_app.conf.task_time_limit == settings.celery_task_time_limit_seconds
    assert process_document.max_retries == settings.celery_task_max_retries


def test_celery_time_limits_are_bounded() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            celery_task_soft_time_limit_seconds=20,
            celery_task_time_limit_seconds=10,
        )
