from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pytest

from app.document_processing.chunking.page_aware_chunker import PageAwareTokenChunker
from app.document_processing.errors import ChunkingError, ChunkingFailureCode
from app.document_processing.models import ExtractedPage, ExtractionResult
from app.document_processing.normalization import count_usable_characters


class CharacterTokenCounter:
    def count(self, text: str) -> int:
        return len(self.encode(text))

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(ord(character) for character in text)

    def decode(self, tokens: Sequence[int]) -> str:
        return "".join(chr(token) for token in tokens)


def make_page(page_number: int, text: str) -> ExtractedPage:
    return ExtractedPage(
        page_number=page_number,
        text=text,
        raw_character_count=len(text),
        normalized_character_count=len(text),
        usable_character_count=count_usable_characters(text),
    )


def make_extraction(*pages: tuple[int, str]) -> ExtractionResult:
    extracted_pages = tuple(make_page(page_number, text) for page_number, text in pages)
    return ExtractionResult(
        page_count=len(extracted_pages),
        pages=extracted_pages,
        pages_with_usable_text=sum(1 for page in extracted_pages if page.usable_character_count),
        total_raw_characters=sum(page.raw_character_count for page in extracted_pages),
        total_normalized_characters=sum(
            page.normalized_character_count for page in extracted_pages
        ),
        total_usable_characters=sum(page.usable_character_count for page in extracted_pages),
    )


def make_chunker(
    *,
    target: int = 50,
    max_tokens: int = 70,
    overlap: int = 5,
    min_tokens: int = 0,
) -> PageAwareTokenChunker:
    return PageAwareTokenChunker(
        token_counter=CharacterTokenCounter(),
        target_tokens=target,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        min_tokens=min_tokens,
    )


def joined_output(result) -> str:
    return "\n\n".join(chunk.text for chunk in result.chunks)


def test_small_single_page_document_creates_one_chunk() -> None:
    result = make_chunker().chunk(make_extraction((1, "Short policy text.")))

    assert result.chunk_count == 1
    assert result.chunks[0].text == "Short policy text."


def test_multi_page_document_preserves_page_order() -> None:
    extraction = make_extraction((2, "Second page marker."), (1, "First page marker."))

    result = make_chunker(target=100, max_tokens=120).chunk(extraction)

    assert result.chunks[0].text.index("First page marker.") < result.chunks[0].text.index(
        "Second page marker."
    )


def test_blank_pages_do_not_create_empty_chunks() -> None:
    result = make_chunker(target=100, max_tokens=120).chunk(
        make_extraction((1, "First"), (2, ""), (3, "Third"))
    )

    assert result.source_page_numbers == (1, 3)
    assert all(chunk.text.strip() for chunk in result.chunks)


def test_chunks_have_correct_page_metadata() -> None:
    result = make_chunker(target=100, max_tokens=120).chunk(
        make_extraction((1, "Page one text."), (2, "Page two text."))
    )

    assert result.chunks[0].page_numbers == (1, 2)
    assert result.chunks[0].start_page == 1
    assert result.chunks[0].end_page == 2


def test_paragraph_boundaries_are_preferred() -> None:
    result = make_chunker(target=20, max_tokens=40, overlap=0).chunk(
        make_extraction((1, "Paragraph one.\n\nParagraph two."))
    )

    assert "Paragraph one." in result.chunks[0].text
    assert "Paragraph two." in result.chunks[0].text
    assert "\n\n" in result.chunks[0].text


def test_sentence_fallback_handles_large_paragraph() -> None:
    text = f"{'A' * 30}. {'B' * 30}."

    result = make_chunker(target=30, max_tokens=40, overlap=0).chunk(make_extraction((1, text)))

    assert result.chunk_count == 2
    assert result.chunks[0].text.endswith(".")
    assert result.chunks[1].text.endswith(".")


