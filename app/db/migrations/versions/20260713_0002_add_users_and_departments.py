"""add users and departments

Revision ID: 20260713_0002
Revises: 20260713_0001
Create Date: 2026-07-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0002"
down_revision: str | Sequence[str] | None = "20260713_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user_role = postgresql.ENUM("ADMIN", "MANAGER", "STAFF", name="user_role")
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_departments_code")),
        sa.UniqueConstraint("name", name=op.f("uq_departments_name")),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("ADMIN", "MANAGER", "STAFF", name="user_role", create_type=False),
            nullable=False,
        ),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_users_department_id_departments"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_department_id"), "users", ["department_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_department_id"), table_name="users")
    op.drop_table("users")
    op.drop_table("departments")

    user_role = postgresql.ENUM("ADMIN", "MANAGER", "STAFF", name="user_role")
    user_role.drop(op.get_bind(), checkfirst=True)
