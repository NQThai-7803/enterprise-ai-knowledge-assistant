"""add generic document authority metadata

Revision ID: 20260822_0011
Revises: cd124fa71c86
Create Date: 2026-08-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260822_0011"
down_revision: str | Sequence[str] | None = "cd124fa71c86"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    lifecycle_status = postgresql.ENUM(
        "ACTIVE",
        "SUPERSEDED",
        "ARCHIVED",
        name="document_lifecycle_status",
    )
    lifecycle_status.create(op.get_bind(), checkfirst=True)

    op.add_column("documents", sa.Column("document_code", sa.String(length=128), nullable=True))
    op.add_column("documents", sa.Column("document_version", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("effective_from", sa.Date(), nullable=True))
    op.add_column("documents", sa.Column("effective_to", sa.Date(), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "lifecycle_status",
            postgresql.ENUM(
                "ACTIVE",
                "SUPERSEDED",
                "ARCHIVED",
                name="document_lifecycle_status",
                create_type=False,
            ),
            server_default=sa.text("'ACTIVE'::document_lifecycle_status"),
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("supersedes_document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_supersedes_document_id_documents",
        "documents",
        "documents",
        ["supersedes_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_documents_document_code_not_blank",
        "documents",
        "document_code IS NULL OR char_length(btrim(document_code)) > 0",
    )
    op.create_check_constraint(
        "ck_documents_document_version_not_blank",
        "documents",
        "document_version IS NULL OR char_length(btrim(document_version)) > 0",
    )
    op.create_check_constraint(
        "ck_documents_effective_dates_ordered",
        "documents",
        "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
    )
    op.create_index(
        "ix_documents_authority",
        "documents",
        ["document_code", "lifecycle_status", "effective_from", "effective_to"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_authority", table_name="documents")
    op.drop_constraint("ck_documents_effective_dates_ordered", "documents", type_="check")
    op.drop_constraint("ck_documents_document_version_not_blank", "documents", type_="check")
    op.drop_constraint("ck_documents_document_code_not_blank", "documents", type_="check")
    op.drop_constraint(
        "fk_documents_supersedes_document_id_documents",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "supersedes_document_id")
    op.drop_column("documents", "lifecycle_status")
    op.drop_column("documents", "effective_to")
    op.drop_column("documents", "effective_from")
    op.drop_column("documents", "document_version")
    op.drop_column("documents", "document_code")
    sa.Enum(name="document_lifecycle_status").drop(op.get_bind(), checkfirst=True)
