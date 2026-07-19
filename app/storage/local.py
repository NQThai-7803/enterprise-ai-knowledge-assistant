from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path, PurePosixPath, PureWindowsPath

import anyio


class StorageError(Exception):
    """Base class for storage-layer failures that must not leak filesystem paths."""


class StorageKeyError(StorageError):
    """Raised when a storage key is unsafe or invalid."""


class StorageNotFoundError(StorageError):
    """Raised when a requested storage key does not exist."""


class StorageConflictError(StorageError):
    """Raised when saving would overwrite an existing file."""


class LocalFileStorage:
    def __init__(self, root_path: str | Path) -> None:
        if not str(root_path).strip():
            msg = "Local storage root must not be empty."
            raise ValueError(msg)
        self.root_path = Path(root_path).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    async def save(self, storage_key: str, chunks: AsyncIterable[bytes]) -> None:
        target_path = self._resolve_storage_key(storage_key)
        if await anyio.to_thread.run_sync(target_path.exists):
            raise StorageConflictError("Storage key already exists.")

        await anyio.to_thread.run_sync(
            lambda: target_path.parent.mkdir(parents=True, exist_ok=True)
        )
        temp_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            async with await anyio.open_file(temp_path, "xb") as file_obj:
                async for chunk in chunks:
                    if chunk:
                        await file_obj.write(chunk)
                await file_obj.flush()
            if await anyio.to_thread.run_sync(target_path.exists):
                raise StorageConflictError("Storage key already exists.")
            await anyio.to_thread.run_sync(os.replace, temp_path, target_path)
        except Exception:
            await self._delete_path_if_exists(temp_path)
            raise

    async def open(self, storage_key: str) -> bytes:
        content = bytearray()
        async for chunk in self.iter_chunks(storage_key, 64 * 1024):
            content.extend(chunk)
        return bytes(content)

    async def iter_chunks(self, storage_key: str, chunk_size: int) -> AsyncIterator[bytes]:
        if chunk_size <= 0:
            msg = "chunk_size must be greater than zero."
            raise ValueError(msg)
        target_path = self._resolve_storage_key(storage_key)
        if not await anyio.to_thread.run_sync(target_path.is_file):
            raise StorageNotFoundError("Storage key does not exist.")
        async with await anyio.open_file(target_path, "rb") as file_obj:
            while True:
                chunk = await file_obj.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_storage_key(storage_key)
        return await anyio.to_thread.run_sync(target_path.is_file)

    async def delete(self, storage_key: str) -> None:
        target_path = self._resolve_storage_key(storage_key)
        await self._delete_path_if_exists(target_path)

    def _resolve_storage_key(self, storage_key: str) -> Path:
        if not storage_key or "\x00" in storage_key:
            raise StorageKeyError("Storage key is invalid.")
        windows_path = PureWindowsPath(storage_key)
        posix_path = PurePosixPath(storage_key)
        if windows_path.is_absolute() or windows_path.drive or posix_path.is_absolute():
            raise StorageKeyError("Storage key must be relative.")

        normalized_key = storage_key.replace("\\", "/")
        parts = PurePosixPath(normalized_key).parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise StorageKeyError("Storage key contains unsafe path segments.")

        target_path = (self.root_path.joinpath(*parts)).resolve()
        try:
            target_path.relative_to(self.root_path)
        except ValueError as exc:
            raise StorageKeyError("Storage key resolves outside storage root.") from exc
        if target_path == self.root_path:
            raise StorageKeyError("Storage key must target a file.")
        return target_path

    async def _delete_path_if_exists(self, path: Path) -> None:
        def unlink() -> None:
            try:
                path.unlink()
            except FileNotFoundError:
                return

        await anyio.to_thread.run_sync(unlink)
