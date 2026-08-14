from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.exceptions import DocumentFileSignatureInvalidError, InvalidFileTypeError
from app.document_processing.document_types import (
    JPEG_MIME_TYPE,
    JPEG_SIGNATURE,
    PNG_MIME_TYPE,
    PNG_SIGNATURE,
    resolve_supported_document_file_type,
)
from app.services.document_service import UploadFileProcessor, generate_document_storage_key


class FakeUploadFile:
    def __init__(self, content: bytes) -> None:
        self.content = content
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


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("scan.png", PNG_MIME_TYPE, PNG_SIGNATURE + b"png body"),
        ("receipt.jpg", JPEG_MIME_TYPE, JPEG_SIGNATURE + b"jpeg body"),
        ("receipt.jpeg", JPEG_MIME_TYPE, JPEG_SIGNATURE + b"jpeg body"),
    ],
)
def test_upload_processor_accepts_supported_image_signatures(
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    async def scenario() -> None:
        file_type = resolve_supported_document_file_type(
            filename=filename,
            content_type=content_type,
        )
        processor = UploadFileProcessor(
            FakeUploadFile(content),
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=4,
            file_type=file_type,
        )

        assert await collect(processor) == content

    run_async(scenario())


def test_upload_processor_rejects_image_signature_mismatch() -> None:
    async def scenario() -> None:
        file_type = resolve_supported_document_file_type(
            filename="scan.png",
            content_type=PNG_MIME_TYPE,
        )
        processor = UploadFileProcessor(
            FakeUploadFile(JPEG_SIGNATURE + b"wrong image"),
            max_upload_size_bytes=100,
            upload_chunk_size_bytes=4,
            file_type=file_type,
        )

        with pytest.raises(DocumentFileSignatureInvalidError):
            await collect(processor)

    run_async(scenario())


def test_supported_image_type_requires_matching_extension_and_mime() -> None:
    with pytest.raises(InvalidFileTypeError):
        resolve_supported_document_file_type(filename="scan.png", content_type=JPEG_MIME_TYPE)


def test_storage_key_uses_image_extension_without_original_filename() -> None:
    document_uuid = uuid.UUID("22222222-2222-4222-8222-222222222222")
    now = datetime(2026, 8, 2, tzinfo=UTC)

    png_key = generate_document_storage_key(
        now=now,
        document_uuid=document_uuid,
        extension=".png",
    )
    jpg_key = generate_document_storage_key(
        now=now,
        document_uuid=document_uuid,
        extension=".jpg",
    )

    assert png_key == "documents/2026/08/22222222-2222-4222-8222-222222222222.png"
    assert jpg_key == "documents/2026/08/22222222-2222-4222-8222-222222222222.jpg"
    assert "scan" not in png_key
    assert "receipt" not in jpg_key
