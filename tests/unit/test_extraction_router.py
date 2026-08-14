from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from app.core.config import Settings
from app.document_processing import extraction_router as router_module
from app.document_processing.document_types import PDF_MIME_TYPE, PNG_MIME_TYPE
from app.document_processing.errors import DocumentExtractionError
from app.document_processing.extraction_router import ExtractionRouter, PDFPageRenderResult
from app.document_processing.models import ExtractedPage, ExtractionResult
from app.document_processing.normalization import count_usable_characters
from app.document_processing.ocr.models import OCRHealthResult, OCRPageResult
from app.document_processing.quality import create_extraction_quality_evaluator


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ocr_document_timeout_seconds": 5,
        "ocr_page_timeout_seconds": 2,
        "celery_task_soft_time_limit_seconds": 30,
        "ocr_max_image_width": 100,
        "ocr_max_image_height": 100,
        "ocr_max_image_pixels": 10_000,
        "ocr_native_text_min_characters_per_page": 4,
        "ocr_native_text_min_alnum_ratio": 0.20,
        "ocr_max_replacement_character_ratio": 0.20,
        "ocr_max_control_character_ratio": 0.20,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def make_page(page_number: int, text: str) -> ExtractedPage:
    return ExtractedPage(
        page_number=page_number,
        text=text,
        raw_character_count=len(text),
        normalized_character_count=len(text),
        usable_character_count=count_usable_characters(text),
    )


def make_extraction_result(pages: tuple[ExtractedPage, ...]) -> ExtractionResult:
    return ExtractionResult(
        page_count=len(pages),
        pages=pages,
        pages_with_usable_text=sum(1 for page in pages if page.usable_character_count > 0),
        total_raw_characters=sum(page.raw_character_count for page in pages),
        total_normalized_characters=sum(page.normalized_character_count for page in pages),
        total_usable_characters=sum(page.usable_character_count for page in pages),
    )


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (8, 6), color=(255, 255, 255))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class FakeNativePDFExtractor:
    def __init__(self, result: ExtractionResult) -> None:
        self.result = result
        self.sources: list[bytes] = []

    def extract(self, source: bytes) -> ExtractionResult:
        self.sources.append(source)
        return self.result


class FakeOCRProvider:
    def __init__(self, texts: tuple[str, ...]) -> None:
        self.texts = texts
        self.calls = []

    async def extract_image(self, image):  # noqa: ANN001
        self.calls.append(image)
        index = len(self.calls) - 1
        return OCRPageResult(
            page_number=image.page_number,
            text=self.texts[index],
            width=image.width,
            height=image.height,
            extraction_method="ocr_fake",
        )

    async def health_check(self) -> OCRHealthResult:
        return OCRHealthResult(available=True, engine="fake", languages=("eng",))


def make_router(
    *,
    native_result: ExtractionResult,
    ocr_texts: tuple[str, ...] = ("Scanned policy text",),
    settings: Settings | None = None,
) -> tuple[ExtractionRouter, FakeNativePDFExtractor, FakeOCRProvider]:
    resolved_settings = settings or make_settings()
    native = FakeNativePDFExtractor(native_result)
    ocr = FakeOCRProvider(ocr_texts)
    router = ExtractionRouter(
        settings=resolved_settings,
        native_pdf_extractor=native,  # type: ignore[arg-type]
        quality_evaluator=create_extraction_quality_evaluator(resolved_settings),
        ocr_provider=ocr,
    )
    return router, native, ocr


@pytest.mark.anyio
async def test_router_uses_usable_native_pdf_text_without_ocr() -> None:
    router, native, ocr = make_router(
        native_result=make_extraction_result((make_page(1, "Native policy text"),)),
    )

    result = await router.extract_document(
        SimpleNamespace(mime_type=PDF_MIME_TYPE),
        b"%PDF-native",
    )

    assert native.sources == [b"%PDF-native"]
    assert ocr.calls == []
    assert result.pages[0].text == "Native policy text"
    assert result.pages[0].extraction_method == "native_pdf"
    assert result.pages[0].source_type == "pdf"


