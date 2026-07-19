from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pymupdf
import pytest

from app.document_processing.chunking.page_aware_chunker import PageAwareTokenChunker
from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor
from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter
from app.embeddings.models import EmbeddingBatch, EmbeddingVector

pytestmark = pytest.mark.integration

TEST_FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")


class FakeEmbeddingProvider:
    @property
    def dimensions(self) -> int:
        return 384

    @property
    def model_name(self) -> str:
        return "fake-model"

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingBatch:
        vectors = tuple(
            EmbeddingVector(
                values=_unit_vector(index),
                dimensions=384,
                normalized=True,
                model_name=self.model_name,
            )
            for index, _text in enumerate(texts)
        )
        return EmbeddingBatch(
            vectors=vectors,
            count=len(vectors),
            dimensions=384,
            normalized=True,
            model_name=self.model_name,
        )

    def embed_query(self, text: str) -> EmbeddingVector:
        return EmbeddingVector(
            values=_unit_vector(0),
            dimensions=384,
            normalized=True,
            model_name=self.model_name,
        )


def _unit_vector(position: int) -> tuple[float, ...]:
    values = [0.0] * 384
    values[position % 384] = 1.0
    return tuple(values)


def make_pdf(page_texts: list[str]) -> bytes:
    document = pymupdf.open()
    try:
        for text in page_texts:
            page = document.new_page()
            if TEST_FONT_PATH.exists():
                page.insert_font(fontname="taskfont", fontfile=str(TEST_FONT_PATH))
                page.insert_text((72, 72), text, fontname="taskfont")
            else:
                page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


def extract_chunk_and_embed(page_texts: list[str]) -> tuple[object, EmbeddingBatch]:
    extraction = PyMuPDFTextExtractor(
        max_pages=500,
        min_usable_characters=1,
        sort_text=True,
    ).extract(make_pdf(page_texts))
    chunking = PageAwareTokenChunker(
        token_counter=TiktokenTokenCounter("cl100k_base"),
        target_tokens=40,
        max_tokens=60,
        overlap_tokens=5,
        min_tokens=0,
    ).chunk(extraction)
    embeddings = FakeEmbeddingProvider().embed_passages(
        tuple(chunk.text for chunk in chunking.chunks)
    )
    return chunking, embeddings


def test_extract_chunk_and_embed_pdf() -> None:
    chunking, embeddings = extract_chunk_and_embed(["Employee leave policy allows annual days."])

    assert chunking.chunk_count == embeddings.count


def test_embedding_count_matches_chunk_count() -> None:
    chunking, embeddings = extract_chunk_and_embed(["Page one policy.", "Page two policy."])

    assert embeddings.count == chunking.chunk_count


def test_each_embedding_has_384_dimensions() -> None:
    _chunking, embeddings = extract_chunk_and_embed(["Dimension check policy."])

    assert all(vector.dimensions == 384 for vector in embeddings.vectors)


def test_chunk_text_is_not_modified_by_embedding() -> None:
    chunking, _embeddings = extract_chunk_and_embed(["Original business identifier HD2026001."])

    assert "HD2026001" in chunking.chunks[0].text


def test_passage_prefix_is_not_persisted_in_chunk_text() -> None:
    chunking, _embeddings = extract_chunk_and_embed(["Prefix should not be stored."])

    assert not chunking.chunks[0].text.startswith("passage:")


def test_embedding_result_does_not_retain_source_text() -> None:
    marker = "CONFIDENTIAL_EMBEDDING_TEST_MARKER"
    _chunking, embeddings = extract_chunk_and_embed([marker])

    assert marker not in repr(embeddings)
