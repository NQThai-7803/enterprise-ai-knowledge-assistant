"""add document models

Revision ID: 20260715_0005
Revises: 20260714_0004
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260715_0005"
down_revision: str | Sequence[str] | None = "20260714_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    document_status = postgresql.ENUM(
        "UPLOADED",
        "PROCESSING",
        "READY",
        "FAILED",
        "ARCHIVED",
        name="document_status",
    )
    document_access_scope = postgresql.ENUM(
        "PRIVATE",
        "DEPARTMENT",
        "ORGANIZATION",
        name="document_access_scope",
    )
    document_permission_level = postgresql.ENUM(
        "VIEW",
        "EDIT",
        "MANAGE",
        name="document_permission_level",
    )
    document_status.create(op.get_bind(), checkfirst=True)
    document_access_scope.create(op.get_bind(), checkfirst=True)
    document_permission_level.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "UPLOADED",
                "PROCESSING",
                "READY",
                "FAILED",
                "ARCHIVED",
                name="document_status",
                create_type=False,
            ),
            server_default=sa.text("'UPLOADED'::document_status"),
            nullable=False,
        ),
        sa.Column(
            "access_scope",
            postgresql.ENUM(
                "PRIVATE",
                "DEPARTMENT",
                "ORGANIZATION",
                name="document_access_scope",
                create_type=False,
            ),
            server_default=sa.text("'PRIVATE'::document_access_scope"),
            nullable=False,
        ),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_size > 0",
            name=op.f("ck_documents_file_size_positive"),
        ),
        sa.CheckConstraint(
            "char_length(checksum_sha256) = 64",
            name=op.f("ck_documents_checksum_sha256_length"),
        ),
        sa.CheckConstraint(
            "checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_documents_checksum_sha256_lower_hex"),
        ),
        sa.CheckConstraint(
            "("
            "access_scope = 'DEPARTMENT' AND department_id IS NOT NULL"
            ") OR ("
            "access_scope IN ('PRIVATE', 'ORGANIZATION') AND department_id IS NULL"
            ")",
            name=op.f("ck_documents_access_scope_department"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_documents_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name=op.f("fk_documents_uploaded_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_documents_storage_key")),
    )
    op.create_index(
        op.f("ix_documents_checksum_sha256"),
        "documents",
        ["checksum_sha256"],
        unique=False,
    )
    op.create_index(op.f("ix_documents_created_at"), "documents", ["created_at"], unique=False)
    op.create_index(
        op.f("ix_documents_department_id_access_scope_is_deleted"),
        "documents",
        ["department_id", "access_scope", "is_deleted"],
        unique=False,
    )
    op.create_index(
        op.f("ix_documents_status_is_deleted"),
        "documents",
        ["status", "is_deleted"],
        unique=False,
    )
    op.create_index(op.f("ix_documents_uploaded_by"), "documents", ["uploaded_by"], unique=False)

    op.create_table(
        "document_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "permission",
            postgresql.ENUM(
                "VIEW",
                "EDIT",
                "MANAGE",
                name="document_permission_level",
                create_type=False,
            ),
            server_default=sa.text("'VIEW'::document_permission_level"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "("
            "user_id IS NOT NULL AND department_id IS NULL"
            ") OR ("
            "user_id IS NULL AND department_id IS NOT NULL"
            ")",
            name=op.f("ck_document_permissions_exactly_one_grantee"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_document_permissions_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_document_permissions_department_id_departments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_permissions_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_document_permissions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_permissions")),
        sa.UniqueConstraint(
            "document_id",
            "department_id",
            name=op.f("uq_document_permissions_document_department"),
        ),
        sa.UniqueConstraint(
            "document_id",
            "user_id",
            name=op.f("uq_document_permissions_document_user"),
        ),
    )
    op.create_index(
        op.f("ix_document_permissions_created_by"),
        "document_permissions",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_permissions_department_id"),
        "document_permissions",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_permissions_document_id"),
        "document_permissions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_permissions_user_id"),
        "document_permissions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_permissions_user_id"), table_name="document_permissions")
    op.drop_index(op.f("ix_document_permissions_document_id"), table_name="document_permissions")
    op.drop_index(
        op.f("ix_document_permissions_department_id"),
        table_name="document_permissions",
    )
    op.drop_index(op.f("ix_document_permissions_created_by"), table_name="document_permissions")
    op.drop_table("document_permissions")

    op.drop_index(op.f("ix_documents_uploaded_by"), table_name="documents")
    op.drop_index(op.f("ix_documents_status_is_deleted"), table_name="documents")
    op.drop_index(
        op.f("ix_documents_department_id_access_scope_is_deleted"),
        table_name="documents",
    )
    op.drop_index(op.f("ix_documents_created_at"), table_name="documents")
    op.drop_index(op.f("ix_documents_checksum_sha256"), table_name="documents")
    op.drop_table("documents")

    document_permission_level = postgresql.ENUM(
        "VIEW",
        "EDIT",
        "MANAGE",
        name="document_permission_level",
    )
    document_access_scope = postgresql.ENUM(
        "PRIVATE",
        "DEPARTMENT",
        "ORGANIZATION",
        name="document_access_scope",
    )
    document_status = postgresql.ENUM(
        "UPLOADED",
        "PROCESSING",
        "READY",
        "FAILED",
        "ARCHIVED",
        name="document_status",
    )
    document_permission_level.drop(op.get_bind(), checkfirst=True)
    document_access_scope.drop(op.get_bind(), checkfirst=True)
    document_status.drop(op.get_bind(), checkfirst=True)
