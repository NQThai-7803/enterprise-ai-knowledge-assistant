from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    literal_column,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.embeddings.constants import EMBEDDING_SCHEMA_DIMENSIONS

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.message_citation import MessageCitation


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index_non_negative"),
        CheckConstraint("token_count > 0", name="ck_document_chunks_token_count_positive"),
        CheckConstraint("character_count > 0", name="ck_document_chunks_character_count_positive"),
        CheckConstraint("start_page > 0", name="ck_document_chunks_start_page_positive"),
        CheckConstraint("end_page >= start_page", name="ck_document_chunks_end_page_range"),
        CheckConstraint(
            "overlap_token_count >= 0",
            name="ck_document_chunks_overlap_token_count_non_negative",
        ),
        CheckConstraint(
            "char_length(content_sha256) = 64",
            name="ck_document_chunks_content_sha256_length",
        ),
        CheckConstraint(
            "embedding_dimensions = 384",
            name="ck_document_chunks_embedding_dimensions_384",
        ),
        CheckConstraint(
            "cardinality(page_numbers) > 0",
            name="ck_document_chunks_page_numbers_not_empty",
        ),
        CheckConstraint(
            "array_position(page_numbers, NULL) IS NULL",
            name="ck_document_chunks_page_numbers_no_nulls",
        ),
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_chunk_index",
        ),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_document_id_chunk_index", "document_id", "chunk_index"),
        Index("ix_document_chunks_content_sha256", "content_sha256"),
        Index(
            "ix_document_chunks_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_document_chunks_text_fts_simple",
            func.to_tsvector(literal_column("'simple'::regconfig"), literal_column("text")),
            postgresql_using="gin",
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    start_page: Mapped[int] = mapped_column(Integer, nullable=False)
    end_page: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(EMBEDDING_SCHEMA_DIMENSIONS), nullable=False
    )
    embedding_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
    message_citations: Mapped[list[MessageCitation]] = relationship(
        "MessageCitation",
        back_populates="chunk",
        passive_deletes=True,
    )
