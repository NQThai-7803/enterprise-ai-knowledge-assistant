from __future__ import annotations

from collections.abc import Callable, Sequence
from math import sqrt
from typing import Any

from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.models import EmbeddingBatch, EmbeddingVector

_NORMALIZED_TOLERANCE = 1e-3

ModelLoader = Callable[..., Any]


class SentenceTransformerEmbeddingProvider:
    def __init__(
        self,
        *,
        model_name: str,
        model_revision: str,
        dimensions: int,
        device: str,
        batch_size: int,
        normalize: bool,
        query_prefix: str,
        passage_prefix: str,
        local_files_only: bool,
        cache_folder: str,
        model_loader: ModelLoader | None = None,
    ) -> None:
        if not model_name.strip():
            msg = "model_name must not be empty."
            raise ValueError(msg)
        if dimensions <= 0:
            msg = "dimensions must be greater than zero."
            raise ValueError(msg)
        if not device.strip():
            msg = "device must not be empty."
            raise ValueError(msg)
        if batch_size <= 0:
            msg = "batch_size must be greater than zero."
            raise ValueError(msg)
        if not query_prefix:
            msg = "query_prefix must not be empty."
            raise ValueError(msg)
        if not passage_prefix:
            msg = "passage_prefix must not be empty."
            raise ValueError(msg)
        if query_prefix == passage_prefix:
            msg = "query_prefix and passage_prefix must be different."
            raise ValueError(msg)
        if not cache_folder.strip():
            msg = "cache_folder must not be empty."
            raise ValueError(msg)

        self._model_name = model_name
        self._model_revision = model_revision
        self._dimensions = dimensions
        self._device = device
        self._batch_size = batch_size
        self._normalize = normalize
        self._query_prefix = query_prefix
        self._passage_prefix = passage_prefix
        self._local_files_only = local_files_only
        self._cache_folder = cache_folder
        self._model_loader = model_loader
        self._model: Any | None = None

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @property
    def normalize(self) -> bool:
        return self._normalize

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingBatch:
        if not texts:
            raise EmbeddingError(EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT)
        prepared_texts: list[str] = []
        for text in texts:
            if not text.strip():
                raise EmbeddingError(EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT)
            prepared_texts.append(f"{self._passage_prefix}{text}")

        vectors = self._encode(prepared_texts, expected_count=len(prepared_texts))
        return EmbeddingBatch(
            vectors=tuple(vectors),
            count=len(vectors),
            dimensions=self._dimensions,
            normalized=self._normalize,
            model_name=self._model_name,
        )

    def embed_query(self, text: str) -> EmbeddingVector:
        if not text.strip():
            raise EmbeddingError(EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT)
        vectors = self._encode([f"{self._query_prefix}{text}"], expected_count=1)
        return vectors[0]

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            loader = self._model_loader
            if loader is None:
                from sentence_transformers import SentenceTransformer

                loader = SentenceTransformer
            model = loader(
                self._model_name,
                device=self._device,
                revision=self._model_revision or None,
                cache_folder=self._cache_folder,
                local_files_only=self._local_files_only,
                trust_remote_code=False,
            )
            if hasattr(model, "get_embedding_dimension"):
                actual_dimensions = model.get_embedding_dimension()
            else:
                actual_dimensions = model.get_sentence_embedding_dimension()
        except Exception as exc:
            raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_MODEL_LOAD_FAILED) from exc
        if actual_dimensions != self._dimensions:
            raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH)
        self._model = model
        return model

    def _encode(
        self, prepared_texts: Sequence[str], *, expected_count: int
    ) -> tuple[EmbeddingVector, ...]:
        model = self._get_model()
        try:
            raw_embeddings = model.encode(
                list(prepared_texts),
                batch_size=self._batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=self._normalize,
            )
        except Exception as exc:
            raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED) from exc

        rows = _to_embedding_rows(raw_embeddings)
        if len(rows) != expected_count:
            raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_BATCH_MISMATCH)

        vectors: list[EmbeddingVector] = []
        for row in rows:
            if len(row) != self._dimensions:
                raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH)
            try:
                vector = EmbeddingVector(
                    values=tuple(row),
                    dimensions=self._dimensions,
                    normalized=self._normalize,
                    model_name=self._model_name,
                )
            except ValueError as exc:
                raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_INVALID_VECTOR) from exc
            if self._normalize and not _is_normalized(vector.values):
                raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_INVALID_VECTOR)
            vectors.append(vector)
        return tuple(vectors)


def _to_embedding_rows(raw_embeddings: Any) -> list[list[float]]:
    if hasattr(raw_embeddings, "tolist"):
        raw_embeddings = raw_embeddings.tolist()
    if raw_embeddings is None:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED)
    rows = list(raw_embeddings)
    if not rows:
        return []
    first_row = rows[0]
    if isinstance(first_row, int | float):
        return [list(rows)]
    return [list(row) for row in rows]


def _is_normalized(values: tuple[float, ...]) -> bool:
    norm = sqrt(sum(value * value for value in values))
    return abs(norm - 1.0) <= _NORMALIZED_TOLERANCE
