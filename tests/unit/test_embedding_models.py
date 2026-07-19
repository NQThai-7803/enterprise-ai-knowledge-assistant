from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.embeddings.models import EmbeddingBatch, EmbeddingVector


def vector(values: tuple[float, ...] = (1.0, 0.0, 0.0)) -> EmbeddingVector:
    return EmbeddingVector(
        values=values,
        dimensions=len(values),
        normalized=True,
        model_name="fake-model",
    )


def test_embedding_vector_is_immutable() -> None:
    embedding = vector()

    with pytest.raises(FrozenInstanceError):
        embedding.dimensions = 4  # type: ignore[misc]


def test_embedding_batch_is_immutable() -> None:
    batch = EmbeddingBatch(
        vectors=(vector(),),
        count=1,
        dimensions=3,
        normalized=True,
        model_name="fake-model",
    )

    with pytest.raises(FrozenInstanceError):
        batch.count = 2  # type: ignore[misc]


def test_embedding_vector_values_not_in_repr() -> None:
    assert "0.12345" not in repr(vector((0.12345, 0.0, 0.99237)))


def test_embedding_batch_repr_does_not_leak_vectors() -> None:
    batch = EmbeddingBatch(
        vectors=(vector((0.12345, 0.0, 0.99237)),),
        count=1,
        dimensions=3,
        normalized=True,
        model_name="fake-model",
    )

    assert "0.12345" not in repr(batch)


def test_embedding_vector_rejects_wrong_dimension() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        EmbeddingVector(
            values=(1.0, 0.0),
            dimensions=3,
            normalized=True,
            model_name="fake-model",
        )


def test_embedding_vector_rejects_nan() -> None:
    with pytest.raises(ValueError, match="finite"):
        vector((nan, 0.0, 0.0))


def test_embedding_vector_rejects_infinity() -> None:
    with pytest.raises(ValueError, match="finite"):
        vector((inf, 0.0, 0.0))


def test_embedding_batch_count_is_consistent() -> None:
    with pytest.raises(ValueError, match="count"):
        EmbeddingBatch(
            vectors=(vector(),),
            count=2,
            dimensions=3,
            normalized=True,
            model_name="fake-model",
        )
