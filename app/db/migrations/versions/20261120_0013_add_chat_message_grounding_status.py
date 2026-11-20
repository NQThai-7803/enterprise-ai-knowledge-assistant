"""store each assistant message's grounding status (BR-3)

Revision ID: 20261120_0013
Revises: 20261118_0012
Create Date: 2026-11-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0013"
down_revision: str | Sequence[str] | None = "20261118_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: messages written before this revision have no stored status.
    op.add_column(
        "chat_messages", sa.Column("grounding_status", sa.String(length=16), nullable=True)
    )
    op.create_check_constraint(
        "ck_chat_messages_grounding_status_known",
        "chat_messages",
        "grounding_status IS NULL OR grounding_status IN ('ANSWERED', 'NO_ANSWER')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_chat_messages_grounding_status_known", "chat_messages", type_="check")
    op.drop_column("chat_messages", "grounding_status")
