"""add chat sessions and messages

Revision ID: 38a6de8861c3
Revises: 20260718_0006
Create Date: 2026-07-19 18:57:25.033168
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "38a6de8861c3"
down_revision: str | Sequence[str] | None = "20260718_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

chat_message_role_enum = postgresql.ENUM(
    "USER",
    "ASSISTANT",
    "SYSTEM",
    name="chat_message_role",
    create_type=False,
)


def upgrade() -> None:
    postgresql.ENUM(
        "USER",
        "ASSISTANT",
        "SYSTEM",
        name="chat_message_role",
    ).create(op.get_bind(), checkfirst=True)
    op.create_table(
        "chat_sessions",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_sessions_user_updated",
        "chat_sessions",
        ["user_id", "updated_at"],
        unique=False,
    )
    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", chat_message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("retrieval_query", sa.Text(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(content)) > 0",
            name="ck_chat_messages_content_not_blank",
        ),
        sa.CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="ck_chat_messages_response_time_non_negative",
        ),
        sa.CheckConstraint(
            "prompt_tokens IS NULL OR prompt_tokens >= 0",
            name="ck_chat_messages_prompt_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "completion_tokens IS NULL OR completion_tokens >= 0",
            name="ck_chat_messages_completion_tokens_non_negative",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_messages_session_created",
        "chat_messages",
        ["session_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_user_updated", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    postgresql.ENUM(
        "USER",
        "ASSISTANT",
        "SYSTEM",
        name="chat_message_role",
    ).drop(op.get_bind(), checkfirst=True)
