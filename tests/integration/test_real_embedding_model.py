from __future__ import annotations

from math import sqrt

import pytest

from app.core.config import Settings
from app.embeddings.factory import create_embedding_provider
from app.embeddings.models import EmbeddingVector

pytestmark = [pytest.mark.integration, pytest.mark.embedding_model_integration]

QUERY = "Nhân viên được nghỉ phép bao nhiêu ngày?"
RELATED = "Nhân viên chính thức được hưởng 12 ngày nghỉ phép có lương mỗi năm."
UNRELATED = "Máy chủ cơ sở dữ liệu được sao lưu vào lúc 02 giờ sáng."


def cosine_distance(first: EmbeddingVector, second: EmbeddingVector) -> float:
    return 1.0 - sum(a * b for a, b in zip(first.values, second.values, strict=True))


def l2_norm(vector: EmbeddingVector) -> float:
    return sqrt(sum(value * value for value in vector.values))


def provider():
    return create_embedding_provider(Settings())


def test_real_model_loads() -> None:
    result = provider().embed_query(QUERY)

    assert result.model_name == "intfloat/multilingual-e5-small"


def test_real_model_dimension_is_384() -> None:
    result = provider().embed_query(QUERY)

    assert result.dimensions == 384
    assert len(result.values) == 384


def test_real_model_embeds_vietnamese_passages() -> None:
    result = provider().embed_passages([RELATED, UNRELATED])

    assert result.count == 2
    assert result.dimensions == 384


def test_real_model_embeds_vietnamese_query() -> None:
    result = provider().embed_query(QUERY)

    assert result.dimensions == 384


def test_real_model_returns_normalized_vectors() -> None:
    query = provider().embed_query(QUERY)
    passages = provider().embed_passages([RELATED, UNRELATED])

    assert abs(l2_norm(query) - 1.0) <= 1e-3
    assert all(abs(l2_norm(vector) - 1.0) <= 1e-3 for vector in passages.vectors)


def test_semantically_related_vietnamese_texts_are_closer() -> None:
    embedding_provider = provider()
    query = embedding_provider.embed_query(QUERY)
    passages = embedding_provider.embed_passages([RELATED, UNRELATED])
    related_distance = cosine_distance(query, passages.vectors[0])
    unrelated_distance = cosine_distance(query, passages.vectors[1])

    assert related_distance < unrelated_distance
