from __future__ import annotations

import pytest

from app.core.exceptions import DocumentFileSignatureInvalidError, InvalidFileTypeError
from app.document_processing.document_types import (
    JPEG_MIME_TYPE,
    JPEG_SIGNATURE,
    PDF_MIME_TYPE,
    PDF_SIGNATURE,
    PNG_MIME_TYPE,
    PNG_SIGNATURE,
    SupportedDocumentType,
    extension_for_mime_type,
    resolve_supported_document_file_type,
    supported_accept_mime_types,
    validate_document_signature,
)


def test_supported_accept_mime_types_include_pdf_png_and_jpeg() -> None:
    assert supported_accept_mime_types() == (PDF_MIME_TYPE, PNG_MIME_TYPE, JPEG_MIME_TYPE)


@pytest.mark.parametrize(
    ("filename", "content_type", "expected_type"),
    [
        ("policy.pdf", PDF_MIME_TYPE, SupportedDocumentType.PDF),
        ("scan.png", PNG_MIME_TYPE, SupportedDocumentType.PNG),
        ("receipt.jpg", JPEG_MIME_TYPE, SupportedDocumentType.JPEG),
        ("receipt.jpeg", JPEG_MIME_TYPE, SupportedDocumentType.JPEG),
        ("RECEIPT.JPEG", JPEG_MIME_TYPE, SupportedDocumentType.JPEG),
    ],
)
def test_resolves_supported_document_file_types(
    filename: str,
    content_type: str,
    expected_type: SupportedDocumentType,
) -> None:
    file_type = resolve_supported_document_file_type(
        filename=filename,
        content_type=content_type,
    )

    assert file_type.document_type == expected_type
    assert file_type.mime_type == content_type


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("policy.txt", "text/plain"),
        ("policy.pdf.exe", PDF_MIME_TYPE),
        ("scan.png", JPEG_MIME_TYPE),
        ("receipt.jpeg", PNG_MIME_TYPE),
        ("receipt.jpg", None),
    ],
)
def test_rejects_unsupported_extension_or_mime_mismatch(
    filename: str,
    content_type: str | None,
) -> None:
    with pytest.raises(InvalidFileTypeError):
        resolve_supported_document_file_type(filename=filename, content_type=content_type)


@pytest.mark.parametrize(
    ("filename", "content_type", "signature"),
    [
        ("policy.pdf", PDF_MIME_TYPE, PDF_SIGNATURE + b"1.7"),
        ("scan.png", PNG_MIME_TYPE, PNG_SIGNATURE + b"body"),
        ("receipt.jpg", JPEG_MIME_TYPE, JPEG_SIGNATURE + b"body"),
    ],
)
def test_validates_supported_document_signatures(
    filename: str,
    content_type: str,
    signature: bytes,
) -> None:
    file_type = resolve_supported_document_file_type(filename=filename, content_type=content_type)

    validate_document_signature(prefix=signature, file_type=file_type)


@pytest.mark.parametrize(
    ("filename", "content_type", "signature"),
    [
        ("policy.pdf", PDF_MIME_TYPE, PNG_SIGNATURE),
        ("scan.png", PNG_MIME_TYPE, JPEG_SIGNATURE),
        ("receipt.jpg", JPEG_MIME_TYPE, PDF_SIGNATURE),
    ],
)
def test_rejects_wrong_supported_document_signatures(
    filename: str,
    content_type: str,
    signature: bytes,
) -> None:
    file_type = resolve_supported_document_file_type(filename=filename, content_type=content_type)

    with pytest.raises(DocumentFileSignatureInvalidError):
        validate_document_signature(prefix=signature, file_type=file_type)


def test_extension_for_mime_type_uses_primary_storage_extension() -> None:
    assert extension_for_mime_type(PDF_MIME_TYPE) == ".pdf"
    assert extension_for_mime_type(PNG_MIME_TYPE) == ".png"
    assert extension_for_mime_type(JPEG_MIME_TYPE) == ".jpg"
