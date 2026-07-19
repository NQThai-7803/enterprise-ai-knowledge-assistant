from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import redis

from app.core.config import get_settings
from app.workers import document_tasks
from app.workers.celery_app import celery_app
from app.workers.document_tasks import enqueue_document_processing, process_document, worker_ping

pytestmark = [pytest.mark.integration, pytest.mark.celery_integration]


def ensure_redis_available() -> None:
    settings = get_settings()
    try:
        client = redis.Redis.from_url(settings.celery_broker_url, socket_connect_timeout=2)
        client.ping()
    except redis.RedisError as exc:
        pytest.skip(f"Redis broker is not available for Celery integration tests: {exc}")


@pytest.fixture(scope="module")
def celery_worker_process() -> Iterator[subprocess.Popen[str]]:
    ensure_redis_available()
    celery_app.control.purge()

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(Path.cwd()))
    command = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.workers.celery_app:celery_app",
        "worker",
        "--loglevel=INFO",
        "--pool=solo",
        "--queues=default,documents",
        "--hostname=pytest-task-011@%h",
    ]
    process = subprocess.Popen(
        command,
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.monotonic() + 60
    last_error = "worker did not become ready"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout is not None else ""
            pytest.fail(f"Celery worker exited early. Output:\n{output}")
        try:
            result = worker_ping.delay()
            payload = result.get(timeout=5)
            result.forget()
            if payload == {"status": "ok", "worker": "enterprise-ai"}:
                break
        except Exception as exc:  # noqa: BLE001 - readiness loop reports the last safe error.
            last_error = repr(exc)
            time.sleep(2)
    else:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        output = process.stdout.read() if process.stdout is not None else ""
        pytest.fail(f"Celery worker did not become ready: {last_error}\n{output}")

    yield process

    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def test_real_worker_receives_ping_task(celery_worker_process: subprocess.Popen[str]) -> None:
    assert celery_worker_process.poll() is None

    result = worker_ping.delay()
    payload = result.get(timeout=15)
    result.forget()

    assert payload["status"] == "ok"


def test_real_worker_returns_ping_result(celery_worker_process: subprocess.Popen[str]) -> None:
    assert celery_worker_process.poll() is None

    result = worker_ping.delay()
    payload = result.get(timeout=15)
    result.forget()

    assert payload == {"status": "ok", "worker": "enterprise-ai"}


def test_document_task_can_be_published_to_documents_queue(
    celery_worker_process: subprocess.Popen[str],
) -> None:
    assert celery_worker_process.poll() is None

    document_id = uuid.uuid4()
    result = process_document.apply_async(
        args=(str(document_id),),
        queue=get_settings().celery_document_queue,
    )
    payload = result.get(timeout=30)
    result.forget()

    assert payload == {
        "document_id": str(document_id),
        "outcome": "NOT_FOUND",
        "status": None,
        "reason": "NOT_FOUND",
    }


def test_task_arguments_contain_only_document_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    expected_result = object()

    def fake_apply_async(*, args, queue):
        captured["args"] = args
        captured["queue"] = queue
        return expected_result

    monkeypatch.setattr(document_tasks.process_document, "apply_async", fake_apply_async)
    document_id = uuid.uuid4()

    result = enqueue_document_processing(document_id)

    assert result is expected_result
    assert captured == {
        "args": (str(document_id),),
        "queue": get_settings().celery_document_queue,
    }
