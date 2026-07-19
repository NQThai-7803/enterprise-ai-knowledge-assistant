"""Text extractor implementations."""

from app.document_processing.extractors.base import TextExtractor
from app.document_processing.extractors.pymupdf_extractor import (
    PyMuPDFTextExtractor,
    create_pdf_text_extractor,
)

__all__ = ["PyMuPDFTextExtractor", "TextExtractor", "create_pdf_text_extractor"]
