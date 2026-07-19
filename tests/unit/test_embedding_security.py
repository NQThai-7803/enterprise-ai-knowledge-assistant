from __future__ import annotations

import logging
from typing import Any

import pytest

from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.models import EmbeddingVector
from app.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.main import app
from app.workers.document_tasks import process_document

CONFIDENTIAL = "CONFIDENTIAL_EMBEDDING_TEST_MARKER"


def test_embedding_repr_does_not_leak_vector_values() -> None:
    vector = EmbeddingVector(
        values=(0.12345, 0.0, 0.99237),
        dimensions=3,
        normalized=True,
        model_name="fake-model",
    )

    assert "0.12345" not in repr(vector)


def test_embedding_error_does_not_include_input_text() -> None:
    error = EmbeddingError(EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED)

    assert CONFIDENTIAL not in str(error)


def test_model_error_does_not_include_cache_path() -> None:
    cache_path = "C:/sensitive/model/cache"

    def failing_loader(*args: Any, **kwargs: Any) -> object:
        raise OSError(cache_path)

    provider = SentenceTransformerEmbeddingProvider(
        model_name="fake-model",
        model_revision="",
        dimensions=3,
        device="cpu",
        batch_size=1,
        normalize=True,
        query_prefix="query: ",
        passage_prefix="passage: ",
        local_files_only=True,
        cache_folder=cache_path,
        model_loader=failing_loader,
    )

    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed_query("hello")

    assert cache_path not in str(exc_info.value)


def test_embedding_logs_do_not_include_chunk_text(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.embeddings")

    with caplog.at_level(logging.INFO):
        logger.info("embedding completed", extra={"chunk_count": 1})

    assert CONFIDENTIAL not in caplog.text


def test_embedding_logs_do_not_include_vector_values(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.embeddings")

    with caplog.at_level(logging.INFO):
        logger.info("embedding completed", extra={"dimensions": 384})

    assert "0.12345" not in caplog.text


def test_embedding_not_returned_through_api() -> None:
    paths = app.openapi()["paths"]
    flattened = "\n".join(sorted(paths))

    assert "embedding" not in flattened
    assert "semantic" not in flattened
    assert "document_chunks" not in flattened


def test_embedding_not_returned_through_celery() -> None:
    result = process_document("not-a-uuid")

    assert "embedding" not in result
    assert "chunks" not in result
    assert "chunk_text" not in result
