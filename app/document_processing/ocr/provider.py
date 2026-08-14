from __future__ import annotations

from typing import Protocol

from app.document_processing.ocr.models import OCRHealthResult, OCRImageInput, OCRPageResult


class OCRProvider(Protocol):
    async def extract_image(self, image: OCRImageInput) -> OCRPageResult:
        """Extract text from a single validated image."""

    async def health_check(self) -> OCRHealthResult:
        """Return local OCR engine health without exposing document content."""
