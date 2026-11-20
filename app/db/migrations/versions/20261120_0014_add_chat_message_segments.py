"""store each answer's verified / unverified segments (BR-3 follow-up)

Revision ID: 20261120_0014
Revises: 20261120_0013
Create Date: 2026-11-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261120_0014"
down_revision: str | Sequence[str] | None = "20261120_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: user messages, NO_ANSWER messages and older answers have no segments.
    op.add_column("chat_messages", sa.Column("segments", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "segments")
