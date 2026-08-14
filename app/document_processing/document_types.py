from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from app.core.exceptions import DocumentFileSignatureInvalidError, InvalidFileTypeError


class SupportedDocumentType(StrEnum):
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"


@dataclass(frozen=True, slots=True)
class SupportedDocumentFileType:
    document_type: SupportedDocumentType
    mime_type: str
    extensions: tuple[str, ...]
    primary_extension: str
    signature_length: int


PDF_MIME_TYPE = "application/pdf"
PNG_MIME_TYPE = "image/png"
JPEG_MIME_TYPE = "image/jpeg"

PDF_EXTENSION = ".pdf"
PNG_EXTENSION = ".png"
JPG_EXTENSION = ".jpg"
JPEG_EXTENSION = ".jpeg"

PDF_SIGNATURE = b"%PDF-"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"

SUPPORTED_DOCUMENT_TYPES: dict[str, SupportedDocumentFileType] = {
    PDF_MIME_TYPE: SupportedDocumentFileType(
        document_type=SupportedDocumentType.PDF,
        mime_type=PDF_MIME_TYPE,
        extensions=(PDF_EXTENSION,),
        primary_extension=PDF_EXTENSION,
        signature_length=len(PDF_SIGNATURE),
    ),
    PNG_MIME_TYPE: SupportedDocumentFileType(
        document_type=SupportedDocumentType.PNG,
        mime_type=PNG_MIME_TYPE,
        extensions=(PNG_EXTENSION,),
        primary_extension=PNG_EXTENSION,
        signature_length=len(PNG_SIGNATURE),
    ),
    JPEG_MIME_TYPE: SupportedDocumentFileType(
        document_type=SupportedDocumentType.JPEG,
        mime_type=JPEG_MIME_TYPE,
        extensions=(JPG_EXTENSION, JPEG_EXTENSION),
        primary_extension=JPG_EXTENSION,
        signature_length=len(JPEG_SIGNATURE),
    ),
}

_EXTENSION_TO_MIME_TYPE = {
    extension: file_type.mime_type
    for file_type in SUPPORTED_DOCUMENT_TYPES.values()
    for extension in file_type.extensions
}


def resolve_supported_document_file_type(
    *,
    filename: str,
    content_type: str | None,
) -> SupportedDocumentFileType:
    extension = normalized_extension(filename)
    expected_mime_type = _EXTENSION_TO_MIME_TYPE.get(extension)
    if expected_mime_type is None:
        raise InvalidFileTypeError()
    if content_type != expected_mime_type:
        raise InvalidFileTypeError()
    return SUPPORTED_DOCUMENT_TYPES[expected_mime_type]


def validate_document_signature(
    *,
    prefix: bytes,
    file_type: SupportedDocumentFileType,
) -> None:
    if len(prefix) < file_type.signature_length:
        raise DocumentFileSignatureInvalidError()
    if file_type.document_type == SupportedDocumentType.PDF and prefix.startswith(PDF_SIGNATURE):
        return
    if file_type.document_type == SupportedDocumentType.PNG and prefix.startswith(PNG_SIGNATURE):
        return
    if file_type.document_type == SupportedDocumentType.JPEG and prefix.startswith(JPEG_SIGNATURE):
        return
    raise DocumentFileSignatureInvalidError()


def normalized_extension(filename: str) -> str:
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    return suffix


def supported_accept_mime_types() -> tuple[str, ...]:
    return tuple(SUPPORTED_DOCUMENT_TYPES)


def extension_for_mime_type(mime_type: str) -> str:
    file_type = SUPPORTED_DOCUMENT_TYPES.get(mime_type)
    if file_type is None:
        raise InvalidFileTypeError()
    return file_type.primary_extension
