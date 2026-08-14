from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OCRImageInput:
    page_number: int
    image_bytes: bytes = field(repr=False)
    width: int
    height: int
    image_format: str

    def __post_init__(self) -> None:
        if self.page_number < 1:
            msg = "page_number must be 1-based."
            raise ValueError(msg)
        if not self.image_bytes:
            msg = "image_bytes must not be empty."
            raise ValueError(msg)
        if self.width <= 0 or self.height <= 0:
            msg = "image dimensions must be positive."
            raise ValueError(msg)
        if not self.image_format.strip():
            msg = "image_format must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class OCRPageResult:
    page_number: int
    text: str = field(repr=False)
    confidence: float | None = None
    language: str | None = None
    width: int | None = None
    height: int | None = None
    extraction_method: str = "ocr"
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        warnings = tuple(self.warnings)
        object.__setattr__(self, "warnings", warnings)
        if self.page_number < 1:
            msg = "page_number must be 1-based."
            raise ValueError(msg)
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            msg = "confidence must be in [0, 1]."
            raise ValueError(msg)
        if self.width is not None and self.width <= 0:
            msg = "width must be positive."
            raise ValueError(msg)
        if self.height is not None and self.height <= 0:
            msg = "height must be positive."
            raise ValueError(msg)
        if not self.extraction_method.strip():
            msg = "extraction_method must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class OCRHealthResult:
    available: bool
    engine: str
    version: str | None = None
    languages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        languages = tuple(self.languages)
        object.__setattr__(self, "languages", languages)
        if not self.engine.strip():
            msg = "engine must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class OCRResult:
    pages: tuple[OCRPageResult, ...]
    full_text: str = field(repr=False)
    extraction_method: str
    native_page_count: int
    ocr_page_count: int
    warning_count: int

    def __post_init__(self) -> None:
        pages = tuple(self.pages)
        object.__setattr__(self, "pages", pages)
        if self.native_page_count < 0 or self.ocr_page_count < 0 or self.warning_count < 0:
            msg = "page and warning counts must not be negative."
            raise ValueError(msg)
        if self.ocr_page_count != len(pages):
            msg = "ocr_page_count must match OCR pages."
            raise ValueError(msg)
        if not self.extraction_method.strip():
            msg = "extraction_method must not be empty."
            raise ValueError(msg)
