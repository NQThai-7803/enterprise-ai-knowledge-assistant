from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.models import User, UserRole
from app.schemas.email import normalize_email_address


class LoginRequest(BaseModel):
    email: str
    password: SecretStr = Field(min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str:
        return normalize_email_address(value)


class RefreshTokenRequest(BaseModel):
    refresh_token: SecretStr = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: SecretStr = Field(min_length=1)


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: UserRole
    department_id: UUID | None
    # BR-4: the name of the user's own Department; null without one.
    department_name: str | None = None
    is_active: bool

    @classmethod
    def from_user(
        cls, user: User, *, department_name: str | None = None
    ) -> AuthenticatedUserResponse:
        return cls.model_validate(user).model_copy(update={"department_name": department_name})


class TokenPairData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthenticatedUserResponse


class TokenPairResponse(BaseModel):
    data: TokenPairData
    meta: None = None


class AuthenticatedUserDataResponse(BaseModel):
    data: AuthenticatedUserResponse
    meta: None = None
