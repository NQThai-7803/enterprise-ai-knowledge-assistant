from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate


def test_user_create_normalizes_email() -> None:
    payload = UserCreate(
        email=" Staff@Example.COM ",
        full_name="Staff User",
        password="StrongPassword123!",
        role=UserRole.STAFF,
        department_id=uuid4(),
    )

    assert str(payload.email) == "staff@example.com"


def test_user_create_trims_full_name() -> None:
    payload = UserCreate(
        email="staff@example.com",
        full_name="  Staff User  ",
        password="StrongPassword123!",
        role=UserRole.STAFF,
        department_id=uuid4(),
    )

    assert payload.full_name == "Staff User"


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            email="staff@example.com",
            full_name="Staff User",
            password="short",
            role=UserRole.STAFF,
            department_id=uuid4(),
        )


def test_user_create_rejects_empty_full_name() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            email="staff@example.com",
            full_name="   ",
            password="StrongPassword123!",
            role=UserRole.STAFF,
            department_id=uuid4(),
        )


def test_user_update_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        UserUpdate()


def test_user_update_does_not_accept_password() -> None:
    with pytest.raises(ValidationError):
        UserUpdate(password="StrongPassword123!")  # type: ignore[call-arg]


def test_user_response_does_not_include_hashed_password() -> None:
    response = UserResponse(
        id=uuid4(),
        email="staff@example.com",
        full_name="Staff User",
        role=UserRole.STAFF,
        department_id=None,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    dumped = response.model_dump()
    assert "hashed_password" not in dumped
    assert "password" not in dumped
