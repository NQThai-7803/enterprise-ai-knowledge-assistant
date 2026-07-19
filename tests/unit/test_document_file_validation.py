from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.exceptions import EmptyFileError, FileTooLargeError, InvalidFileTypeError
from app.services.document_service import (
    UploadFileProcessor,
    generate_document_storage_key,
    sanitize_original_filename,
    validate_pdf_extension,
    validate_pdf_mime_type,
)


class FakeUploadFile:
    def __init__(self, content: bytes, *, filename: str = "sample.pdf") -> None:
        self.content = content
        self.filename = filename
        self.offset = 0
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if size == -1:
            size = len(self.content) - self.offset
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def collect_chunks(processor: UploadFileProcessor) -> list[bytes]:
    return [chunk async for chunk in processor.iter_chunks()]


def test_pdf_extension_is_case_insensitive() -> None:
    validate_pdf_extension("Employee-Handbook.PDF")


def test_non_pdf_extension_is_rejected() -> None:
    with pytest.raises(InvalidFileTypeError):
        validate_pdf_extension("employee-handbook.txt")


def test_application_pdf_mime_is_accepted() -> None:
    validate_pdf_mime_type("application/pdf")


def test_wrong_mime_type_is_rejected() -> None:
    with pytest.raises(InvalidFileTypeError):
        validate_pdf_mime_type("text/plain")


def test_pdf_signature_is_accepted() -> None:
    async def scenario() -> None:
        processor = UploadFileProcessor(
            FakeUploadFile(b"%PDF-1.7\nbody"),
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=3,
        )

        assert b"".join(await collect_chunks(processor)) == b"%PDF-1.7\nbody"

    run_async(scenario())


def test_wrong_pdf_signature_is_rejected() -> None:
    async def scenario() -> None:
        processor = UploadFileProcessor(
            FakeUploadFile(b"not-a-pdf"),
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=4,
        )

        with pytest.raises(InvalidFileTypeError):
            await collect_chunks(processor)

    run_async(scenario())


def test_empty_file_is_rejected() -> None:
    async def scenario() -> None:
        processor = UploadFileProcessor(
            FakeUploadFile(b""),
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=8,
        )

        with pytest.raises(EmptyFileError):
            await collect_chunks(processor)

    run_async(scenario())


def test_oversized_file_is_rejected() -> None:
    async def scenario() -> None:
        processor = UploadFileProcessor(
            FakeUploadFile(b"%PDF-12345"),
            max_upload_size_bytes=8,
            upload_chunk_size_bytes=5,
        )

        with pytest.raises(FileTooLargeError):
            await collect_chunks(processor)

    run_async(scenario())


def test_checksum_is_sha256_lowercase_hex() -> None:
    async def scenario() -> None:
        processor = UploadFileProcessor(
            FakeUploadFile(b"%PDF-content"),
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=5,
        )
        await collect_chunks(processor)

        assert len(processor.checksum_sha256) == 64
        assert processor.checksum_sha256 == processor.checksum_sha256.lower()
        assert all(character in "0123456789abcdef" for character in processor.checksum_sha256)

    run_async(scenario())


def test_upload_is_processed_in_chunks() -> None:
    async def scenario() -> None:
        fake_file = FakeUploadFile(b"%PDF-1234567890")
        processor = UploadFileProcessor(
            fake_file,
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=5,
        )

        await collect_chunks(processor)

        assert -1 not in fake_file.read_sizes
        assert fake_file.read_sizes.count(5) >= 3

    run_async(scenario())


def test_original_filename_is_reduced_to_basename() -> None:
    assert sanitize_original_filename("../../employee.pdf") == "employee.pdf"
    assert sanitize_original_filename("..\\..\\employee.pdf") == "employee.pdf"


def test_storage_key_does_not_include_original_filename() -> None:
    document_uuid = uuid.UUID("11111111-1111-4111-8111-111111111111")
    now = datetime(2026, 7, 15, tzinfo=UTC)

    storage_key = generate_document_storage_key(now=now, document_uuid=document_uuid)

    assert storage_key == "documents/2026/07/11111111-1111-4111-8111-111111111111.pdf"
    assert "employee" not in storage_key
