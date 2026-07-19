from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.models import DocumentStatus
from app.services.document_processing_pipeline import (
    DocumentProcessingOutcome,
    DocumentProcessingResult,
    PermanentDocumentProcessingError,
    TransientDocumentProcessingError,
)
from app.services.document_processing_status_service import (
    DocumentProcessingClaimOutcome,
    DocumentProcessingClaimResult,
    sanitize_processing_error,
)
from app.workers import document_tasks


class FakeStatusService:
    claim_result = DocumentProcessingClaimResult(DocumentProcessingClaimOutcome.NOT_FOUND)
    failed_messages: list[str] = []
    retry_resets: list[str] = []

    def __init__(self, session: object) -> None:
        self.session = session

    async def claim_document_for_processing(self, document_id):
        return self.claim_result

    async def mark_document_failed(self, document_id, error_message: str) -> bool:
        self.failed_messages.append(error_message)
        return True

    async def reset_document_for_retry(self, document_id) -> bool:
        self.retry_resets.append(str(document_id))
        return True


@asynccontextmanager
async def fake_worker_session():
    yield object()


@pytest.fixture(autouse=True)
def reset_fake_service(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeStatusService.claim_result = DocumentProcessingClaimResult(
        DocumentProcessingClaimOutcome.NOT_FOUND
    )
    FakeStatusService.failed_messages = []
    FakeStatusService.retry_resets = []
    monkeypatch.setattr(document_tasks, "DocumentProcessingStatusService", FakeStatusService)
    monkeypatch.setattr(document_tasks, "worker_session", fake_worker_session)


async def successful_processing(document_id):
    return DocumentProcessingResult(
        document_id=document_id,
        outcome=DocumentProcessingOutcome.READY,
        status=DocumentStatus.READY,
        page_count=2,
        chunk_count=3,
        total_tokens=123,
        embedding_dimensions=384,
    )


def run(coro):
    return asyncio.run(coro)


def test_worker_ping_returns_safe_response() -> None:
    assert document_tasks.worker_ping() == {"status": "ok", "worker": "enterprise-ai"}


def test_worker_ping_does_not_return_environment() -> None:
    result = document_tasks.worker_ping()

    assert set(result) == {"status", "worker"}


def test_worker_ping_result_is_json_serializable() -> None:
    json.dumps(document_tasks.worker_ping())


def test_process_document_rejects_invalid_uuid_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(coro):
        raise AssertionError("invalid document id should not run async processing")

    monkeypatch.setattr(document_tasks, "run_async", fail_if_called)

    result = document_tasks.process_document("not-a-uuid")

    assert result == {
        "document_id": "not-a-uuid",
        "outcome": DocumentProcessingOutcome.INVALID_DOCUMENT_ID.value,
        "status": None,
        "reason": document_tasks.INVALID_DOCUMENT_ID_REASON,
    }


def test_process_document_returns_not_found_for_missing_document() -> None:
    document_id = uuid4()
    FakeStatusService.claim_result = DocumentProcessingClaimResult(
        DocumentProcessingClaimOutcome.NOT_FOUND
    )

    result = run(document_tasks.process_document_async(document_id))

    assert result == {
        "document_id": str(document_id),
        "outcome": "NOT_FOUND",
        "status": None,
        "reason": "NOT_FOUND",
    }


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (DocumentProcessingClaimOutcome.DELETED, DocumentStatus.UPLOADED),
        (DocumentProcessingClaimOutcome.ARCHIVED, DocumentStatus.ARCHIVED),
        (DocumentProcessingClaimOutcome.ALREADY_READY, DocumentStatus.READY),
        (DocumentProcessingClaimOutcome.ALREADY_PROCESSING, DocumentStatus.PROCESSING),
    ],
)
def test_process_document_skips_ineligible_document_states(
    outcome: DocumentProcessingClaimOutcome,
    status: DocumentStatus,
) -> None:
    document_id = uuid4()
    FakeStatusService.claim_result = DocumentProcessingClaimResult(
        outcome,
        document_id=document_id,
        status=status,
    )

    result = run(document_tasks.process_document_async(document_id))

    expected_outcome = outcome.value
    if outcome == DocumentProcessingClaimOutcome.ALREADY_READY:
        expected_outcome = DocumentProcessingOutcome.ALREADY_READY.value
    assert result["outcome"] == expected_outcome
    assert result["status"] == status.value
    assert result["reason"] == expected_outcome


