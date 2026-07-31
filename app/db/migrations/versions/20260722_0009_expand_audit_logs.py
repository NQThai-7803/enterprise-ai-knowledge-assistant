"""expand audit logs

Revision ID: 20260722_0009
Revises: 20260720_0008
Create Date: 2026-07-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260722_0009"
down_revision: str | Sequence[str] | None = "20260720_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "audit_logs",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    )
    op.add_column(
        "audit_logs",
        sa.Column(
            "outcome",
            sa.String(length=16),
            server_default=sa.text("'SUCCESS'"),
            nullable=False,
        ),
    )
    op.add_column("audit_logs", sa.Column("request_id", sa.String(length=128), nullable=True))
    op.add_column("audit_logs", sa.Column("error_code", sa.String(length=100), nullable=True))
    op.alter_column(
        "audit_logs",
        "entity_type",
        existing_type=sa.String(length=50),
        type_=sa.String(length=64),
        existing_nullable=True,
    )
    op.create_index("ix_audit_logs_created_id", "audit_logs", ["created_at", "id"], unique=False)
    op.create_index(
        "ix_audit_logs_action_created",
        "audit_logs",
        ["action", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_user_created",
        "audit_logs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_entity_created",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_outcome_created",
        "audit_logs",
        ["outcome", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.alter_column(
        "audit_logs",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        server_default=None,
    )
    op.drop_index("ix_audit_logs_outcome_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_id", table_name="audit_logs")
    op.alter_column(
        "audit_logs",
        "entity_type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
    op.drop_column("audit_logs", "error_code")
    op.drop_column("audit_logs", "request_id")
    op.drop_column("audit_logs", "outcome")
