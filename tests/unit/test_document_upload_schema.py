from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import Document, DocumentAccessScope, DocumentStatus
from app.schemas.document import DocumentUploadMetadata, DocumentUploadResponse


def test_upload_metadata_trims_title() -> None:
    metadata = DocumentUploadMetadata(
        title="  Employee Handbook  ",
        access_scope=DocumentAccessScope.PRIVATE,
    )

    assert metadata.title == "Employee Handbook"


def test_upload_metadata_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        DocumentUploadMetadata(title="   ", access_scope=DocumentAccessScope.PRIVATE)


def test_upload_metadata_normalizes_blank_description_to_none() -> None:
    metadata = DocumentUploadMetadata(
        title="Employee Handbook",
        description="   ",
        access_scope=DocumentAccessScope.PRIVATE,
    )

    assert metadata.description is None


def test_upload_response_excludes_sensitive_storage_fields() -> None:
    document = Document(
        id=uuid.uuid4(),
        title="Employee Handbook",
        description=None,
        original_filename="employee.pdf",
        storage_key="documents/2026/07/private-key.pdf",
        mime_type="application/pdf",
        file_size=123,
        checksum_sha256="a" * 64,
        status=DocumentStatus.UPLOADED,
        access_scope=DocumentAccessScope.PRIVATE,
        department_id=None,
        uploaded_by=uuid.uuid4(),
        error_message="hidden",
        is_deleted=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    response = DocumentUploadResponse.from_document(document).model_dump()

    assert "storage_key" not in response
    assert "checksum_sha256" not in response
    assert "error_message" not in response
    assert "permissions" not in response
