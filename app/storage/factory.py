from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import FileStorage
from app.storage.local import LocalFileStorage


@lru_cache
def _build_file_storage() -> FileStorage:
    settings = get_settings()
    if settings.storage_backend != "local":
        msg = f"Unsupported storage backend: {settings.storage_backend}"
        raise RuntimeError(msg)
    return LocalFileStorage(settings.local_storage_path)


def get_file_storage() -> FileStorage:
    return _build_file_storage()
