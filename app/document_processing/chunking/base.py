from __future__ import annotations

from typing import Protocol

from app.document_processing.chunking.models import ChunkingResult
from app.document_processing.models import ExtractionResult


class TextChunker(Protocol):
    def chunk(self, extraction: ExtractionResult) -> ChunkingResult:
        """Divide extracted page text into deterministic chunks."""
