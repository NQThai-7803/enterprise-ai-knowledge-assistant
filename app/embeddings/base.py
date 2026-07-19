from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.embeddings.models import EmbeddingBatch, EmbeddingVector


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingBatch: ...

    def embed_query(self, text: str) -> EmbeddingVector: ...
