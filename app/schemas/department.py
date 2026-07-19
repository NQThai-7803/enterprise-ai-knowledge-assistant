from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Department

DEPARTMENT_CODE_PATTERN = re.compile(r"^[A-Z0-9_-]+$")


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=120)
    code: str = Field(max_length=50)
    description: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value:
            msg = "Department name must not be empty."
            raise ValueError(msg)
        return value

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value:
            msg = "Department code must not be empty."
            raise ValueError(msg)
        if not DEPARTMENT_CODE_PATTERN.fullmatch(value):
            msg = (
                "Department code may contain only Latin letters, digits, underscores, and hyphens."
            )
            raise ValueError(msg)
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None and not value:
            msg = "Department name must not be empty."
            raise ValueError(msg)
        return value

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value:
            msg = "Department code must not be empty."
            raise ValueError(msg)
        if not DEPARTMENT_CODE_PATTERN.fullmatch(value):
            msg = (
                "Department code may contain only Latin letters, digits, underscores, and hyphens."
            )
            raise ValueError(msg)
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def reject_empty_payload(self) -> DepartmentUpdate:
        if not self.model_fields_set:
            msg = "At least one field must be provided."
            raise ValueError(msg)
        return self


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: str | None
    created_at: datetime

    @classmethod
    def from_department(cls, department: Department) -> DepartmentResponse:
        return cls.model_validate(department)
