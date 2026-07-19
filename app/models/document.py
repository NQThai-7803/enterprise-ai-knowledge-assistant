from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentAccessScope, DocumentStatus

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.document_chunk import DocumentChunk
    from app.models.document_permission import DocumentPermission
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_documents_storage_key"),
        CheckConstraint("file_size > 0", name="ck_documents_file_size_positive"),
        CheckConstraint(
            "char_length(checksum_sha256) = 64",
            name="ck_documents_checksum_sha256_length",
        ),
        CheckConstraint(
            "checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_documents_checksum_sha256_lower_hex",
        ),
        CheckConstraint(
            "("
            "access_scope = 'DEPARTMENT' AND department_id IS NOT NULL"
            ") OR ("
            "access_scope IN ('PRIVATE', 'ORGANIZATION') AND department_id IS NULL"
            ")",
            name="ck_documents_access_scope_department",
        ),
        Index("ix_documents_checksum_sha256", "checksum_sha256"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
        Index("ix_documents_status_is_deleted", "status", "is_deleted"),
        Index(
            "ix_documents_department_id_access_scope_is_deleted",
            "department_id",
            "access_scope",
            "is_deleted",
        ),
        Index("ix_documents_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        server_default=DocumentStatus.UPLOADED.value,
    )
    access_scope: Mapped[DocumentAccessScope] = mapped_column(
        Enum(DocumentAccessScope, name="document_access_scope"),
        nullable=False,
        default=DocumentAccessScope.PRIVATE,
        server_default=DocumentAccessScope.PRIVATE.value,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )

    department: Mapped[Department | None] = relationship()
    uploader: Mapped[User] = relationship(foreign_keys=[uploaded_by])
    permissions: Mapped[list[DocumentPermission]] = relationship(
        "DocumentPermission",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
