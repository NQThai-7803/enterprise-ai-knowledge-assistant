"""add feedback

Revision ID: 20260720_0008
Revises: 20260720_0007
Create Date: 2026-07-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260720_0008"
down_revision: str | Sequence[str] | None = "20260720_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

feedback_rating = postgresql.ENUM(
    "HELPFUL",
    "NOT_HELPFUL",
    name="feedback_rating",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE feedback_rating AS ENUM ('HELPFUL', 'NOT_HELPFUL');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.create_table(
        "feedback",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("rating", feedback_rating, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
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
            "reason IS NULL OR char_length(btrim(reason)) > 0",
            name="ck_feedback_reason_not_blank",
        ),
        sa.CheckConstraint(
            "reason IS NULL OR char_length(reason) <= 1000",
            name="ck_feedback_reason_max_length",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
    )
    op.create_index(
        "ix_feedback_user_updated",
        "feedback",
        ["user_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_rating_updated",
        "feedback",
        ["rating", "updated_at"],
        unique=False,
    )
    op.create_index("ix_feedback_message", "feedback", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feedback_message", table_name="feedback")
    op.drop_index("ix_feedback_rating_updated", table_name="feedback")
    op.drop_index("ix_feedback_user_updated", table_name="feedback")
    op.drop_table("feedback")
    op.execute("DROP TYPE IF EXISTS feedback_rating")
