from __future__ import annotations

from math import nan
from typing import Any

import pytest

from app.embeddings.errors import EmbeddingError, EmbeddingFailureCode
from app.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider

CONFIDENTIAL = "CONFIDENTIAL_EMBEDDING_TEST_MARKER"


class FakeSentenceTransformerModel:
    def __init__(
        self,
        *,
        dimensions: int = 3,
        output: list[list[float]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.dimensions = dimensions
        self.output = output
        self.error = error
        self.encode_calls: list[dict[str, Any]] = []

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimensions

    def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        self.encode_calls.append({"texts": texts, "kwargs": kwargs})
        if self.error is not None:
            raise self.error
        if self.output is not None:
            return self.output
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeLoader:
    def __init__(self, model: FakeSentenceTransformerModel | None = None) -> None:
        self.model = model or FakeSentenceTransformerModel()
        self.calls: list[dict[str, Any]] = []

    def __call__(self, model_name: str, **kwargs: Any) -> FakeSentenceTransformerModel:
        self.calls.append({"model_name": model_name, "kwargs": kwargs})
        return self.model


def make_provider(
    *,
    loader: FakeLoader | None = None,
    dimensions: int = 3,
    normalize: bool = True,
) -> SentenceTransformerEmbeddingProvider:
    return SentenceTransformerEmbeddingProvider(
        model_name="fake-model",
        model_revision="",
        dimensions=dimensions,
        device="cpu",
        batch_size=2,
        normalize=normalize,
        query_prefix="query: ",
        passage_prefix="passage: ",
        local_files_only=False,
        cache_folder="./data/models",
        model_loader=loader or FakeLoader(),
    )


def test_provider_loads_model_lazily() -> None:
    loader = FakeLoader()
    provider = make_provider(loader=loader)

    assert loader.calls == []

    provider.embed_query("hello")

    assert len(loader.calls) == 1


def test_provider_does_not_load_model_on_import() -> None:
    loader = FakeLoader()
    make_provider(loader=loader)

    assert loader.calls == []


def test_provider_uses_trust_remote_code_false() -> None:
    loader = FakeLoader()

    make_provider(loader=loader).embed_query("hello")

    assert loader.calls[0]["kwargs"]["trust_remote_code"] is False


def test_provider_uses_configured_device() -> None:
    loader = FakeLoader()

    make_provider(loader=loader).embed_query("hello")

    assert loader.calls[0]["kwargs"]["device"] == "cpu"


def test_provider_uses_configured_batch_size() -> None:
    loader = FakeLoader()

    make_provider(loader=loader).embed_passages(["a", "b"])

    assert loader.model.encode_calls[0]["kwargs"]["batch_size"] == 2


def test_provider_disables_progress_bar() -> None:
    loader = FakeLoader()

    make_provider(loader=loader).embed_query("hello")

    assert loader.model.encode_calls[0]["kwargs"]["show_progress_bar"] is False


def test_provider_normalizes_embeddings() -> None:
    loader = FakeLoader()

    result = make_provider(loader=loader).embed_query("hello")

    assert result.normalized is True
    assert loader.model.encode_calls[0]["kwargs"]["normalize_embeddings"] is True


def test_passage_embedding_adds_passage_prefix() -> None:
    loader = FakeLoader()

    make_provider(loader=loader).embed_passages(["policy text"])

    assert loader.model.encode_calls[0]["texts"] == ["passage: policy text"]


def test_query_embedding_adds_query_prefix() -> None:
    loader = FakeLoader()

    make_provider(loader=loader).embed_query("leave days?")

    assert loader.model.encode_calls[0]["texts"] == ["query: leave days?"]


def test_prefix_is_not_returned_as_source_text() -> None:
    result = make_provider().embed_passages([CONFIDENTIAL])

    assert CONFIDENTIAL not in repr(result)
    assert "passage:" not in repr(result)


def test_empty_passage_list_is_rejected() -> None:
    with pytest.raises(EmbeddingError) as exc_info:
        make_provider().embed_passages([])

    assert exc_info.value.code == EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT


def test_empty_passage_is_rejected() -> None:
    with pytest.raises(EmbeddingError) as exc_info:
        make_provider().embed_passages(["  "])

    assert exc_info.value.code == EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT


def test_empty_query_is_rejected() -> None:
    with pytest.raises(EmbeddingError) as exc_info:
        make_provider().embed_query("  ")

    assert exc_info.value.code == EmbeddingFailureCode.EMPTY_EMBEDDING_INPUT


def test_dimension_mismatch_is_rejected() -> None:
    loader = FakeLoader(FakeSentenceTransformerModel(dimensions=2))

    with pytest.raises(EmbeddingError) as exc_info:
        make_provider(loader=loader, dimensions=3).embed_query("hello")

    assert exc_info.value.code == EmbeddingFailureCode.EMBEDDING_DIMENSION_MISMATCH


def test_batch_count_mismatch_is_rejected() -> None:
    loader = FakeLoader(FakeSentenceTransformerModel(output=[[1.0, 0.0, 0.0]]))

    with pytest.raises(EmbeddingError) as exc_info:
        make_provider(loader=loader).embed_passages(["a", "b"])

    assert exc_info.value.code == EmbeddingFailureCode.EMBEDDING_BATCH_MISMATCH


def test_invalid_vector_is_rejected() -> None:
    loader = FakeLoader(FakeSentenceTransformerModel(output=[[nan, 0.0, 0.0]]))

    with pytest.raises(EmbeddingError) as exc_info:
        make_provider(loader=loader).embed_query("hello")

    assert exc_info.value.code == EmbeddingFailureCode.EMBEDDING_INVALID_VECTOR


def test_raw_model_error_is_sanitized() -> None:
    loader = FakeLoader(FakeSentenceTransformerModel(error=RuntimeError(CONFIDENTIAL)))

    with pytest.raises(EmbeddingError) as exc_info:
        make_provider(loader=loader).embed_query("hello")

    assert exc_info.value.code == EmbeddingFailureCode.EMBEDDING_GENERATION_FAILED
    assert CONFIDENTIAL not in str(exc_info.value)


def test_model_load_error_is_sanitized() -> None:
    def failing_loader(*args: Any, **kwargs: Any) -> FakeSentenceTransformerModel:
        raise OSError(CONFIDENTIAL)

    provider = SentenceTransformerEmbeddingProvider(
        model_name="fake-model",
        model_revision="",
        dimensions=3,
        device="cpu",
        batch_size=2,
        normalize=True,
        query_prefix="query: ",
        passage_prefix="passage: ",
        local_files_only=True,
        cache_folder="./data/models",
        model_loader=failing_loader,
    )

    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed_query("hello")

    assert exc_info.value.code == EmbeddingFailureCode.EMBEDDING_MODEL_LOAD_FAILED
    assert CONFIDENTIAL not in str(exc_info.value)
