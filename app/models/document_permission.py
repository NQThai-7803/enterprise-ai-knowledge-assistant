from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentPermissionLevel

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.document import Document
    from app.models.user import User


class DocumentPermission(Base):
    __tablename__ = "document_permissions"
    __table_args__ = (
        CheckConstraint(
            "("
            "user_id IS NOT NULL AND department_id IS NULL"
            ") OR ("
            "user_id IS NULL AND department_id IS NOT NULL"
            ")",
            name="ck_document_permissions_exactly_one_grantee",
        ),
        UniqueConstraint(
            "document_id",
            "user_id",
            name="uq_document_permissions_document_user",
        ),
        UniqueConstraint(
            "document_id",
            "department_id",
            name="uq_document_permissions_document_department",
        ),
        Index("ix_document_permissions_document_id", "document_id"),
        Index("ix_document_permissions_user_id", "user_id"),
        Index("ix_document_permissions_department_id", "department_id"),
        Index("ix_document_permissions_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
    )
    permission: Mapped[DocumentPermissionLevel] = mapped_column(
        Enum(DocumentPermissionLevel, name="document_permission_level"),
        nullable=False,
        default=DocumentPermissionLevel.VIEW,
        server_default=DocumentPermissionLevel.VIEW.value,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="permissions")
    user: Mapped[User | None] = relationship(foreign_keys=[user_id])
    department: Mapped[Department | None] = relationship()
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
