"""add citation evidence text

Revision ID: cd124fa71c86
Revises: 20260803_0010
Create Date: 2026-08-17 22:17:14.339562
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cd124fa71c86"
down_revision: str | Sequence[str] | None = "20260803_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "message_citations",
        sa.Column(
            "evidence_text",
            sa.Text(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_message_citations_evidence_text_not_blank",
        "message_citations",
        ("evidence_text IS NULL OR char_length(btrim(evidence_text)) > 0"),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_message_citations_evidence_text_not_blank",
        "message_citations",
        type_="check",
    )

    op.drop_column(
        "message_citations",
        "evidence_text",
    )
