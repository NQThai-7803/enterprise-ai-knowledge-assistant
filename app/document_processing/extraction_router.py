from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Protocol

import pymupdf

from app.core.config import Settings, get_settings
from app.document_processing.document_types import (
    JPEG_MIME_TYPE,
    PDF_MIME_TYPE,
    PNG_MIME_TYPE,
    SUPPORTED_DOCUMENT_TYPES,
    SupportedDocumentType,
)
from app.document_processing.errors import (
    DocumentExtractionError,
    PDFExtractionError,
    PDFExtractionFailureCode,
)
from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor
from app.document_processing.image_safety import validate_and_normalize_image_bytes
from app.document_processing.models import ExtractedPage, ExtractionResult
from app.document_processing.normalization import count_usable_characters, normalize_extracted_text
from app.document_processing.ocr.models import OCRImageInput, OCRPageResult
from app.document_processing.ocr.provider import OCRProvider
from app.document_processing.ocr.tesseract_provider import create_tesseract_ocr_provider
from app.document_processing.quality import (
    ExtractionQualityEvaluator,
    create_extraction_quality_evaluator,
)


@dataclass(frozen=True, slots=True)
class PDFPageRenderResult:
    image_bytes: bytes
    width: int
    height: int


class DocumentProcessingMetadataLike(Protocol):
    mime_type: str


class ExtractionRouter:
    def __init__(
        self,
        *,
        settings: Settings,
        native_pdf_extractor: PyMuPDFTextExtractor,
        quality_evaluator: ExtractionQualityEvaluator,
        ocr_provider: OCRProvider,
    ) -> None:
        self.settings = settings
        self.native_pdf_extractor = native_pdf_extractor
        self.quality_evaluator = quality_evaluator
        self.ocr_provider = ocr_provider

    async def extract_document(
        self,
        metadata: DocumentProcessingMetadataLike,
        source: bytes | bytearray | memoryview,
    ) -> ExtractionResult:
        data = _coerce_source(source)
        try:
            async with asyncio.timeout(self.settings.ocr_document_timeout_seconds):
                if metadata.mime_type == PDF_MIME_TYPE:
                    return await self._extract_pdf(data)
                if metadata.mime_type in {PNG_MIME_TYPE, JPEG_MIME_TYPE}:
                    return await self._extract_image_document(data, mime_type=metadata.mime_type)
        except TimeoutError as exc:
            raise DocumentExtractionError("DOCUMENT_OCR_TIMEOUT") from exc
        raise DocumentExtractionError("DOCUMENT_IMAGE_INVALID")

    async def _extract_pdf(self, data: bytes) -> ExtractionResult:
        try:
            native_result = self.native_pdf_extractor.extract(data)
        except PDFExtractionError as exc:
            raise _map_pdf_extraction_error(exc) from exc

        pages: list[ExtractedPage] = []
        ocr_page_indexes: list[int] = []
        for index, page in enumerate(native_result.pages):
            if self.quality_evaluator.page_has_usable_native_text(page):
                pages.append(
                    _copy_page_with_metadata(
                        page,
                        extraction_method="native_pdf",
                        source_type=SupportedDocumentType.PDF.value,
                    )
                )
                continue
            pages.append(page)
            ocr_page_indexes.append(index)

        if not ocr_page_indexes:
            return _build_extraction_result(pages, self.settings.ocr_max_extracted_characters)
        if not self.settings.ocr_enabled:
            raise DocumentExtractionError("DOCUMENT_OCR_DISABLED")
        if native_result.page_count > self.settings.ocr_max_pages:
            raise DocumentExtractionError("DOCUMENT_OCR_PAGE_LIMIT_EXCEEDED")

        for index in ocr_page_indexes:
            page_number = index + 1
            rendered = _render_pdf_page_for_ocr(data, page_index=index, settings=self.settings)
            ocr_result = await self.ocr_provider.extract_image(
                OCRImageInput(
                    page_number=page_number,
                    image_bytes=rendered.image_bytes,
                    width=rendered.width,
                    height=rendered.height,
                    image_format="png",
                )
            )
            pages[index] = _quality_checked_ocr_page(
                _page_from_ocr_result(
                    ocr_result,
                    source_type=SupportedDocumentType.PDF.value,
                ),
                self.quality_evaluator,
            )

        return _build_extraction_result(pages, self.settings.ocr_max_extracted_characters)

    async def _extract_image_document(self, data: bytes, *, mime_type: str) -> ExtractionResult:
        if not self.settings.ocr_enabled:
            raise DocumentExtractionError("DOCUMENT_OCR_DISABLED")
        file_type = SUPPORTED_DOCUMENT_TYPES[mime_type]
        validated_image = validate_and_normalize_image_bytes(data, settings=self.settings)
        ocr_result = await self.ocr_provider.extract_image(
            OCRImageInput(
                page_number=1,
                image_bytes=validated_image.image_bytes,
                width=validated_image.width,
                height=validated_image.height,
                image_format=validated_image.image_format,
            )
        )
        page = _quality_checked_ocr_page(
            _page_from_ocr_result(ocr_result, source_type=file_type.document_type.value),
            self.quality_evaluator,
        )
        return _build_extraction_result((page,), self.settings.ocr_max_extracted_characters)


