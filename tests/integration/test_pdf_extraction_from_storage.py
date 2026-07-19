from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from typing import Any

import pytest

from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor
from app.document_processing.storage import PDFStorageReadError, load_pdf_bytes_for_extraction
from app.storage.local import LocalFileStorage, StorageNotFoundError
from tests.unit.test_pymupdf_extractor import make_pdf

SECRET_MARKER = "CONFIDENTIAL_TEST_MARKER"


async def one_chunk(content: bytes) -> AsyncIterator[bytes]:
    yield content


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def test_extracts_pdf_loaded_through_file_storage(tmp_path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        storage_key = "documents/test/storage-extraction.pdf"
        pdf = make_pdf(["Storage extraction text"])
        await storage.save(storage_key, one_chunk(pdf))

        loaded = await load_pdf_bytes_for_extraction(
            storage,
            storage_key,
            expected_size=len(pdf),
            maximum_size=len(pdf),
        )
        result = PyMuPDFTextExtractor(
            max_pages=500,
            min_usable_characters=1,
            sort_text=True,
        ).extract(loaded)

        assert result.page_count == 1
        assert "Storage extraction text" in result.pages[0].text

    run_async(scenario())


def test_storage_key_is_not_exposed_in_result(tmp_path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        storage_key = "documents/test/secret-storage-key.pdf"
        pdf = make_pdf(["Storage key safety text"])
        await storage.save(storage_key, one_chunk(pdf))

        loaded = await load_pdf_bytes_for_extraction(
            storage,
            storage_key,
            expected_size=len(pdf),
            maximum_size=len(pdf),
        )
        result = PyMuPDFTextExtractor(500, 1, True).extract(loaded)

        assert storage_key not in repr(result)

    run_async(scenario())


def test_absolute_path_is_not_exposed_in_result(tmp_path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        storage_key = "documents/test/path-safety.pdf"
        pdf = make_pdf(["Absolute path safety text"])
        await storage.save(storage_key, one_chunk(pdf))

        loaded = await load_pdf_bytes_for_extraction(
            storage,
            storage_key,
            expected_size=len(pdf),
            maximum_size=len(pdf),
        )
        result = PyMuPDFTextExtractor(500, 1, True).extract(loaded)

        assert str(tmp_path) not in repr(result)

    run_async(scenario())


def test_pdf_bytes_are_not_retained_in_result(tmp_path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        storage_key = "documents/test/no-bytes-retained.pdf"
        pdf = make_pdf([SECRET_MARKER])
        await storage.save(storage_key, one_chunk(pdf))

        loaded = await load_pdf_bytes_for_extraction(
            storage,
            storage_key,
            expected_size=len(pdf),
            maximum_size=len(pdf),
        )
        result = PyMuPDFTextExtractor(500, 1, True).extract(loaded)

        assert loaded.startswith(b"%PDF-")
        assert not hasattr(result, "pdf_bytes")
        assert SECRET_MARKER not in repr(result)

    run_async(scenario())


def test_missing_storage_file_is_reported_safely(tmp_path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        storage_key = "documents/test/missing.pdf"

        with pytest.raises(StorageNotFoundError) as exc_info:
            await load_pdf_bytes_for_extraction(
                storage,
                storage_key,
                expected_size=10,
                maximum_size=100,
            )

        assert storage_key not in str(exc_info.value)
        assert str(tmp_path) not in str(exc_info.value)

    run_async(scenario())


def test_storage_read_is_size_bounded(tmp_path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        storage_key = "documents/test/too-large.pdf"
        pdf = make_pdf(["Bounded read text"])
        await storage.save(storage_key, one_chunk(pdf))

        with pytest.raises(PDFStorageReadError) as exc_info:
            await load_pdf_bytes_for_extraction(
                storage,
                storage_key,
                expected_size=len(pdf),
                maximum_size=len(pdf) - 1,
            )

        assert exc_info.value.safe_message == "PDF file exceeds the maximum allowed size."
        assert storage_key not in str(exc_info.value)
        assert str(tmp_path) not in str(exc_info.value)

    run_async(scenario())
