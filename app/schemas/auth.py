from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.models import User, UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


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
    is_active: bool

    @classmethod
    def from_user(cls, user: User) -> AuthenticatedUserResponse:
        return cls.model_validate(user)


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
