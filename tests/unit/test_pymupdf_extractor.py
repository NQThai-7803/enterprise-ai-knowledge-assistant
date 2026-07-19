from __future__ import annotations

import logging

import pymupdf
import pytest

from app.document_processing.errors import PDFExtractionError, PDFExtractionFailureCode
from app.document_processing.extractors import pymupdf_extractor
from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor
from app.document_processing.models import ExtractionResult

SECRET_MARKER = "CONFIDENTIAL_TEST_MARKER"


class FakePage:
    def __init__(self, text: str = "", *, error_message: str | None = None) -> None:
        self.text = text
        self.error_message = error_message
        self.calls: list[tuple[str, bool]] = []

    def get_text(self, format_name: str, *, sort: bool) -> str:
        self.calls.append((format_name, sort))
        if self.error_message is not None:
            raise RuntimeError(self.error_message)
        return self.text


class FakeDocument:
    def __init__(self, pages: list[FakePage], *, needs_pass: bool = False) -> None:
        self.pages = pages
        self.needs_pass = needs_pass
        self.page_count = len(pages)
        self.closed = False
        self.loaded_pages: list[int] = []

    def load_page(self, index: int) -> FakePage:
        self.loaded_pages.append(index)
        return self.pages[index]

    def close(self) -> None:
        self.closed = True


def make_pdf(page_texts: list[str | None]) -> bytes:
    document = pymupdf.open()
    try:
        for text in page_texts:
            page = document.new_page()
            if text is not None:
                page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


def make_image_only_pdf() -> bytes:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.draw_rect(pymupdf.Rect(72, 72, 144, 144))
        return document.tobytes()
    finally:
        document.close()


def make_encrypted_pdf() -> bytes:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.insert_text((72, 72), "Encrypted content")
        return document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner-password",
            user_pw="user-password",
            permissions=0,
        )
    finally:
        document.close()


def make_extractor(
    *,
    max_pages: int = 500,
    min_usable_characters: int = 1,
    sort_text: bool = True,
) -> PyMuPDFTextExtractor:
    return PyMuPDFTextExtractor(
        max_pages=max_pages,
        min_usable_characters=min_usable_characters,
        sort_text=sort_text,
    )


def patch_open(monkeypatch: pytest.MonkeyPatch, document: FakeDocument) -> None:
    def fake_open(*, stream: bytes, filetype: str) -> FakeDocument:
        assert stream.startswith(b"%PDF-")
        assert filetype == "pdf"
        return document

    monkeypatch.setattr(pymupdf_extractor.pymupdf, "open", fake_open)


def assert_failure(source: bytes, code: PDFExtractionFailureCode) -> PDFExtractionError:
    with pytest.raises(PDFExtractionError) as exc_info:
        make_extractor().extract(source)
    assert exc_info.value.code == code
    return exc_info.value


def test_extracts_single_page_pdf() -> None:
    result = make_extractor().extract(make_pdf(["Hello PDF text"]))

    assert result.page_count == 1
    assert result.pages[0].page_number == 1
    assert "Hello PDF text" in result.pages[0].text


def test_extracts_multi_page_pdf() -> None:
    result = make_extractor().extract(make_pdf(["First page text", "Second page text"]))

    assert result.page_count == 2
    assert "First page" in result.pages[0].text
    assert "Second page" in result.pages[1].text


def test_page_numbers_are_one_based() -> None:
    result = make_extractor().extract(make_pdf(["First", "Second", "Third"]))

    assert [page.page_number for page in result.pages] == [1, 2, 3]


def test_preserves_blank_pages() -> None:
    result = make_extractor().extract(make_pdf(["First page text", None, "Third page text"]))

    assert result.page_count == 3
    assert len(result.pages) == 3
    assert result.pages[1].page_number == 2
    assert result.pages[1].text == ""
    assert result.pages_with_usable_text == 2


def test_returns_page_count() -> None:
    result = make_extractor().extract(make_pdf(["One", "Two"]))

    assert result.page_count == 2


def test_returns_pages_with_usable_text_count() -> None:
    result = make_extractor().extract(make_pdf(["One", None, "Two"]))

    assert result.pages_with_usable_text == 2


def test_returns_total_character_counts() -> None:
    result = make_extractor().extract(make_pdf(["Character count text", "More text"]))

    assert result.total_raw_characters == sum(page.raw_character_count for page in result.pages)
    assert result.total_normalized_characters == sum(
        page.normalized_character_count for page in result.pages
    )
    assert result.total_usable_characters == sum(
        page.usable_character_count for page in result.pages
    )


