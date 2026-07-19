from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "enterprise_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.document_tasks"],
)

celery_app.conf.update(
    task_default_queue=settings.celery_task_default_queue,
    task_routes={
        "documents.process_document": {"queue": settings.celery_document_queue},
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=settings.celery_task_track_started,
    task_acks_late=settings.celery_task_acks_late,
    task_reject_on_worker_lost=settings.celery_task_reject_on_worker_lost,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    broker_connection_retry_on_startup=True,
    result_expires=settings.celery_result_expires_seconds,
)
