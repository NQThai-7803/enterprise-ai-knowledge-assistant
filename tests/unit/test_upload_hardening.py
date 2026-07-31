from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest

from app.core.exceptions import (
    DocumentFilenameInvalidError,
    DocumentFileSignatureInvalidError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from app.services.document_service import (
    UploadFileProcessor,
    sanitize_original_filename,
    validate_pdf_extension,
)


class FakeUploadFile:
    def __init__(self, content: bytes, *, filename: str = "sample.pdf") -> None:
        self.content = content
        self.filename = filename
        self.offset = 0

    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            size = len(self.content) - self.offset
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def collect(processor: UploadFileProcessor) -> bytes:
    return b"".join([chunk async for chunk in processor.iter_chunks()])


def test_signature_mismatch_uses_document_signature_error_code() -> None:
    async def scenario() -> None:
        processor = UploadFileProcessor(
            FakeUploadFile(b"MZ executable content"),
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=8,
        )
        with pytest.raises(DocumentFileSignatureInvalidError) as exc_info:
            await collect(processor)
        assert exc_info.value.code == "DOCUMENT_FILE_SIGNATURE_INVALID"

    run_async(scenario())


def test_filename_invalid_uses_document_filename_error_code() -> None:
    with pytest.raises(DocumentFilenameInvalidError) as exc_info:
        sanitize_original_filename("   ")

    assert exc_info.value.code == "DOCUMENT_FILENAME_INVALID"


def test_executable_masquerading_as_pdf_is_rejected_by_extension() -> None:
    with pytest.raises(InvalidFileTypeError) as exc_info:
        validate_pdf_extension("policy.pdf.exe")

    assert exc_info.value.code == "DOCUMENT_FILE_TYPE_INVALID"


def test_streaming_upload_size_error_uses_document_code() -> None:
    async def scenario() -> None:
        processor = UploadFileProcessor(
            FakeUploadFile(b"%PDF-123456789"),
            max_upload_size_bytes=8,
            upload_chunk_size_bytes=5,
        )
        with pytest.raises(FileTooLargeError) as exc_info:
            await collect(processor)
        assert exc_info.value.code == "DOCUMENT_FILE_TOO_LARGE"

    run_async(scenario())
