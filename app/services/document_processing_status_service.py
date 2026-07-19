from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentStatus

MAX_PROCESSING_ERROR_LENGTH = 1000


class DocumentProcessingClaimOutcome(StrEnum):
    CLAIMED = "CLAIMED"
    NOT_FOUND = "NOT_FOUND"
    DELETED = "DELETED"
    ALREADY_PROCESSING = "ALREADY_PROCESSING"
    ALREADY_READY = "ALREADY_READY"
    ARCHIVED = "ARCHIVED"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


@dataclass(frozen=True)
class DocumentProcessingClaimResult:
    outcome: DocumentProcessingClaimOutcome
    document_id: UUID | None = None
    status: DocumentStatus | None = None


class DocumentProcessingStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim_document_for_processing(
        self,
        document_id: UUID,
    ) -> DocumentProcessingClaimResult:
        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.is_deleted.is_(False),
                Document.status.in_((DocumentStatus.UPLOADED, DocumentStatus.FAILED)),
            )
            .values(
                status=DocumentStatus.PROCESSING,
                error_message=None,
                updated_at=func.now(),
            )
            .returning(Document.id)
        )
        result = await self.session.execute(statement)
        claimed_id = result.scalar_one_or_none()
        if claimed_id is not None:
            await self.session.commit()
            return DocumentProcessingClaimResult(
                outcome=DocumentProcessingClaimOutcome.CLAIMED,
                document_id=claimed_id,
                status=DocumentStatus.PROCESSING,
            )

        await self.session.rollback()
        document_state = await self.session.execute(
            select(Document.status, Document.is_deleted).where(Document.id == document_id)
        )
        row = document_state.one_or_none()
        await self.session.rollback()
        if row is None:
            return DocumentProcessingClaimResult(DocumentProcessingClaimOutcome.NOT_FOUND)

        status, is_deleted = row
        if is_deleted:
            return DocumentProcessingClaimResult(
                DocumentProcessingClaimOutcome.DELETED,
                document_id=document_id,
                status=status,
            )
        if status == DocumentStatus.PROCESSING:
            outcome = DocumentProcessingClaimOutcome.ALREADY_PROCESSING
        elif status == DocumentStatus.READY:
            outcome = DocumentProcessingClaimOutcome.ALREADY_READY
        elif status == DocumentStatus.ARCHIVED:
            outcome = DocumentProcessingClaimOutcome.ARCHIVED
        else:
            outcome = DocumentProcessingClaimOutcome.NOT_ELIGIBLE
        return DocumentProcessingClaimResult(
            outcome=outcome,
            document_id=document_id,
            status=status,
        )

    async def mark_document_failed(
        self,
        document_id: UUID,
        error_message: str,
    ) -> bool:
        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.is_deleted.is_(False),
                Document.status.in_(
                    (
                        DocumentStatus.UPLOADED,
                        DocumentStatus.PROCESSING,
                        DocumentStatus.FAILED,
                    )
                ),
            )
            .values(
                status=DocumentStatus.FAILED,
                error_message=sanitize_processing_error(error_message),
                updated_at=func.now(),
            )
            .returning(Document.id)
        )
        result = await self.session.execute(statement)
        changed = result.scalar_one_or_none() is not None
        await self.session.commit()
        return changed

    async def reset_document_for_retry(self, document_id: UUID) -> bool:
        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.is_deleted.is_(False),
                Document.status == DocumentStatus.PROCESSING,
            )
            .values(
                status=DocumentStatus.UPLOADED,
                error_message=None,
                updated_at=func.now(),
            )
            .returning(Document.id)
        )
        result = await self.session.execute(statement)
        changed = result.scalar_one_or_none() is not None
        await self.session.commit()
        return changed


def sanitize_processing_error(error_message: str) -> str:
    sanitized = " ".join(error_message.replace("\x00", " ").split())
    if not sanitized:
        sanitized = "Document processing failed."
    return sanitized[:MAX_PROCESSING_ERROR_LENGTH]
