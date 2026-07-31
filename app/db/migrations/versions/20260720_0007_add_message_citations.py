"""add message citations

Revision ID: 20260720_0007
Revises: 38a6de8861c3
Create Date: 2026-07-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260720_0007"
down_revision: str | Sequence[str] | None = "38a6de8861c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_citations",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("citation_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "citation_order >= 1",
            name="ck_message_citations_order_positive",
        ),
        sa.CheckConstraint("page_number > 0", name="ck_message_citations_page_positive"),
        sa.CheckConstraint(
            "char_length(btrim(excerpt)) > 0",
            name="ck_message_citations_excerpt_not_blank",
        ),
        sa.CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_message_citations_relevance_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id",
            "citation_order",
            name="uq_message_citations_message_order",
        ),
    )
    op.create_index(
        "ix_message_citations_message_order",
        "message_citations",
        ["message_id", "citation_order"],
        unique=False,
    )
    op.create_index(
        "ix_message_citations_document",
        "message_citations",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_message_citations_document", table_name="message_citations")
    op.drop_index("ix_message_citations_message_order", table_name="message_citations")
    op.drop_table("message_citations")
