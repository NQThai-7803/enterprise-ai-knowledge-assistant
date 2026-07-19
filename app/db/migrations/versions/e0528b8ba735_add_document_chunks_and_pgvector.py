"""add document chunks and pgvector

Revision ID: e0528b8ba735
Revises: 20260715_0005
Create Date: 2026-07-17 16:19:49.971647
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "e0528b8ba735"
down_revision: str | Sequence[str] | None = "20260715_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("page_numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("start_page", sa.Integer(), nullable=False),
        sa.Column("end_page", sa.Integer(), nullable=False),
        sa.Column("overlap_token_count", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding", VECTOR(384), nullable=False),
        sa.Column("embedding_provider", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name=op.f("ck_document_chunks_chunk_index_non_negative"),
        ),
        sa.CheckConstraint(
            "token_count > 0",
            name=op.f("ck_document_chunks_token_count_positive"),
        ),
        sa.CheckConstraint(
            "character_count > 0",
            name=op.f("ck_document_chunks_character_count_positive"),
        ),
        sa.CheckConstraint(
            "start_page > 0",
            name=op.f("ck_document_chunks_start_page_positive"),
        ),
        sa.CheckConstraint(
            "end_page >= start_page",
            name=op.f("ck_document_chunks_end_page_range"),
        ),
        sa.CheckConstraint(
            "overlap_token_count >= 0",
            name=op.f("ck_document_chunks_overlap_token_count_non_negative"),
        ),
        sa.CheckConstraint(
            "char_length(content_sha256) = 64",
            name=op.f("ck_document_chunks_content_sha256_length"),
        ),
        sa.CheckConstraint(
            "embedding_dimensions = 384",
            name=op.f("ck_document_chunks_embedding_dimensions_384"),
        ),
        sa.CheckConstraint(
            "cardinality(page_numbers) > 0",
            name=op.f("ck_document_chunks_page_numbers_not_empty"),
        ),
        sa.CheckConstraint(
            "array_position(page_numbers, NULL) IS NULL",
            name=op.f("ck_document_chunks_page_numbers_no_nulls"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_chunk_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_document_id_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_content_sha256",
        "document_chunks",
        ["content_sha256"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw_cosine "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw_cosine")
    op.drop_index("ix_document_chunks_content_sha256", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id_chunk_index", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    # The vector extension is intentionally not dropped; it may predate this migration.