def test_process_document_skips_deleted_document() -> None:
    test_process_document_skips_ineligible_document_states(
        DocumentProcessingClaimOutcome.DELETED,
        DocumentStatus.UPLOADED,
    )


def test_process_document_skips_archived_document() -> None:
    test_process_document_skips_ineligible_document_states(
        DocumentProcessingClaimOutcome.ARCHIVED,
        DocumentStatus.ARCHIVED,
    )


def test_process_document_skips_ready_document() -> None:
    test_process_document_skips_ineligible_document_states(
        DocumentProcessingClaimOutcome.ALREADY_READY,
        DocumentStatus.READY,
    )


def test_process_document_skips_already_processing_document() -> None:
    test_process_document_skips_ineligible_document_states(
        DocumentProcessingClaimOutcome.ALREADY_PROCESSING,
        DocumentStatus.PROCESSING,
    )


@pytest.mark.parametrize("source_status", [DocumentStatus.UPLOADED, DocumentStatus.FAILED])
def test_process_document_claims_eligible_document(
    source_status: DocumentStatus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid4()
    FakeStatusService.claim_result = DocumentProcessingClaimResult(
        DocumentProcessingClaimOutcome.CLAIMED,
        document_id=document_id,
        status=DocumentStatus.PROCESSING,
    )
    monkeypatch.setattr(document_tasks, "execute_document_processing", successful_processing)

    result = run(document_tasks.process_document_async(document_id))

    assert source_status in {DocumentStatus.UPLOADED, DocumentStatus.FAILED}
    assert result["outcome"] == "READY"
    assert result["status"] == DocumentStatus.READY.value
    assert result["page_count"] == 2
    assert result["chunk_count"] == 3
    assert result["embedding_dimensions"] == 384


def test_process_document_claims_uploaded_document(monkeypatch: pytest.MonkeyPatch) -> None:
    test_process_document_claims_eligible_document(DocumentStatus.UPLOADED, monkeypatch)


def test_process_document_claims_failed_document(monkeypatch: pytest.MonkeyPatch) -> None:
    test_process_document_claims_eligible_document(DocumentStatus.FAILED, monkeypatch)


def test_permanent_processing_error_marks_document_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid4()
    FakeStatusService.claim_result = DocumentProcessingClaimResult(
        DocumentProcessingClaimOutcome.CLAIMED,
        document_id=document_id,
        status=DocumentStatus.PROCESSING,
    )

    async def fail_processing(document_id):
        raise PermanentDocumentProcessingError(
            code="PDF_NO_USABLE_TEXT",
            safe_message="No usable text was found in the PDF.",
        )

    monkeypatch.setattr(document_tasks, "execute_document_processing", fail_processing)

    result = run(document_tasks.process_document_async(document_id))

    assert result == {
        "document_id": str(document_id),
        "outcome": "FAILED",
        "status": DocumentStatus.FAILED.value,
        "reason": "PDF_NO_USABLE_TEXT",
    }
    assert FakeStatusService.failed_messages == ["No usable text was found in the PDF."]


def test_process_document_stores_sanitized_error() -> None:
    sanitized = sanitize_processing_error("  error\nwith\x00  spacing  ")

    assert sanitized == "error with spacing"
    assert "\n" not in sanitized
    assert "\x00" not in sanitized


def test_process_document_result_is_json_serializable() -> None:
    result = document_tasks.process_document("not-a-uuid")

    json.dumps(result)


def test_process_document_does_not_return_storage_key() -> None:
    result = document_tasks.process_document("not-a-uuid")

    assert "storage_key" not in result
    assert "checksum_sha256" not in result
    assert "absolute_path" not in result


def test_unexpected_error_returns_safe_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    document_id = uuid4()

    async def raise_unexpected(document_id):
        raise RuntimeError("CONFIDENTIAL_PIPELINE_TEST_MARKER")

    monkeypatch.setattr(document_tasks, "process_document_async", raise_unexpected)

    result = document_tasks.process_document(str(document_id))

    assert result == {
        "document_id": str(document_id),
        "outcome": "FAILED",
        "status": DocumentStatus.FAILED.value,
        "reason": document_tasks.DOCUMENT_PROCESSING_FAILED_REASON,
    }
    assert "CONFIDENTIAL_PIPELINE_TEST_MARKER" not in repr(result)
    assert "CONFIDENTIAL_PIPELINE_TEST_MARKER" not in caplog.text


class FakeRetryTask:
    def __init__(self, retries: int) -> None:
        self.request = SimpleNamespace(retries=retries)
        self.retry_call: dict[str, Any] | None = None

    def retry(self, *, exc: Exception, countdown: int, max_retries: int):
        self.retry_call = {
            "exc": exc,
            "countdown": countdown,
            "max_retries": max_retries,
        }
        raise RuntimeError("retry scheduled")


def test_transient_error_resets_processing_status_before_retry() -> None:
    document_id = uuid4()
    task = FakeRetryTask(retries=0)
    error = TransientDocumentProcessingError()

    with pytest.raises(RuntimeError, match="retry scheduled"):
        document_tasks._retry_or_return_final_failure(task, document_id, error)

    assert FakeStatusService.retry_resets == [str(document_id)]
    assert task.retry_call is not None
    assert task.retry_call["exc"] is error


def test_retry_count_is_bounded() -> None:
    document_id = uuid4()
    task = FakeRetryTask(retries=1)

    with pytest.raises(RuntimeError, match="retry scheduled"):
        document_tasks._retry_or_return_final_failure(
            task,
            document_id,
            TransientDocumentProcessingError(),
        )

    assert task.retry_call is not None
    assert task.retry_call["max_retries"] == document_tasks.get_settings().celery_task_max_retries
    assert task.retry_call["countdown"] >= 1


def test_retry_exhaustion_marks_failed() -> None:
    document_id = uuid4()
    task = FakeRetryTask(retries=document_tasks.get_settings().celery_task_max_retries)

    result = document_tasks._retry_or_return_final_failure(
        task,
        document_id,
        TransientDocumentProcessingError(code="TEMPORARY_MODEL_LOAD"),
    )

    assert result == {
        "document_id": str(document_id),
        "outcome": "FAILED",
        "status": DocumentStatus.FAILED.value,
        "reason": "TEMPORARY_MODEL_LOAD",
    }
    assert FakeStatusService.failed_messages == [
        "Document processing failed after retryable error."
    ]


def test_enqueue_document_processing_sends_only_document_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    expected_result = object()

    def fake_apply_async(*, args, queue):
        captured["args"] = args
        captured["queue"] = queue
        return expected_result

    monkeypatch.setattr(document_tasks.process_document, "apply_async", fake_apply_async)
    document_id = uuid4()

    result = document_tasks.enqueue_document_processing(document_id)

    assert result is expected_result
    assert captured["args"] == (str(document_id),)
    assert captured["queue"] == document_tasks.get_settings().celery_document_queue


def test_try_enqueue_document_processing_sanitizes_broker_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_enqueue(document_id):
        raise RuntimeError("redis://secret:password@localhost/1")

    monkeypatch.setattr(document_tasks, "enqueue_document_processing", fail_enqueue)

    enqueued = document_tasks.try_enqueue_document_processing(uuid4())

    assert enqueued is False
    assert "redis://" not in caplog.text
    assert "password" not in caplog.text
