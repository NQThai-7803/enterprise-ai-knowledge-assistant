from __future__ import annotations

from app.core.config import Settings, get_settings
from app.document_processing.chunking.base import TextChunker
from app.document_processing.chunking.page_aware_chunker import PageAwareTokenChunker
from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter


def create_document_chunker(settings: Settings | None = None) -> TextChunker:
    resolved_settings = settings or get_settings()
    return PageAwareTokenChunker(
        token_counter=TiktokenTokenCounter(resolved_settings.tokenizer_encoding_name),
        target_tokens=resolved_settings.chunk_target_tokens,
        max_tokens=resolved_settings.chunk_max_tokens,
        overlap_tokens=resolved_settings.chunk_overlap_tokens,
        min_tokens=resolved_settings.chunk_min_tokens,
    )