def test_applies_normalization_per_page(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_page = FakePage("A\t  B\r\nC\x00")
    fake_document = FakeDocument([fake_page])
    patch_open(monkeypatch, fake_document)

    result = make_extractor().extract(b"%PDF-fake")

    assert result.pages[0].text == "A B\nC"


def test_uses_sorted_text_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_page = FakePage("Sorted text")
    fake_document = FakeDocument([fake_page])
    patch_open(monkeypatch, fake_document)

    make_extractor(sort_text=True).extract(b"%PDF-fake")

    assert fake_page.calls == [("text", True)]


def test_uses_unsorted_text_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_page = FakePage("Unsorted text")
    fake_document = FakeDocument([fake_page])
    patch_open(monkeypatch, fake_document)

    make_extractor(sort_text=False).extract(b"%PDF-fake")

    assert fake_page.calls == [("text", False)]


def test_accepts_bytearray_and_memoryview_sources() -> None:
    pdf = make_pdf(["Byte source text"])

    assert isinstance(make_extractor().extract(bytearray(pdf)), ExtractionResult)
    assert isinstance(make_extractor().extract(memoryview(pdf)), ExtractionResult)


def test_rejects_empty_source() -> None:
    error = assert_failure(b"", PDFExtractionFailureCode.INVALID_PDF)

    assert error.safe_message == "The PDF file is invalid or corrupted."


def test_rejects_non_pdf_signature() -> None:
    assert_failure(b"not a pdf", PDFExtractionFailureCode.INVALID_PDF)


def test_rejects_corrupted_pdf() -> None:
    assert_failure(b"%PDF-not-a-valid-pdf", PDFExtractionFailureCode.INVALID_PDF)


def test_rejects_encrypted_pdf() -> None:
    assert_failure(make_encrypted_pdf(), PDFExtractionFailureCode.ENCRYPTED_PDF)


def test_rejects_pdf_over_page_limit() -> None:
    with pytest.raises(PDFExtractionError) as exc_info:
        make_extractor(max_pages=1).extract(make_pdf(["one", "two"]))

    assert exc_info.value.code == PDFExtractionFailureCode.PDF_PAGE_LIMIT_EXCEEDED


def test_rejects_blank_pdf_without_usable_text() -> None:
    assert_failure(make_pdf([None]), PDFExtractionFailureCode.PDF_NO_USABLE_TEXT)


def test_rejects_image_only_pdf_without_ocr() -> None:
    assert_failure(make_image_only_pdf(), PDFExtractionFailureCode.PDF_NO_USABLE_TEXT)


def test_page_extraction_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_document = FakeDocument([FakePage(error_message=SECRET_MARKER)])
    patch_open(monkeypatch, fake_document)
    caplog.set_level(logging.WARNING, logger=pymupdf_extractor.__name__)

    with pytest.raises(PDFExtractionError) as exc_info:
        make_extractor().extract(b"%PDF-fake")

    assert exc_info.value.code == PDFExtractionFailureCode.PDF_PAGE_EXTRACTION_FAILED
    assert SECRET_MARKER not in exc_info.value.safe_message
    assert SECRET_MARKER not in caplog.text
    assert fake_document.closed


def test_document_is_closed_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_document = FakeDocument([FakePage("Close after success")])
    patch_open(monkeypatch, fake_document)

    make_extractor().extract(b"%PDF-fake")

    assert fake_document.closed is True


def test_document_is_closed_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_document = FakeDocument([FakePage("one"), FakePage("two")])
    patch_open(monkeypatch, fake_document)

    with pytest.raises(PDFExtractionError):
        make_extractor(max_pages=1).extract(b"%PDF-fake")

    assert fake_document.closed is True
    assert fake_document.loaded_pages == []


def test_invalid_pdf_error_does_not_include_binary_content() -> None:
    marker = b"%PDF-" + SECRET_MARKER.encode()
    error = assert_failure(marker, PDFExtractionFailureCode.INVALID_PDF)

    assert SECRET_MARKER not in error.safe_message
    assert SECRET_MARKER not in str(error)


def test_page_failure_error_does_not_include_page_text(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_document = FakeDocument([FakePage(error_message=SECRET_MARKER)])
    patch_open(monkeypatch, fake_document)

    with pytest.raises(PDFExtractionError) as exc_info:
        make_extractor().extract(b"%PDF-fake")

    assert SECRET_MARKER not in exc_info.value.safe_message


def test_extraction_result_repr_does_not_leak_text() -> None:
    result = make_extractor().extract(make_pdf([SECRET_MARKER]))

    assert SECRET_MARKER not in repr(result)


def test_factory_uses_settings() -> None:
    class SettingsStub:
        pdf_max_pages = 7
        pdf_min_usable_characters = 3
        pdf_text_sort = False

    extractor = pymupdf_extractor.create_pdf_text_extractor(SettingsStub())  # type: ignore[arg-type]

    assert extractor.max_pages == 7
    assert extractor.min_usable_characters == 3
    assert extractor.sort_text is False
