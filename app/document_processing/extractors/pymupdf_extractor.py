from __future__ import annotations

import logging
from dataclasses import dataclass

import pymupdf

from app.core.config import Settings, get_settings
from app.document_processing.errors import PDFExtractionError, PDFExtractionFailureCode
from app.document_processing.models import ExtractedPage, ExtractionResult
from app.document_processing.normalization import (
    count_usable_characters,
    normalize_extracted_text,
)

PDF_SIGNATURE = b"%PDF-"
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PyMuPDFTextExtractor:
    max_pages: int
    min_usable_characters: int
    sort_text: bool = True

    def __post_init__(self) -> None:
        if self.max_pages <= 0:
            msg = "max_pages must be greater than zero."
            raise ValueError(msg)
        if self.min_usable_characters < 0:
            msg = "min_usable_characters must not be negative."
            raise ValueError(msg)

    def extract(self, source: bytes | bytearray | memoryview) -> ExtractionResult:
        data = _coerce_pdf_source(source)
        if not data or not data.startswith(PDF_SIGNATURE):
            raise PDFExtractionError(PDFExtractionFailureCode.INVALID_PDF)

        document = _open_pdf_document(data)
        try:
            return self._extract_from_document(document)
        except PDFExtractionError:
            raise
        except Exception as exc:
            raise PDFExtractionError(PDFExtractionFailureCode.PDF_EXTRACTION_FAILED) from exc
        finally:
            document.close()

    def _extract_from_document(self, document: pymupdf.Document) -> ExtractionResult:
        if document.needs_pass:
            raise PDFExtractionError(PDFExtractionFailureCode.ENCRYPTED_PDF)

        page_count = document.page_count
        if page_count <= 0:
            raise PDFExtractionError(PDFExtractionFailureCode.PDF_NO_USABLE_TEXT)
        if page_count > self.max_pages:
            raise PDFExtractionError(PDFExtractionFailureCode.PDF_PAGE_LIMIT_EXCEEDED)

        pages: list[ExtractedPage] = []
        for index in range(page_count):
            page_number = index + 1
            page = document.load_page(index)
            try:
                raw_text = page.get_text("text", sort=self.sort_text) or ""
            except Exception as exc:
                logger.warning(
                    "PDF page text extraction failed.",
                    extra={"page_number": page_number},
                )
                raise PDFExtractionError(
                    PDFExtractionFailureCode.PDF_PAGE_EXTRACTION_FAILED
                ) from exc

            normalized_text = normalize_extracted_text(raw_text)
            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=normalized_text,
                    raw_character_count=len(raw_text),
                    normalized_character_count=len(normalized_text),
                    usable_character_count=count_usable_characters(normalized_text),
                )
            )

        result = ExtractionResult(
            page_count=page_count,
            pages=tuple(pages),
            pages_with_usable_text=sum(1 for page in pages if page.usable_character_count > 0),
            total_raw_characters=sum(page.raw_character_count for page in pages),
            total_normalized_characters=sum(page.normalized_character_count for page in pages),
            total_usable_characters=sum(page.usable_character_count for page in pages),
        )
        if result.total_usable_characters < self.min_usable_characters:
            raise PDFExtractionError(PDFExtractionFailureCode.PDF_NO_USABLE_TEXT)
        return result


def create_pdf_text_extractor(settings: Settings | None = None) -> PyMuPDFTextExtractor:
    resolved_settings = settings or get_settings()
    return PyMuPDFTextExtractor(
        max_pages=resolved_settings.pdf_max_pages,
        min_usable_characters=resolved_settings.pdf_min_usable_characters,
        sort_text=resolved_settings.pdf_text_sort,
    )


def _coerce_pdf_source(source: bytes | bytearray | memoryview) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, bytearray):
        return bytes(source)
    if isinstance(source, memoryview):
        return source.tobytes()
    raise TypeError("source must be bytes, bytearray, or memoryview.")


def _open_pdf_document(data: bytes) -> pymupdf.Document:
    try:
        return pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PDFExtractionError(PDFExtractionFailureCode.INVALID_PDF) from exc