@pytest.mark.anyio
async def test_router_extracts_image_document_with_ocr() -> None:
    router, _native, ocr = make_router(
        native_result=make_extraction_result((make_page(1, "unused native"),)),
        ocr_texts=("Scanned image leave policy",),
    )

    result = await router.extract_document(
        SimpleNamespace(mime_type=PNG_MIME_TYPE),
        make_image_bytes(),
    )

    assert len(ocr.calls) == 1
    assert ocr.calls[0].page_number == 1
    assert ocr.calls[0].image_format == "png"
    assert result.page_count == 1
    assert result.pages[0].text == "Scanned image leave policy"
    assert result.pages[0].source_type == "png"
    assert result.pages[0].extraction_method == "ocr_fake"
    assert result.pages[0].width == 8
    assert result.pages[0].height == 6


@pytest.mark.anyio
async def test_router_rejects_image_when_ocr_disabled() -> None:
    router, _native, _ocr = make_router(
        native_result=make_extraction_result((make_page(1, "unused native"),)),
        settings=make_settings(ocr_enabled=False),
    )

    with pytest.raises(DocumentExtractionError) as exc_info:
        await router.extract_document(SimpleNamespace(mime_type=PNG_MIME_TYPE), make_image_bytes())

    assert exc_info.value.code == "DOCUMENT_OCR_DISABLED"


@pytest.mark.anyio
async def test_router_ocr_extracts_only_low_quality_pdf_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_render(data: bytes, *, page_index: int, settings: Settings) -> PDFPageRenderResult:
        assert data == b"%PDF-scanned"
        assert page_index == 1
        assert settings.ocr_render_dpi == 200
        return PDFPageRenderResult(image_bytes=make_image_bytes(), width=8, height=6)

    monkeypatch.setattr(router_module, "_render_pdf_page_for_ocr", fake_render)
    router, _native, ocr = make_router(
        native_result=make_extraction_result(
            (
                make_page(1, "Native page stays native"),
                make_page(2, ""),
            )
        ),
        ocr_texts=("Scanned second page policy",),
    )

    result = await router.extract_document(
        SimpleNamespace(mime_type=PDF_MIME_TYPE),
        b"%PDF-scanned",
    )

    assert [call.page_number for call in ocr.calls] == [2]
    assert result.pages[0].text == "Native page stays native"
    assert result.pages[0].extraction_method == "native_pdf"
    assert result.pages[1].text == "Scanned second page policy"
    assert result.pages[1].extraction_method == "ocr_fake"
    assert result.pages[1].source_type == "pdf"


@pytest.mark.anyio
async def test_router_rejects_pdf_ocr_when_page_limit_is_exceeded() -> None:
    router, _native, _ocr = make_router(
        native_result=make_extraction_result((make_page(1, ""), make_page(2, ""))),
        settings=make_settings(ocr_max_pages=1),
    )

    with pytest.raises(DocumentExtractionError) as exc_info:
        await router.extract_document(SimpleNamespace(mime_type=PDF_MIME_TYPE), b"%PDF-pages")

    assert exc_info.value.code == "DOCUMENT_OCR_PAGE_LIMIT_EXCEEDED"


@pytest.mark.anyio
async def test_router_discards_low_quality_ocr_text_and_fails_empty_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        router_module,
        "_render_pdf_page_for_ocr",
        lambda *args, **kwargs: PDFPageRenderResult(  # noqa: ARG005
            image_bytes=make_image_bytes(),
            width=8,
            height=6,
        ),
    )
    router, _native, _ocr = make_router(
        native_result=make_extraction_result((make_page(1, ""),)),
        ocr_texts=("!!!",),
    )

    with pytest.raises(DocumentExtractionError) as exc_info:
        await router.extract_document(SimpleNamespace(mime_type=PDF_MIME_TYPE), b"%PDF-low-quality")

    assert exc_info.value.code == "DOCUMENT_EXTRACTION_EMPTY"


@pytest.mark.anyio
async def test_router_enforces_max_extracted_characters() -> None:
    router, _native, _ocr = make_router(
        native_result=make_extraction_result((make_page(1, "Native policy text"),)),
        settings=make_settings(ocr_max_extracted_characters=5),
    )

    with pytest.raises(DocumentExtractionError) as exc_info:
        await router.extract_document(SimpleNamespace(mime_type=PDF_MIME_TYPE), b"%PDF-large")

    assert exc_info.value.code == "DOCUMENT_EXTRACTED_TEXT_TOO_LARGE"
