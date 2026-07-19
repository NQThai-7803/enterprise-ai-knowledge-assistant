from __future__ import annotations

from pathlib import Path

import pymupdf

from app.document_processing.chunking.page_aware_chunker import PageAwareTokenChunker
from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor
from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter
from app.models import DocumentStatus

TEST_FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")


def make_pdf(page_texts: list[str | None]) -> bytes:
    document = pymupdf.open()
    try:
        for text in page_texts:
            page = document.new_page()
            if text is not None:
                if TEST_FONT_PATH.exists():
                    page.insert_font(fontname="taskfont", fontfile=str(TEST_FONT_PATH))
                    page.insert_text((72, 72), text, fontname="taskfont")
                else:
                    page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


def make_extractor() -> PyMuPDFTextExtractor:
    return PyMuPDFTextExtractor(max_pages=500, min_usable_characters=1, sort_text=True)


def make_chunker(
    *,
    target: int = 40,
    max_tokens: int = 60,
    overlap: int = 5,
) -> PageAwareTokenChunker:
    return PageAwareTokenChunker(
        token_counter=TiktokenTokenCounter("cl100k_base"),
        target_tokens=target,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        min_tokens=0,
    )


def extract_and_chunk(page_texts: list[str | None], *, target: int = 40, max_tokens: int = 60):
    extraction = make_extractor().extract(make_pdf(page_texts))
    return make_chunker(target=target, max_tokens=max_tokens).chunk(extraction)


def test_extract_and_chunk_single_page_pdf() -> None:
    result = extract_and_chunk(["Single page PDF content for chunking."])

    assert result.chunk_count == 1
    assert "Single page PDF content" in result.chunks[0].text


def test_extract_and_chunk_multi_page_pdf() -> None:
    result = extract_and_chunk(["First page content.", "Second page content."])

    assert result.source_page_numbers == (1, 2)
    assert result.chunk_count >= 1


def test_extract_and_chunk_preserves_page_numbers() -> None:
    result = extract_and_chunk(["First page content.", None, "Third page content."])

    assert result.source_page_numbers == (1, 3)


def test_extract_and_chunk_preserves_vietnamese_text() -> None:
    result = extract_and_chunk(["Hợp đồng số HD2026001 có hiệu lực từ 17/07/2026."])

    assert "Hợp đồng" in result.chunks[0].text
    assert "HD2026001" in result.chunks[0].text
    assert "17/07/2026" in result.chunks[0].text


def test_extract_and_chunk_respects_token_limits() -> None:
    page_texts = [
        f"Token limit page {index} with repeated business terms and policy notes."
        for index in range(20)
    ]

    result = extract_and_chunk(page_texts, target=30, max_tokens=45)

    assert result.chunk_count > 1
    assert all(chunk.token_count <= 45 for chunk in result.chunks)


def test_extract_and_chunk_generates_deterministic_checksums() -> None:
    page_texts = ["Deterministic checksum page one.", "Deterministic checksum page two."]

    first = extract_and_chunk(page_texts)
    second = extract_and_chunk(page_texts)

    assert [chunk.content_sha256 for chunk in first.chunks] == [
        chunk.content_sha256 for chunk in second.chunks
    ]


def test_extract_and_chunk_does_not_persist_data(tmp_path: Path) -> None:
    result = extract_and_chunk(["No persistence should happen."])

    assert list(tmp_path.iterdir()) == []
    assert not hasattr(result.chunks[0], "storage_key")
    assert not hasattr(result.chunks[0], "absolute_path")


def test_extract_and_chunk_does_not_change_document_status() -> None:
    status = DocumentStatus.UPLOADED

    result = extract_and_chunk(["Status should remain external to chunking."])

    assert result.chunk_count == 1
    assert status == DocumentStatus.UPLOADED
