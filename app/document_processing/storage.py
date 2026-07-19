from __future__ import annotations

from app.storage.base import FileStorage

DEFAULT_EXTRACTION_READ_CHUNK_SIZE = 64 * 1024


class PDFStorageReadError(Exception):
    def __init__(self, safe_message: str) -> None:
        self.safe_message = safe_message
        super().__init__(safe_message)


async def load_pdf_bytes_for_extraction(
    storage: FileStorage,
    storage_key: str,
    expected_size: int,
    maximum_size: int,
    chunk_size: int = DEFAULT_EXTRACTION_READ_CHUNK_SIZE,
) -> bytes:
    if expected_size < 0:
        raise PDFStorageReadError("PDF file size metadata is invalid.")
    if maximum_size <= 0:
        raise PDFStorageReadError("PDF maximum read size is invalid.")
    if chunk_size <= 0:
        raise PDFStorageReadError("PDF read chunk size is invalid.")
    if expected_size > maximum_size:
        raise PDFStorageReadError("PDF file exceeds the maximum allowed size.")

    content = bytearray()
    async for chunk in storage.iter_chunks(storage_key, chunk_size):
        if not chunk:
            continue
        content.extend(chunk)
        if len(content) > maximum_size:
            raise PDFStorageReadError("PDF file exceeds the maximum allowed size.")

    if len(content) != expected_size:
        raise PDFStorageReadError("PDF file size does not match metadata.")
    return bytes(content)
