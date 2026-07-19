from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from pathlib import Path
from typing import Any

import pytest

from app.storage.local import LocalFileStorage, StorageConflictError, StorageKeyError


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def byte_chunks(*chunks: bytes) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


def test_local_storage_creates_root_directory(tmp_path: Path) -> None:
    root = tmp_path / "uploads"

    LocalFileStorage(root)

    assert root.is_dir()


def test_local_storage_saves_file(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)

        await storage.save("documents/2026/07/file.pdf", byte_chunks(b"%PDF-1.7"))

        assert (tmp_path / "documents" / "2026" / "07" / "file.pdf").is_file()

    run_async(scenario())


def test_local_storage_open_returns_saved_content(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        await storage.save("documents/file.pdf", byte_chunks(b"%PDF-", b"content"))

        saved_content = await storage.open("documents/file.pdf")

        assert saved_content == b"%PDF-content"

    run_async(scenario())


def test_local_storage_exists_returns_true_for_saved_file(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        await storage.save("documents/file.pdf", byte_chunks(b"%PDF-content"))

        assert await storage.exists("documents/file.pdf") is True

    run_async(scenario())


def test_local_storage_delete_removes_file(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        await storage.save("documents/file.pdf", byte_chunks(b"%PDF-content"))

        await storage.delete("documents/file.pdf")

        assert await storage.exists("documents/file.pdf") is False

    run_async(scenario())


def test_local_storage_delete_is_idempotent(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)

        await storage.delete("documents/missing.pdf")
        await storage.delete("documents/missing.pdf")

        assert await storage.exists("documents/missing.pdf") is False

    run_async(scenario())


def test_local_storage_rejects_parent_traversal(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)

        with pytest.raises(StorageKeyError):
            await storage.exists("documents/../../../secret.txt")

    run_async(scenario())


def test_local_storage_rejects_windows_parent_traversal(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)

        with pytest.raises(StorageKeyError):
            await storage.exists("..\\..\\secret.txt")

    run_async(scenario())


def test_local_storage_rejects_windows_absolute_path(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)

        with pytest.raises(StorageKeyError):
            await storage.exists("C:\\Windows\\system.ini")

    run_async(scenario())


def test_local_storage_rejects_posix_absolute_path(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)

        with pytest.raises(StorageKeyError):
            await storage.exists("/var/log/app.log")

    run_async(scenario())


def test_local_storage_does_not_leave_partial_file_on_failure(tmp_path: Path) -> None:
    async def failing_chunks() -> AsyncIterator[bytes]:
        yield b"partial"
        raise RuntimeError("simulated write stream failure")

    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)

        with pytest.raises(RuntimeError):
            await storage.save("documents/file.pdf", failing_chunks())

        assert not (tmp_path / "documents" / "file.pdf").exists()
        assert [path for path in tmp_path.rglob("*") if path.is_file()] == []

    run_async(scenario())


def test_local_storage_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    async def scenario() -> None:
        storage = LocalFileStorage(tmp_path)
        await storage.save("documents/file.pdf", byte_chunks(b"first"))

        with pytest.raises(StorageConflictError):
            await storage.save("documents/file.pdf", byte_chunks(b"second"))

        assert await storage.open("documents/file.pdf") == b"first"

    run_async(scenario())
