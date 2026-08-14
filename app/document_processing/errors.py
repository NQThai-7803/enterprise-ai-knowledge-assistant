from __future__ import annotations

from enum import StrEnum


class PDFExtractionFailureCode(StrEnum):
    INVALID_PDF = "INVALID_PDF"
    ENCRYPTED_PDF = "ENCRYPTED_PDF"
    PDF_PAGE_LIMIT_EXCEEDED = "PDF_PAGE_LIMIT_EXCEEDED"
    PDF_NO_USABLE_TEXT = "PDF_NO_USABLE_TEXT"
    PDF_PAGE_EXTRACTION_FAILED = "PDF_PAGE_EXTRACTION_FAILED"
    PDF_EXTRACTION_FAILED = "PDF_EXTRACTION_FAILED"


SAFE_PDF_EXTRACTION_MESSAGES = {
    PDFExtractionFailureCode.INVALID_PDF: "The PDF file is invalid or corrupted.",
    PDFExtractionFailureCode.ENCRYPTED_PDF: "Password-protected PDF files are not supported.",
    PDFExtractionFailureCode.PDF_PAGE_LIMIT_EXCEEDED: (
        "The PDF exceeds the maximum supported page count."
    ),
    PDFExtractionFailureCode.PDF_NO_USABLE_TEXT: "No usable text was found in the PDF.",
    PDFExtractionFailureCode.PDF_PAGE_EXTRACTION_FAILED: (
        "Text could not be extracted from one or more PDF pages."
    ),
    PDFExtractionFailureCode.PDF_EXTRACTION_FAILED: "The PDF could not be processed.",
}


class PDFExtractionError(Exception):
    def __init__(
        self,
        code: PDFExtractionFailureCode,
        safe_message: str | None = None,
    ) -> None:
        self.code = code
        self.safe_message = safe_message or SAFE_PDF_EXTRACTION_MESSAGES[code]
        super().__init__(self.safe_message)

    def __str__(self) -> str:
        return self.safe_message


class DocumentExtractionFailureCode(StrEnum):
    DOCUMENT_OCR_DISABLED = "DOCUMENT_OCR_DISABLED"
    DOCUMENT_OCR_PAGE_LIMIT_EXCEEDED = "DOCUMENT_OCR_PAGE_LIMIT_EXCEEDED"
    DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED = "DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED"
    DOCUMENT_IMAGE_INVALID = "DOCUMENT_IMAGE_INVALID"
    DOCUMENT_PDF_ENCRYPTED = "DOCUMENT_PDF_ENCRYPTED"
    DOCUMENT_PDF_INVALID = "DOCUMENT_PDF_INVALID"
    DOCUMENT_OCR_TIMEOUT = "DOCUMENT_OCR_TIMEOUT"
    DOCUMENT_OCR_FAILED = "DOCUMENT_OCR_FAILED"
    DOCUMENT_EXTRACTION_EMPTY = "DOCUMENT_EXTRACTION_EMPTY"
    DOCUMENT_EXTRACTED_TEXT_TOO_LARGE = "DOCUMENT_EXTRACTED_TEXT_TOO_LARGE"
    DOCUMENT_PDF_RENDER_FAILED = "DOCUMENT_PDF_RENDER_FAILED"


SAFE_DOCUMENT_EXTRACTION_MESSAGES = {
    DocumentExtractionFailureCode.DOCUMENT_OCR_DISABLED: "OCR processing is disabled.",
    DocumentExtractionFailureCode.DOCUMENT_OCR_PAGE_LIMIT_EXCEEDED: (
        "The document exceeds the maximum OCR page count."
    ),
    DocumentExtractionFailureCode.DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED: (
        "The image dimensions exceed the supported limit."
    ),
    DocumentExtractionFailureCode.DOCUMENT_IMAGE_INVALID: (
        "The image file is invalid or unsupported."
    ),
    DocumentExtractionFailureCode.DOCUMENT_PDF_ENCRYPTED: (
        "Password-protected PDF files are not supported."
    ),
    DocumentExtractionFailureCode.DOCUMENT_PDF_INVALID: "The PDF file is invalid or corrupted.",
    DocumentExtractionFailureCode.DOCUMENT_OCR_TIMEOUT: "OCR processing timed out.",
    DocumentExtractionFailureCode.DOCUMENT_OCR_FAILED: "OCR processing failed.",
    DocumentExtractionFailureCode.DOCUMENT_EXTRACTION_EMPTY: (
        "No usable text was found in the document."
    ),
    DocumentExtractionFailureCode.DOCUMENT_EXTRACTED_TEXT_TOO_LARGE: (
        "The extracted document text exceeds the supported limit."
    ),
    DocumentExtractionFailureCode.DOCUMENT_PDF_RENDER_FAILED: (
        "The PDF page could not be rendered for OCR."
    ),
}


class DocumentExtractionError(Exception):
    def __init__(
        self,
        code: DocumentExtractionFailureCode | str,
        safe_message: str | None = None,
    ) -> None:
        self.code = DocumentExtractionFailureCode(code)
        self.safe_message = safe_message or SAFE_DOCUMENT_EXTRACTION_MESSAGES[self.code]
        super().__init__(self.safe_message)

    def __str__(self) -> str:
        return self.safe_message


class ChunkingFailureCode(StrEnum):
    EMPTY_EXTRACTION = "EMPTY_EXTRACTION"
    INVALID_CHUNK_CONFIGURATION = "INVALID_CHUNK_CONFIGURATION"
    TOKENIZATION_FAILED = "TOKENIZATION_FAILED"
    CHUNKING_FAILED = "CHUNKING_FAILED"


SAFE_CHUNKING_MESSAGES = {
    ChunkingFailureCode.EMPTY_EXTRACTION: "No extractable text is available for chunking.",
    ChunkingFailureCode.INVALID_CHUNK_CONFIGURATION: "The chunking configuration is invalid.",
    ChunkingFailureCode.TOKENIZATION_FAILED: "The document text could not be tokenized.",
    ChunkingFailureCode.CHUNKING_FAILED: "The document text could not be divided into chunks.",
}


class ChunkingError(Exception):
    def __init__(
        self,
        code: ChunkingFailureCode,
        safe_message: str | None = None,
    ) -> None:
        self.code = code
        self.safe_message = safe_message or SAFE_CHUNKING_MESSAGES[code]
        super().__init__(self.safe_message)

    def __str__(self) -> str:
        return self.safe_message
