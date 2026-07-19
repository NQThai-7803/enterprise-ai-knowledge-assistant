from __future__ import annotations

from typing import Protocol

from app.document_processing.models import ExtractionResult


class TextExtractor(Protocol):
    def extract(self, source: bytes | bytearray | memoryview) -> ExtractionResult:
        """Extract normalized page-level text from a bounded binary source."""