def test_token_window_handles_large_sentence() -> None:
    result = make_chunker(target=30, max_tokens=40, overlap=5).chunk(
        make_extraction((1, "X" * 120))
    )

    assert result.chunk_count > 1
    assert all(chunk.token_count <= 40 for chunk in result.chunks)


def test_no_chunk_exceeds_hard_maximum() -> None:
    result = make_chunker(target=25, max_tokens=35, overlap=4).chunk(
        make_extraction((1, "A" * 30), (2, "B" * 30), (3, "C" * 30))
    )

    assert all(chunk.token_count <= 35 for chunk in result.chunks)


def test_target_size_is_respected_when_possible() -> None:
    result = make_chunker(target=25, max_tokens=28, overlap=0).chunk(
        make_extraction((1, "a" * 10 + "\n\n" + "b" * 10 + "\n\n" + "c" * 10))
    )

    assert result.chunks[0].token_count <= 25
    assert all(chunk.token_count <= 28 for chunk in result.chunks)


def test_overlap_is_applied() -> None:
    result = make_chunker(target=18, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "A" * 20 + "\n\n" + "B" * 20))
    )

    assert result.chunk_count == 2
    assert result.chunks[1].overlap_token_count > 0
    assert result.chunks[1].text.startswith("A" * 5)


def test_first_chunk_has_zero_overlap() -> None:
    result = make_chunker(target=18, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "A" * 20 + "\n\n" + "B" * 20))
    )

    assert result.chunks[0].overlap_token_count == 0


def test_overlap_never_exceeds_configuration() -> None:
    result = make_chunker(target=18, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "A" * 20 + "\n\n" + "B" * 20 + "\n\n" + "C" * 20))
    )

    assert all(chunk.overlap_token_count <= 5 for chunk in result.chunks)


def test_overlap_does_not_create_duplicate_only_chunk() -> None:
    result = make_chunker(target=18, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "A" * 20 + "\n\n" + "B" * 20))
    )

    assert result.chunks[0].text != result.chunks[1].text
    assert "B" * 20 in result.chunks[1].text


def test_final_small_chunk_merges_when_safe() -> None:
    result = make_chunker(target=20, max_tokens=30, overlap=0, min_tokens=10).chunk(
        make_extraction((1, "A" * 20 + "\n\n" + "B" * 5))
    )

    assert result.chunk_count == 1
    assert "B" * 5 in result.chunks[0].text


def test_final_small_chunk_is_kept_when_merge_exceeds_max() -> None:
    result = make_chunker(target=25, max_tokens=35, overlap=0, min_tokens=15).chunk(
        make_extraction((1, "A" * 30 + "\n\n" + "B" * 10))
    )

    assert result.chunk_count == 2
    assert result.chunks[-1].text == "B" * 10


def test_chunk_indexes_are_contiguous() -> None:
    result = make_chunker(target=18, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "A" * 20 + "\n\n" + "B" * 20 + "\n\n" + "C" * 20))
    )

    assert [chunk.chunk_index for chunk in result.chunks] == list(range(result.chunk_count))


def test_checksums_are_deterministic() -> None:
    result = make_chunker(target=18, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "A" * 20 + "\n\n" + "B" * 20))
    )

    assert (
        result.chunks[0].content_sha256
        == hashlib.sha256(result.chunks[0].text.encode("utf-8")).hexdigest()
    )


def test_same_input_produces_same_output() -> None:
    extraction = make_extraction((1, "Alpha" * 10 + "\n\n" + "Beta" * 10))
    chunker = make_chunker(target=25, max_tokens=35, overlap=5)

    first = chunker.chunk(extraction)
    second = chunker.chunk(extraction)

    assert [chunk.text for chunk in first.chunks] == [chunk.text for chunk in second.chunks]
    assert [chunk.content_sha256 for chunk in first.chunks] == [
        chunk.content_sha256 for chunk in second.chunks
    ]


