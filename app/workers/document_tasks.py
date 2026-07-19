from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from celery import Task
from celery.result import AsyncResult
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.models import DocumentStatus
from app.services.document_processing_pipeline import (
    DOCUMENT_PROCESSING_FAILED_MESSAGE,
    DOCUMENT_PROCESSING_TRANSIENT_FAILED_MESSAGE,
    DocumentProcessingOutcome,
    DocumentProcessingResult,
    PermanentDocumentProcessingError,
    TransientDocumentProcessingError,
    create_document_processing_pipeline,
)
from app.services.document_processing_status_service import (
    DocumentProcessingClaimOutcome,
    DocumentProcessingClaimResult,
    DocumentProcessingStatusService,
)
from app.workers.async_runner import run_async
from app.workers.celery_app import celery_app
from app.workers.worker_database import worker_session

logger = logging.getLogger(__name__)

DOCUMENT_PROCESSING_FAILED_REASON = "DOCUMENT_PROCESSING_FAILED"
DOCUMENT_PROCESSING_TRANSIENT_FAILED_REASON = "DOCUMENT_PROCESSING_TRANSIENT_FAILED"
INVALID_DOCUMENT_ID_REASON = DocumentProcessingOutcome.INVALID_DOCUMENT_ID.value


@celery_app.task(name="system.worker_ping")
def worker_ping() -> dict[str, str]:
    return {"status": "ok", "worker": "enterprise-ai"}


@celery_app.task(
    bind=True,
    name="documents.process_document",
    max_retries=get_settings().celery_task_max_retries,
    acks_late=get_settings().celery_task_acks_late,
    reject_on_worker_lost=get_settings().celery_task_reject_on_worker_lost,
)
def process_document(self: Task, document_id: str) -> dict[str, Any]:
    try:
        parsed_document_id = UUID(document_id)
    except (TypeError, ValueError):
        return _task_result(
            document_id=str(document_id),
            outcome=DocumentProcessingOutcome.INVALID_DOCUMENT_ID.value,
            status=None,
            reason=INVALID_DOCUMENT_ID_REASON,
        )

    try:
        return run_async(process_document_async(parsed_document_id))
    except OperationalError as exc:
        return _retry_or_return_final_failure(self, parsed_document_id, exc)
    except TransientDocumentProcessingError as exc:
        return _retry_or_return_final_failure(self, parsed_document_id, exc)
    except Exception as exc:
        logger.error(
            "Unexpected document processing failure.",
            extra={
                "document_id": str(parsed_document_id),
                "error_type": exc.__class__.__name__,
            },
        )
        try:
            run_async(_mark_unexpected_failure(parsed_document_id))
        except Exception as mark_exc:  # noqa: BLE001 - result must remain safe.
            logger.error(
                "Could not mark unexpected document processing failure.",
                extra={
                    "document_id": str(parsed_document_id),
                    "error_type": mark_exc.__class__.__name__,
                },
            )
        return _task_result(
            document_id=str(parsed_document_id),
            outcome=DocumentProcessingOutcome.FAILED.value,
            status=DocumentStatus.FAILED.value,
            reason=DOCUMENT_PROCESSING_FAILED_REASON,
        )


async def process_document_async(document_id: UUID) -> dict[str, Any]:
    async with worker_session() as session:
        claim = await DocumentProcessingStatusService(session).claim_document_for_processing(
            document_id
        )

    if claim.outcome != DocumentProcessingClaimOutcome.CLAIMED:
        return _claim_result_to_task_result(document_id, claim)

    try:
        result = await execute_document_processing(document_id)
        return result.to_task_result()
    except PermanentDocumentProcessingError as exc:
        if exc.mark_failed:
            async with worker_session() as session:
                await DocumentProcessingStatusService(session).mark_document_failed(
                    document_id,
                    exc.safe_message,
                )
        return _task_result(
            document_id=str(document_id),
            outcome=exc.outcome.value,
            status=exc.status.value if exc.status is not None else None,
            reason=exc.code,
        )


async def execute_document_processing(document_id: UUID) -> DocumentProcessingResult:
    pipeline = create_document_processing_pipeline()
    return await pipeline.process(document_id)