def create_extraction_router(settings: Settings | None = None) -> ExtractionRouter:
    resolved_settings = settings or get_settings()
    return ExtractionRouter(
        settings=resolved_settings,
        native_pdf_extractor=PyMuPDFTextExtractor(
            max_pages=resolved_settings.pdf_max_pages,
            min_usable_characters=0,
            sort_text=resolved_settings.pdf_text_sort,
        ),
        quality_evaluator=create_extraction_quality_evaluator(resolved_settings),
        ocr_provider=create_tesseract_ocr_provider(resolved_settings),
    )


def _coerce_source(source: bytes | bytearray | memoryview) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, bytearray):
        return bytes(source)
    if isinstance(source, memoryview):
        return source.tobytes()
    raise TypeError("source must be bytes, bytearray, or memoryview.")


def _copy_page_with_metadata(
    page: ExtractedPage,
    *,
    extraction_method: str,
    source_type: str,
) -> ExtractedPage:
    return ExtractedPage(
        page_number=page.page_number,
        text=page.text,
        raw_character_count=page.raw_character_count,
        normalized_character_count=page.normalized_character_count,
        usable_character_count=page.usable_character_count,
        extraction_method=extraction_method,
        source_type=source_type,
        confidence=page.confidence,
        width=page.width,
        height=page.height,
        warnings=page.warnings,
    )


def _page_from_ocr_result(result: OCRPageResult, *, source_type: str) -> ExtractedPage:
    normalized_text = normalize_extracted_text(result.text)
    return ExtractedPage(
        page_number=result.page_number,
        text=normalized_text,
        raw_character_count=len(result.text),
        normalized_character_count=len(normalized_text),
        usable_character_count=count_usable_characters(normalized_text),
        extraction_method=result.extraction_method,
        source_type=source_type,
        confidence=result.confidence,
        width=result.width,
        height=result.height,
        warnings=result.warnings,
    )


def _quality_checked_ocr_page(
    page: ExtractedPage,
    quality_evaluator: ExtractionQualityEvaluator,
) -> ExtractedPage:
    if quality_evaluator.page_has_usable_ocr_text(page):
        return page
    return ExtractedPage(
        page_number=page.page_number,
        text="",
        raw_character_count=page.raw_character_count,
        normalized_character_count=0,
        usable_character_count=0,
        extraction_method=page.extraction_method,
        source_type=page.source_type,
        confidence=page.confidence,
        width=page.width,
        height=page.height,
        warnings=(*page.warnings, "OCR_LOW_QUALITY"),
    )


def _build_extraction_result(
    pages: tuple[ExtractedPage, ...] | list[ExtractedPage],
    max_extracted_characters: int,
) -> ExtractionResult:
    page_tuple = tuple(sorted(pages, key=lambda page: page.page_number))
    total_normalized = sum(page.normalized_character_count for page in page_tuple)
    if total_normalized > max_extracted_characters:
        raise DocumentExtractionError("DOCUMENT_EXTRACTED_TEXT_TOO_LARGE")
    result = ExtractionResult(
        page_count=len(page_tuple),
        pages=page_tuple,
        pages_with_usable_text=sum(1 for page in page_tuple if page.usable_character_count > 0),
        total_raw_characters=sum(page.raw_character_count for page in page_tuple),
        total_normalized_characters=total_normalized,
        total_usable_characters=sum(page.usable_character_count for page in page_tuple),
    )
    if result.total_usable_characters <= 0:
        raise DocumentExtractionError("DOCUMENT_EXTRACTION_EMPTY")
    return result


def _render_pdf_page_for_ocr(
    data: bytes,
    *,
    page_index: int,
    settings: Settings,
) -> PDFPageRenderResult:
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise DocumentExtractionError("DOCUMENT_PDF_INVALID") from exc
    try:
        page = document.load_page(page_index)
        scale = settings.ocr_render_dpi / 72.0
        width = math.ceil(page.rect.width * scale)
        height = math.ceil(page.rect.height * scale)
        _validate_rendered_dimensions(width, height, settings=settings)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        _validate_rendered_dimensions(pixmap.width, pixmap.height, settings=settings)
        return PDFPageRenderResult(
            image_bytes=pixmap.tobytes("png"),
            width=pixmap.width,
            height=pixmap.height,
        )
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("DOCUMENT_PDF_RENDER_FAILED") from exc
    finally:
        document.close()


def _validate_rendered_dimensions(width: int, height: int, *, settings: Settings) -> None:
    if width <= 0 or height <= 0:
        raise DocumentExtractionError("DOCUMENT_PDF_RENDER_FAILED")
    if width > settings.ocr_max_image_width or height > settings.ocr_max_image_height:
        raise DocumentExtractionError("DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED")
    if width * height > settings.ocr_max_image_pixels:
        raise DocumentExtractionError("DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED")


def _map_pdf_extraction_error(exc: PDFExtractionError) -> DocumentExtractionError:
    if exc.code == PDFExtractionFailureCode.INVALID_PDF:
        return DocumentExtractionError("DOCUMENT_PDF_INVALID")
    if exc.code == PDFExtractionFailureCode.ENCRYPTED_PDF:
        return DocumentExtractionError("DOCUMENT_PDF_ENCRYPTED")
    if exc.code == PDFExtractionFailureCode.PDF_PAGE_LIMIT_EXCEEDED:
        return DocumentExtractionError("DOCUMENT_OCR_PAGE_LIMIT_EXCEEDED")
    if exc.code == PDFExtractionFailureCode.PDF_NO_USABLE_TEXT:
        return DocumentExtractionError("DOCUMENT_EXTRACTION_EMPTY")
    return DocumentExtractionError("DOCUMENT_PDF_RENDER_FAILED")
