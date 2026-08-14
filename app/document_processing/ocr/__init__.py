"""OCR provider abstractions and local implementations."""

from app.document_processing.ocr.models import OCRHealthResult, OCRImageInput, OCRPageResult
from app.document_processing.ocr.provider import OCRProvider
from app.document_processing.ocr.tesseract_provider import TesseractOCRProvider

__all__ = [
    "OCRHealthResult",
    "OCRImageInput",
    "OCRPageResult",
    "OCRProvider",
    "TesseractOCRProvider",
]
