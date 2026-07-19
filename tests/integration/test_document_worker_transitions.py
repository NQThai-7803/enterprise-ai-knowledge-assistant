from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Document, DocumentAccessScope, DocumentStatus, User, UserRole
from app.services.document_processing_pipeline import (
    DocumentProcessingOutcome,
    DocumentProcessingResult,
)
from app.services.document_processing_status_service import (
    DocumentProcessingClaimOutcome,
    DocumentProcessingStatusService,
)
from app.workers import document_tasks
from app.workers.document_tasks import _mark_transient_final_failure, process_document_async

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def create_user(session: AsyncSession) -> User:
    user = User(
        email=f"worker-{uuid.uuid4()}@example.com",
        full_name="Worker Test User",
        hashed_password="not-used-by-worker-tests",
        role=UserRole.STAFF,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_document(
    session: AsyncSession,
    *,
    uploader: User,
    status: DocumentStatus = DocumentStatus.UPLOADED,
    is_deleted: bool = False,
    error_message: str | None = None,
) -> Document:
    document = Document(
        title="Worker transition document",
        description="Worker transition test",
        original_filename="worker.pdf",
        storage_key=f"documents/worker/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
        status=status,
        access_scope=DocumentAccessScope.PRIVATE,
        uploaded_by=uploader.id,
        error_message=error_message,
        is_deleted=is_deleted,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def get_document_state(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> tuple[DocumentStatus, str | None]:
    row = await session.execute(
        select(Document.status, Document.error_message).where(Document.id == document_id)
    )
    status, error_message = row.one()
    return status, error_message


def test_uploaded_document_transitions_to_processing(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(session, uploader=uploader)

            claim = await DocumentProcessingStatusService(session).claim_document_for_processing(
                document.id
            )
            await session.refresh(document)

            assert claim.outcome == DocumentProcessingClaimOutcome.CLAIMED
            assert document.status == DocumentStatus.PROCESSING
            assert document.error_message is None

    run_async(scenario())


def test_failed_document_can_transition_to_processing(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(
                session,
                uploader=uploader,
                status=DocumentStatus.FAILED,
                error_message="previous safe error",
            )

            claim = await DocumentProcessingStatusService(session).claim_document_for_processing(
                document.id
            )
            await session.refresh(document)

            assert claim.outcome == DocumentProcessingClaimOutcome.CLAIMED
            assert document.status == DocumentStatus.PROCESSING
            assert document.error_message is None

    run_async(scenario())


@pytest.mark.parametrize(
    ("status", "expected_outcome"),
    [
        (DocumentStatus.READY, DocumentProcessingClaimOutcome.ALREADY_READY),
        (DocumentStatus.ARCHIVED, DocumentProcessingClaimOutcome.ARCHIVED),
    ],
)
def test_terminal_document_cannot_transition_to_processing(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    status: DocumentStatus,
    expected_outcome: DocumentProcessingClaimOutcome,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(session, uploader=uploader, status=status)

            claim = await DocumentProcessingStatusService(session).claim_document_for_processing(
                document.id
            )
            await session.refresh(document)

            assert claim.outcome == expected_outcome
            assert document.status == status

    run_async(scenario())


def test_ready_document_cannot_transition_to_processing(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    test_terminal_document_cannot_transition_to_processing(
        async_session_factory_for_tests,
        DocumentStatus.READY,
        DocumentProcessingClaimOutcome.ALREADY_READY,
    )


def test_archived_document_cannot_transition_to_processing(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    test_terminal_document_cannot_transition_to_processing(
        async_session_factory_for_tests,
        DocumentStatus.ARCHIVED,
        DocumentProcessingClaimOutcome.ARCHIVED,
    )


def test_deleted_document_cannot_transition_to_processing(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(session, uploader=uploader, is_deleted=True)

            claim = await DocumentProcessingStatusService(session).claim_document_for_processing(
                document.id
            )
            await session.refresh(document)

            assert claim.outcome == DocumentProcessingClaimOutcome.DELETED
            assert document.status == DocumentStatus.UPLOADED

    run_async(scenario())


def test_processing_document_cannot_be_claimed_twice(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(session, uploader=uploader)
            service = DocumentProcessingStatusService(session)

            first_claim = await service.claim_document_for_processing(document.id)
            second_claim = await service.claim_document_for_processing(document.id)

            assert first_claim.outcome == DocumentProcessingClaimOutcome.CLAIMED
            assert second_claim.outcome == DocumentProcessingClaimOutcome.ALREADY_PROCESSING

    run_async(scenario())


def test_only_one_concurrent_claim_succeeds(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as setup_session:
            uploader = await create_user(setup_session)
            document = await create_document(setup_session, uploader=uploader)
            document_id = document.id

        async with (
            async_session_factory_for_tests() as session_one,
            async_session_factory_for_tests() as session_two,
        ):
            claims = await asyncio.gather(
                DocumentProcessingStatusService(session_one).claim_document_for_processing(
                    document_id
                ),
                DocumentProcessingStatusService(session_two).claim_document_for_processing(
                    document_id
                ),
            )

        outcomes = [claim.outcome for claim in claims]
        assert outcomes.count(DocumentProcessingClaimOutcome.CLAIMED) == 1
        assert outcomes.count(DocumentProcessingClaimOutcome.ALREADY_PROCESSING) == 1

    run_async(scenario())


def test_claimed_worker_invokes_processing_pipeline(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(session, uploader=uploader)
            document_id = document.id

        async def fake_execute_pipeline(document_id: uuid.UUID) -> DocumentProcessingResult:
            async with async_session_factory_for_tests() as session:
                document = await session.get(Document, document_id)
                assert document is not None
                assert document.status == DocumentStatus.PROCESSING
                document.status = DocumentStatus.READY
                document.error_message = None
                await session.commit()
            return DocumentProcessingResult(
                document_id=document_id,
                outcome=DocumentProcessingOutcome.READY,
                status=DocumentStatus.READY,
                page_count=1,
                chunk_count=1,
                total_tokens=3,
                embedding_dimensions=384,
            )

        monkeypatch.setattr(document_tasks, "execute_document_processing", fake_execute_pipeline)
        result = await process_document_async(document_id)

        async with async_session_factory_for_tests() as session:
            status, error_message = await get_document_state(session, document_id)

        assert result["outcome"] == "READY"
        assert result["status"] == DocumentStatus.READY.value
        assert status == DocumentStatus.READY
        assert error_message is None

    run_async(scenario())


def test_failure_clears_or_sets_sanitized_error_message(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(
                session,
                uploader=uploader,
                status=DocumentStatus.PROCESSING,
            )

            await DocumentProcessingStatusService(session).mark_document_failed(
                document.id,
                "  safe\nmessage\x00 with   spacing  ",
            )
            await session.refresh(document)

            assert document.status == DocumentStatus.FAILED
            assert document.error_message == "safe message with spacing"

    run_async(scenario())


def test_retry_reset_returns_document_to_uploaded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(
                session,
                uploader=uploader,
                status=DocumentStatus.PROCESSING,
                error_message="temporary safe error",
            )

            changed = await DocumentProcessingStatusService(session).reset_document_for_retry(
                document.id
            )
            await session.refresh(document)

            assert changed is True
            assert document.status == DocumentStatus.UPLOADED
            assert document.error_message is None

    run_async(scenario())


def test_final_retry_failure_marks_document_failed(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session)
            document = await create_document(
                session,
                uploader=uploader,
                status=DocumentStatus.PROCESSING,
            )
            document_id = document.id

        await _mark_transient_final_failure(document_id)

        async with async_session_factory_for_tests() as session:
            status, error_message = await get_document_state(session, document_id)

        assert status == DocumentStatus.FAILED
        assert error_message == "Document processing failed after retryable error."

    run_async(scenario())
