from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    Document,
    DocumentAccessScope,
    DocumentPermission,
    DocumentPermissionLevel,
    DocumentStatus,
)


class DocumentUploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=255)
    description: str | None = None
    access_scope: DocumentAccessScope
    department_id: UUID | None = None

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value:
            msg = "Document title must not be empty."
            raise ValueError(msg)
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class DocumentSafeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    original_filename: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    access_scope: DocumentAccessScope
    department_id: UUID | None
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: Document):
        return cls.model_validate(document)


class DocumentUploadResponse(DocumentSafeResponse):
    pass


class DocumentListItem(DocumentSafeResponse):
    pass


class DocumentDetailResponse(DocumentSafeResponse):
    pass


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DocumentStatus
    error_message: str | None
    updated_at: datetime

    @classmethod
    def from_document(cls, document: Document) -> DocumentStatusResponse:
        return cls.model_validate(document)


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    access_scope: DocumentAccessScope | None = None
    department_id: UUID | None = None

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is not None and not value:
            msg = "Document title must not be empty."
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
    def reject_empty_payload(self) -> DocumentUpdate:
        if not self.model_fields_set:
            msg = "At least one field must be provided."
            raise ValueError(msg)
        return self


class DocumentPermissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID | None = None
    department_id: UUID | None = None
    permission: DocumentPermissionLevel

    @model_validator(mode="after")
    def require_exactly_one_grantee(self) -> DocumentPermissionCreate:
        if (self.user_id is None) == (self.department_id is None):
            msg = "Exactly one grantee must be provided."
            raise ValueError(msg)
        return self


class DocumentPermissionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission: DocumentPermissionLevel


class DocumentPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    user_id: UUID | None
    department_id: UUID | None
    permission: DocumentPermissionLevel
    created_by: UUID
    created_at: datetime

    @classmethod
    def from_permission(
        cls,
        document_permission: DocumentPermission,
    ) -> DocumentPermissionResponse:
        return cls.model_validate(document_permission)
