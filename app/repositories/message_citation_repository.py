from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import build_accessible_document_filter
from app.models import ChatMessage, ChatMessageRole, Document, MessageCitation, User


@dataclass(frozen=True, slots=True)
class MessageCitationRow:
    message_id: UUID
    document_id: UUID
    document_title: str
    chunk_id: UUID | None
    page_number: int
    excerpt: str = field(repr=False)
    relevance_score: float | None
    citation_order: int


async def create_many(
    session: AsyncSession,
    *,
    assistant_message: ChatMessage,
    citations: Sequence[object],
) -> tuple[MessageCitation, ...]:
    if assistant_message.role != ChatMessageRole.ASSISTANT:
        msg = "citations can only be attached to ASSISTANT messages."
        raise ValueError(msg)
    orders = [citation.citation_order for citation in citations]
    if len(orders) != len(set(orders)):
        msg = "citation orders must be unique."
        raise ValueError(msg)
    rows: list[MessageCitation] = []
    for citation in sorted(citations, key=lambda item: item.citation_order):
        relevance_score = citation.relevance_score
        rows.append(
            MessageCitation(
                message_id=assistant_message.id,
                document_id=citation.document_id,
                chunk_id=citation.chunk_id,
                page_number=citation.page_number,
                excerpt=citation.excerpt,
                relevance_score=(
                    None if relevance_score is None else Decimal(str(relevance_score))
                ),
                citation_order=citation.citation_order,
            )
        )
    session.add_all(rows)
    return tuple(rows)


async def list_by_message_ids(
    session: AsyncSession,
    *,
    message_ids: Sequence[UUID],
    current_user: User,
) -> tuple[MessageCitationRow, ...]:
    unique_message_ids = tuple(dict.fromkeys(message_ids))
    if not unique_message_ids:
        return ()
    statement = (
        select(
            MessageCitation.message_id,
            MessageCitation.document_id,
            Document.title.label("document_title"),
            MessageCitation.chunk_id,
            MessageCitation.page_number,
            MessageCitation.excerpt,
            MessageCitation.relevance_score,
            MessageCitation.citation_order,
        )
        .join(Document, Document.id == MessageCitation.document_id)
        .where(
            MessageCitation.message_id.in_(unique_message_ids),
            build_accessible_document_filter(current_user),
        )
        .order_by(MessageCitation.message_id.asc(), MessageCitation.citation_order.asc())
    )
    rows = (await session.execute(statement)).all()
    return tuple(_row_from_result(row) for row in rows)


async def list_by_message(
    session: AsyncSession,
    *,
    message_id: UUID,
    current_user: User,
) -> tuple[MessageCitationRow, ...]:
    return await list_by_message_ids(
        session,
        message_ids=(message_id,),
        current_user=current_user,
    )


def _row_from_result(row) -> MessageCitationRow:  # noqa: ANN001
    relevance = row.relevance_score
    return MessageCitationRow(
        message_id=row.message_id,
        document_id=row.document_id,
        document_title=row.document_title,
        chunk_id=row.chunk_id,
        page_number=row.page_number,
        excerpt=row.excerpt,
        relevance_score=None if relevance is None else float(relevance),
        citation_order=row.citation_order,
    )
