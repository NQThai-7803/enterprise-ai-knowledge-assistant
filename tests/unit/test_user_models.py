from sqlalchemy import UniqueConstraint

from app.db.base import Base
from app.models import Department, RefreshToken, User, UserRole


def test_user_role_values() -> None:
    assert [role.value for role in UserRole] == ["ADMIN", "MANAGER", "STAFF"]


def test_department_table_registered() -> None:
    assert Department.__tablename__ == "departments"
    assert "departments" in Base.metadata.tables


def test_user_table_registered() -> None:
    assert User.__tablename__ == "users"
    assert "users" in Base.metadata.tables


def test_user_has_unique_email_constraint() -> None:
    unique_constraints = {
        constraint.name
        for constraint in User.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_users_email" in unique_constraints


def test_user_department_foreign_key_uses_set_null() -> None:
    foreign_key = next(iter(User.__table__.c.department_id.foreign_keys))

    assert foreign_key.target_fullname == "departments.id"
    assert foreign_key.ondelete == "SET NULL"


def test_refresh_token_table_registered() -> None:
    assert RefreshToken.__tablename__ == "refresh_tokens"
    assert "refresh_tokens" in Base.metadata.tables


def test_refresh_token_user_foreign_key_uses_cascade() -> None:
    foreign_key = next(iter(RefreshToken.__table__.c.user_id.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_refresh_token_has_no_raw_token_column() -> None:
    assert "raw_token" not in RefreshToken.__table__.columns
    assert "refresh_token" not in RefreshToken.__table__.columns
