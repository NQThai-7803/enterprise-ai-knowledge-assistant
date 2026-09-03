from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CitationSourceType

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk


class MessageCitation(Base):
    __tablename__ = "message_citations"
    __table_args__ = (
        CheckConstraint("citation_order >= 1", name="ck_message_citations_order_positive"),
        CheckConstraint("page_number > 0", name="ck_message_citations_page_positive"),
        CheckConstraint(
            "char_length(btrim(excerpt)) > 0",
            name="ck_message_citations_excerpt_not_blank",
        ),
        CheckConstraint(
            "evidence_text IS NULL OR char_length(btrim(evidence_text)) > 0",
            name="ck_message_citations_evidence_text_not_blank",
        ),
        CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_message_citations_relevance_score_range",
        ),
        CheckConstraint(
            "source_type IN ('INTERNAL', 'WEB')",
            name="ck_message_citations_source_type_valid",
        ),
        CheckConstraint(
            "source_type != 'INTERNAL' OR document_id IS NOT NULL",
            name="ck_message_citations_internal_document_required",
        ),
        CheckConstraint(
            "source_type != 'WEB' OR ("
            "document_id IS NULL AND chunk_id IS NULL "
            "AND source_url IS NOT NULL AND char_length(btrim(source_url)) > 0 "
            "AND source_title IS NOT NULL AND char_length(btrim(source_title)) > 0"
            ")",
            name="ck_message_citations_web_source_required",
        ),
        UniqueConstraint(
            "message_id",
            "citation_order",
            name="uq_message_citations_message_order",
        ),
        Index("ix_message_citations_message_order", "message_id", "citation_order"),
        Index("ix_message_citations_document", "document_id"),
        Index("ix_message_citations_source_type", "source_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CitationSourceType.INTERNAL.value,
        server_default=CitationSourceType.INTERNAL.value,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    citation_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped[ChatMessage] = relationship("ChatMessage", back_populates="citations")
    document: Mapped[Document | None] = relationship(
        "Document",
        back_populates="message_citations",
    )
    chunk: Mapped[DocumentChunk | None] = relationship(
        "DocumentChunk",
        back_populates="message_citations",
    )
