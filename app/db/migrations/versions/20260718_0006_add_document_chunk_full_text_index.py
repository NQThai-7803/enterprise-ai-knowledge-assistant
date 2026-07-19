"""add document chunk full text index

Revision ID: 20260718_0006
Revises: e0528b8ba735
Create Date: 2026-07-18 00:06:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260718_0006"
down_revision: str | Sequence[str] | None = "e0528b8ba735"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_document_chunks_text_fts_simple "
        "ON document_chunks USING gin (to_tsvector('simple'::regconfig, text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_text_fts_simple")
