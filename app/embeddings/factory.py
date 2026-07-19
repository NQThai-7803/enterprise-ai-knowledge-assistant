from __future__ import annotations

from app.core.config import Settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.constants import EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS
from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider != EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS:
        raise EmbeddingError(EmbeddingFailureCode.EMBEDDING_MODEL_LOAD_FAILED)
    return SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model_name,
        model_revision=settings.embedding_model_revision,
        dimensions=settings.embedding_dimensions,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize=settings.embedding_normalize,
        query_prefix=settings.embedding_query_prefix,
        passage_prefix=settings.embedding_passage_prefix,
        local_files_only=settings.embedding_local_files_only,
        cache_folder=settings.embedding_model_cache_path,
    )