def enqueue_document_processing(document_id: UUID) -> AsyncResult:
    settings = get_settings()
    return process_document.apply_async(
        args=(str(document_id),),
        queue=settings.celery_document_queue,
    )


def try_enqueue_document_processing(document_id: UUID) -> bool:
    try:
        enqueue_document_processing(document_id)
    except Exception as exc:  # noqa: BLE001 - enqueue failure must not leak broker details.
        logger.warning(
            "Document processing enqueue failed.",
            extra={"document_id": str(document_id), "error_type": exc.__class__.__name__},
        )
        return False
    return True


async def _reset_document_for_retry(document_id: UUID) -> None:
    async with worker_session() as session:
        await DocumentProcessingStatusService(session).reset_document_for_retry(document_id)


async def _mark_transient_final_failure(document_id: UUID) -> None:
    async with worker_session() as session:
        await DocumentProcessingStatusService(session).mark_document_failed(
            document_id,
            DOCUMENT_PROCESSING_TRANSIENT_FAILED_MESSAGE,
        )


async def _mark_unexpected_failure(document_id: UUID) -> None:
    async with worker_session() as session:
        await DocumentProcessingStatusService(session).mark_document_failed(
            document_id,
            DOCUMENT_PROCESSING_FAILED_MESSAGE,
        )


def _retry_or_return_final_failure(
    task: Task,
    document_id: UUID,
    exc: Exception,
) -> dict[str, Any]:
    settings = get_settings()
    reason = getattr(exc, "code", DOCUMENT_PROCESSING_TRANSIENT_FAILED_REASON)
    if task.request.retries >= settings.celery_task_max_retries:
        run_async(_mark_transient_final_failure(document_id))
        return _task_result(
            document_id=str(document_id),
            outcome=DocumentProcessingOutcome.FAILED.value,
            status=DocumentStatus.FAILED.value,
            reason=str(reason),
        )

    try:
        run_async(_reset_document_for_retry(document_id))
    except Exception as reset_exc:
        logger.error(
            "Could not reset document before retry.",
            extra={"document_id": str(document_id), "error_type": reset_exc.__class__.__name__},
        )
    base_countdown = max(1, settings.celery_task_retry_backoff_seconds)
    countdown = base_countdown * (2**task.request.retries)
    raise task.retry(
        exc=exc,
        countdown=countdown,
        max_retries=settings.celery_task_max_retries,
    )


def _claim_result_to_task_result(
    document_id: UUID,
    claim: DocumentProcessingClaimResult,
) -> dict[str, Any]:
    outcome = _claim_outcome_to_processing_outcome(claim.outcome)
    return _task_result(
        document_id=str(document_id),
        outcome=outcome.value,
        status=claim.status.value if claim.status is not None else None,
        reason=outcome.value,
    )


def _claim_outcome_to_processing_outcome(
    outcome: DocumentProcessingClaimOutcome,
) -> DocumentProcessingOutcome:
    mapping = {
        DocumentProcessingClaimOutcome.NOT_FOUND: DocumentProcessingOutcome.NOT_FOUND,
        DocumentProcessingClaimOutcome.DELETED: DocumentProcessingOutcome.DELETED,
        DocumentProcessingClaimOutcome.ALREADY_PROCESSING: (
            DocumentProcessingOutcome.ALREADY_PROCESSING
        ),
        DocumentProcessingClaimOutcome.ALREADY_READY: DocumentProcessingOutcome.ALREADY_READY,
        DocumentProcessingClaimOutcome.ARCHIVED: DocumentProcessingOutcome.ARCHIVED,
        DocumentProcessingClaimOutcome.NOT_ELIGIBLE: DocumentProcessingOutcome.NOT_ELIGIBLE,
    }
    return mapping.get(outcome, DocumentProcessingOutcome.NOT_ELIGIBLE)


def _task_result(
    *,
    document_id: str,
    outcome: str,
    status: str | None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "document_id": document_id,
        "outcome": outcome,
        "status": status,
    }
    if reason is not None:
        payload["reason"] = reason
    return payload
