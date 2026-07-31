from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import build_accessible_document_filter
from app.models import Document, DocumentChunk, DocumentStatus, User


@dataclass(frozen=True, slots=True)
class PermittedCitationSourceRow:
    chunk_id: UUID
    document_id: UUID
    document_title: str


async def get_permitted_ready_chunks_by_ids(
    session: AsyncSession,
    *,
    chunk_ids: Sequence[UUID],
    current_user: User,
) -> tuple[PermittedCitationSourceRow, ...]:
    unique_chunk_ids = tuple(dict.fromkeys(chunk_ids))
    if not unique_chunk_ids:
        return ()
    statement = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id.label("document_id"),
            Document.title.label("document_title"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.id.in_(unique_chunk_ids),
            Document.status == DocumentStatus.READY,
            build_accessible_document_filter(current_user),
        )
    )
    rows = (await session.execute(statement)).all()
    return tuple(
        PermittedCitationSourceRow(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
        )
        for row in rows
    )
