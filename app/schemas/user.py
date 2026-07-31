from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.models import User, UserRole
from app.schemas.email import normalize_email_address


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    full_name: str = Field(max_length=200)
    password: SecretStr = Field(min_length=12)
    role: UserRole
    department_id: UUID | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str:
        return normalize_email_address(value)

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_full_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        if not value:
            msg = "Full name must not be empty."
            raise ValueError(msg)
        return value


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    full_name: str | None = Field(default=None, max_length=200)
    role: UserRole | None = None
    department_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str | None:
        if value is None:
            return None
        return normalize_email_address(value)

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_full_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is not None and not value:
            msg = "Full name must not be empty."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def reject_empty_payload(self) -> UserUpdate:
        if not self.model_fields_set:
            msg = "At least one field must be provided."
            raise ValueError(msg)
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: UserRole
    department_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        return cls.model_validate(user)
