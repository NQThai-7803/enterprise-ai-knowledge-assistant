from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from typing import Protocol


class FileStorage(Protocol):
    async def save(self, storage_key: str, chunks: AsyncIterable[bytes]) -> None:
        """Save chunks under a relative storage key."""

    async def open(self, storage_key: str) -> bytes:
        """Read bytes stored under a relative storage key."""

    def iter_chunks(self, storage_key: str, chunk_size: int) -> AsyncIterator[bytes]:
        """Stream bytes stored under a relative storage key."""
        ...

    async def exists(self, storage_key: str) -> bool:
        """Return whether the relative storage key exists."""

    async def delete(self, storage_key: str) -> None:
        """Delete the relative storage key if it exists."""
