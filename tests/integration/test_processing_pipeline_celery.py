from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncIterator, Coroutine, Iterator
from pathlib import Path
from typing import Any

import pytest
import redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models import Document, DocumentAccessScope, DocumentStatus, User, UserRole
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.storage.local import LocalFileStorage
from app.workers.celery_app import celery_app
from app.workers.document_tasks import process_document, worker_ping
from tests.integration.test_end_to_end_document_processing_pipeline import make_pdf

pytestmark = [
    pytest.mark.integration,
    pytest.mark.celery_integration,
    pytest.mark.processing_pipeline_celery_integration,
]


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def one_chunk(content: bytes) -> AsyncIterator[bytes]:
    yield content


def ensure_redis_available() -> None:
    settings = get_settings()
    try:
        client = redis.Redis.from_url(settings.celery_broker_url, socket_connect_timeout=2)
        client.ping()
    except redis.RedisError as exc:
        pytest.skip(f"Redis broker is not available for pipeline Celery tests: {exc}")


@pytest.fixture(scope="module")
def celery_pipeline_storage_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("pipeline-worker-storage")


@pytest.fixture(scope="module")
def celery_pipeline_worker_log_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("pipeline-worker-logs") / "worker.log"


@pytest.fixture(scope="module")
def celery_pipeline_worker_process(
    celery_pipeline_storage_root: Path,
    celery_pipeline_worker_log_path: Path,
    integration_database_url: str,
) -> Iterator[subprocess.Popen[str]]:
    ensure_redis_available()
    celery_app.control.purge()

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(Path.cwd()))
    env["DATABASE_URL"] = integration_database_url
    env["LOCAL_STORAGE_PATH"] = str(celery_pipeline_storage_root)
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
        "--hostname=pytest-task-015@%h",
    ]
    log_file = celery_pipeline_worker_log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=Path.cwd(),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.monotonic() + 60
    last_error = "worker did not become ready"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log_file.flush()
            output = celery_pipeline_worker_log_path.read_text(encoding="utf-8", errors="replace")
            pytest.fail(f"Celery pipeline worker exited early. Output:\n{output}")
        try:
            result = worker_ping.delay()
            payload = result.get(timeout=5)
            result.forget()
            if payload == {"status": "ok", "worker": "enterprise-ai"}:
                break
        except Exception as exc:  # noqa: BLE001 - readiness loop reports sanitized progress.
            last_error = repr(exc)
            time.sleep(2)
    else:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_file.flush()
        output = celery_pipeline_worker_log_path.read_text(encoding="utf-8", errors="replace")
        pytest.fail(f"Celery pipeline worker did not become ready: {last_error}\n{output}")

    yield process

    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)
    log_file.close()


async def create_user(session: AsyncSession) -> User:
    user = User(
        email=f"celery-pipeline-{uuid.uuid4()}@example.com",
        full_name="Celery Pipeline User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_uploaded_document(
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalFileStorage,
    pdf_bytes: bytes,
) -> Document:
    async with session_factory() as session:
        uploader = await create_user(session)
        storage_key = f"documents/celery/{uuid.uuid4()}.pdf"
        await storage.save(storage_key, one_chunk(pdf_bytes))
        document = Document(
            title="Celery Pipeline Document",
            original_filename="celery-pipeline.pdf",
            storage_key=storage_key,
            mime_type="application/pdf",
            file_size=len(pdf_bytes),
            checksum_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
            uploaded_by=uploader.id,
            access_scope=DocumentAccessScope.PRIVATE,
            status=DocumentStatus.UPLOADED,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document


def read_worker_tail(log_path: Path) -> str:
    return log_path.read_text(encoding="utf-8", errors="replace")[-8000:]


def test_real_worker_processes_document_to_ready(
    celery_pipeline_worker_process: subprocess.Popen[str],
    celery_pipeline_worker_log_path: Path,
    celery_pipeline_storage_root: Path,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    assert celery_pipeline_worker_process.poll() is None
    storage = LocalFileStorage(celery_pipeline_storage_root)
    pdf_bytes = make_pdf(["Celery worker pipeline text for embeddings and chunks."])
    document = run_async(
        create_uploaded_document(async_session_factory_for_tests, storage, pdf_bytes)
    )

    task_result = process_document.apply_async(
        args=(str(document.id),),
        queue=get_settings().celery_document_queue,
    )
    try:
        payload = task_result.get(timeout=300)
    except Exception as exc:  # noqa: BLE001 - include worker diagnostics in test failure.
        raise AssertionError(
            "Timed out waiting for document task. Worker output:\n"
            f"{read_worker_tail(celery_pipeline_worker_log_path)}"
        ) from exc
    task_result.forget()

    async def verify() -> None:
        async with async_session_factory_for_tests() as session:
            saved = await session.get(Document, document.id)
            assert saved is not None
            rows = await DocumentChunkRepository(session).list_by_document(document.id)
            assert saved.status == DocumentStatus.READY
            assert saved.error_message is None
            assert rows
            assert len(rows) == payload["chunk_count"]
            assert all(len(row.embedding) == 384 for row in rows)

    run_async(verify())
    assert payload["outcome"] == "READY"
    assert payload["status"] == "READY"
    assert "text" not in payload
    assert "embedding" not in payload
    assert "storage_key" not in payload


def test_real_worker_does_not_duplicate_chunks(
    celery_pipeline_worker_process: subprocess.Popen[str],
    celery_pipeline_worker_log_path: Path,
    celery_pipeline_storage_root: Path,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    assert celery_pipeline_worker_process.poll() is None
    storage = LocalFileStorage(celery_pipeline_storage_root)
    pdf_bytes = make_pdf(["Celery duplicate delivery text."])
    document = run_async(
        create_uploaded_document(async_session_factory_for_tests, storage, pdf_bytes)
    )

    first = process_document.apply_async(
        args=(str(document.id),),
        queue=get_settings().celery_document_queue,
    )
    try:
        first_payload = first.get(timeout=300)
    except Exception as exc:  # noqa: BLE001 - include worker diagnostics in test failure.
        raise AssertionError(
            "Timed out waiting for first document task. Worker output:\n"
            f"{read_worker_tail(celery_pipeline_worker_log_path)}"
        ) from exc
    first.forget()
    second = process_document.apply_async(
        args=(str(document.id),),
        queue=get_settings().celery_document_queue,
    )
    second_payload = second.get(timeout=60)
    second.forget()

    async def verify() -> None:
        async with async_session_factory_for_tests() as session:
            count = await DocumentChunkRepository(session).count_by_document(document.id)
            assert count == first_payload["chunk_count"]

    run_async(verify())
    assert first_payload["outcome"] == "READY"
    assert second_payload["outcome"] == "ALREADY_READY"
