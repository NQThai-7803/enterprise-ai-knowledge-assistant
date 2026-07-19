from __future__ import annotations

from app.core.config import Settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import create_embedding_provider
from app.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider


def test_create_embedding_provider_returns_protocol_compatible_provider() -> None:
    provider = create_embedding_provider(Settings())

    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    assert isinstance(provider, EmbeddingProvider)
    assert provider.dimensions == 384


def test_create_embedding_provider_does_not_load_model() -> None:
    provider = create_embedding_provider(Settings())

    assert provider.model_name == "intfloat/multilingual-e5-small"
