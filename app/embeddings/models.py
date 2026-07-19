from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from numbers import Real


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    values: tuple[float, ...] = field(repr=False)
    dimensions: int
    normalized: bool
    model_name: str

    def __post_init__(self) -> None:
        if self.dimensions <= 0:
            msg = "dimensions must be greater than zero."
            raise ValueError(msg)
        if not self.model_name.strip():
            msg = "model_name must not be empty."
            raise ValueError(msg)
        values = _coerce_values(self.values)
        if len(values) != self.dimensions:
            msg = "values length must match dimensions."
            raise ValueError(msg)
        object.__setattr__(self, "values", values)


@dataclass(frozen=True, slots=True)
class EmbeddingBatch:
    vectors: tuple[EmbeddingVector, ...]
    count: int
    dimensions: int
    normalized: bool
    model_name: str

    def __post_init__(self) -> None:
        vectors = tuple(self.vectors)
        object.__setattr__(self, "vectors", vectors)
        if self.count != len(vectors):
            msg = "count must match vectors length."
            raise ValueError(msg)
        if self.dimensions <= 0:
            msg = "dimensions must be greater than zero."
            raise ValueError(msg)
        if not self.model_name.strip():
            msg = "model_name must not be empty."
            raise ValueError(msg)
        for vector in vectors:
            if vector.dimensions != self.dimensions:
                msg = "all vectors must match batch dimensions."
                raise ValueError(msg)
            if vector.normalized != self.normalized:
                msg = "all vectors must match batch normalization metadata."
                raise ValueError(msg)
            if vector.model_name != self.model_name:
                msg = "all vectors must use the same model name."
                raise ValueError(msg)


def _coerce_values(values: tuple[float, ...]) -> tuple[float, ...]:
    coerced: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            msg = "embedding values must be finite numbers."
            raise ValueError(msg)
        numeric_value = float(value)
        if not isfinite(numeric_value):
            msg = "embedding values must be finite numbers."
            raise ValueError(msg)
        coerced.append(numeric_value)
    return tuple(coerced)
