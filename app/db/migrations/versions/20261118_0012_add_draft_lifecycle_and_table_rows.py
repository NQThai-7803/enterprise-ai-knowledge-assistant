"""add the DRAFT lifecycle (DEC-033) and table-row chunks (DEC-034)

Revision ID: 20261118_0012
Revises: 20260822_0011
Create Date: 2026-11-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261118_0012"
down_revision: str | Sequence[str] | None = "20260822_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEARCH_VECTOR = "to_tsvector('simple'::regconfig, COALESCE(search_text, text))"


def upgrade() -> None:
    op.execute("ALTER TYPE document_lifecycle_status ADD VALUE IF NOT EXISTS 'DRAFT'")

    op.add_column(
        "document_chunks",
        sa.Column("chunk_kind", sa.String(length=16), server_default="TEXT", nullable=False),
    )
    op.add_column(
        "document_chunks",
        sa.Column("parent_chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("document_chunks", sa.Column("search_text", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_document_chunks_parent_chunk_id_document_chunks",
        "document_chunks",
        "document_chunks",
        ["parent_chunk_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "ck_document_chunks_chunk_kind", "document_chunks", "chunk_kind IN ('TEXT', 'TABLE_ROW')"
    )
    op.create_index("ix_document_chunks_parent_chunk_id", "document_chunks", ["parent_chunk_id"])
    op.execute(
        "CREATE INDEX ix_document_chunks_search_fts_simple ON document_chunks "
        f"USING gin ({_SEARCH_VECTOR})"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_search_fts_simple")
    op.drop_index("ix_document_chunks_parent_chunk_id", table_name="document_chunks")
    op.drop_constraint("ck_document_chunks_chunk_kind", "document_chunks", type_="check")
    op.drop_constraint(
        "fk_document_chunks_parent_chunk_id_document_chunks", "document_chunks", type_="foreignkey"
    )
    op.execute("DELETE FROM document_chunks WHERE chunk_kind <> 'TEXT'")
    op.drop_column("document_chunks", "search_text")
    op.drop_column("document_chunks", "parent_chunk_id")
    op.drop_column("document_chunks", "chunk_kind")

    # PostgreSQL cannot drop an enum value: rebuild the type without DRAFT.
    op.execute("UPDATE documents SET lifecycle_status = 'ACTIVE' WHERE lifecycle_status = 'DRAFT'")
    op.execute("ALTER TYPE document_lifecycle_status RENAME TO document_lifecycle_status_old")
    op.execute("CREATE TYPE document_lifecycle_status AS ENUM ('ACTIVE', 'SUPERSEDED', 'ARCHIVED')")
    op.execute("ALTER TABLE documents ALTER COLUMN lifecycle_status DROP DEFAULT")
    op.execute(
        "ALTER TABLE documents ALTER COLUMN lifecycle_status TYPE document_lifecycle_status "
        "USING lifecycle_status::text::document_lifecycle_status"
    )
    op.execute(
        "ALTER TABLE documents ALTER COLUMN lifecycle_status "
        "SET DEFAULT 'ACTIVE'::document_lifecycle_status"
    )
    op.execute("DROP TYPE document_lifecycle_status_old")