def test_vietnamese_diacritics_are_preserved() -> None:
    text = "Điều khoản thanh toán bằng tiếng Việt."

    result = make_chunker().chunk(make_extraction((1, text)))

    assert text in result.chunks[0].text


def test_numbers_dates_and_currency_are_preserved() -> None:
    text = "Hợp đồng số HD-2026-001\nGiá trị: 150.000.000 ₫\nNgày hiệu lực: 17/07/2026"

    result = make_chunker(target=200, max_tokens=250).chunk(make_extraction((1, text)))

    assert "HD-2026-001" in result.chunks[0].text
    assert "150.000.000 ₫" in result.chunks[0].text
    assert "17/07/2026" in result.chunks[0].text


def test_long_word_does_not_cause_infinite_loop() -> None:
    result = make_chunker(target=25, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "X" * 300))
    )

    assert result.chunk_count > 1
    assert all(chunk.token_count <= 30 for chunk in result.chunks)


def test_empty_extraction_is_rejected() -> None:
    with pytest.raises(ChunkingError) as exc_info:
        make_chunker().chunk(make_extraction((1, "")))

    assert exc_info.value.code == ChunkingFailureCode.EMPTY_EXTRACTION


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ChunkingError) as exc_info:
        make_chunker(target=10, max_tokens=9)

    assert exc_info.value.code == ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION


def test_all_source_paragraphs_appear_in_output() -> None:
    paragraphs = ["SOURCE-PARA-1", "SOURCE-PARA-2", "SOURCE-PARA-3"]
    result = make_chunker(target=12, max_tokens=25, overlap=3).chunk(
        make_extraction((1, "\n\n".join(paragraphs)))
    )
    output = joined_output(result)

    assert all(paragraph in output for paragraph in paragraphs)


def test_page_order_is_not_changed() -> None:
    result = make_chunker(target=100, max_tokens=120).chunk(
        make_extraction((1, "PAGE-ONE"), (2, "PAGE-TWO"), (3, "PAGE-THREE"))
    )
    output = joined_output(result)

    assert output.index("PAGE-ONE") < output.index("PAGE-TWO") < output.index("PAGE-THREE")


def test_overlap_is_the_only_expected_duplication() -> None:
    result = make_chunker(target=18, max_tokens=30, overlap=5).chunk(
        make_extraction((1, "UNIQUE-ONE-12345\n\nUNIQUE-TWO-67890"))
    )
    output = joined_output(result)

    assert output.count("UNIQUE-ONE-12345") == 1
    assert output.count("UNIQUE-TWO-67890") == 1
    assert result.chunks[1].overlap_token_count > 0


def test_chunking_does_not_lowercase_text() -> None:
    result = make_chunker().chunk(make_extraction((1, "MixedCASE Contract TERM")))

    assert "MixedCASE Contract TERM" in result.chunks[0].text


def test_chunking_does_not_remove_punctuation() -> None:
    text = "Clause A: pay on time; Clause B: notify in writing!"

    result = make_chunker(target=100, max_tokens=120).chunk(make_extraction((1, text)))

    assert text in result.chunks[0].text


def test_chunking_does_not_modify_business_identifiers() -> None:
    text = "Hợp đồng số HD-2026-001 có PO#A-77/2026 và VAT 10%."

    result = make_chunker(target=100, max_tokens=120).chunk(make_extraction((1, text)))

    assert "HD-2026-001" in result.chunks[0].text
    assert "PO#A-77/2026" in result.chunks[0].text
    assert "VAT 10%" in result.chunks[0].text


def test_chunker_completes_large_synthetic_document() -> None:
    text = "\n\n".join(f"Paragraph {index} " + "A" * 40 for index in range(120))

    result = make_chunker(target=80, max_tokens=100, overlap=10).chunk(make_extraction((1, text)))

    assert result.chunk_count > 1
    assert all(chunk.token_count <= 100 for chunk in result.chunks)
