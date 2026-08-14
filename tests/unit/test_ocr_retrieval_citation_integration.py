from __future__ import annotations

from uuid import UUID

from app.chat.context_builder import select_context_for_prompt
from app.citations.mapper import map_validated_citations
from app.citations.registry import build_prompt_source_registry
from app.retrieval.models import HybridRetrievalHit


class TinyTokenCounter:
    def count(self, text: str) -> int:
        return max(1, len(text.split()))

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens: tuple[int, ...]) -> str:
        return " ".join(str(token) for token in tokens)


def test_ocr_chunk_flows_through_retrieval_context_and_citation_mapping() -> None:
    document_id = UUID("11111111-1111-4111-8111-111111111111")
    chunk_id = UUID("22222222-2222-4222-8222-222222222222")
    hit = HybridRetrievalHit(
        chunk_id=chunk_id,
        document_id=document_id,
        document_title="Scanned Policy",
        chunk_index=0,
        text="OCR image policy text says invoices require approval.",
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=9,
        hybrid_score=1.0,
        semantic_score=0.91,
        semantic_rank=1,
        keyword_score=None,
        keyword_rank=None,
        matched_by=("semantic",),
    )

    selected = select_context_for_prompt(
        hits=(hit,),
        history_messages=(),
        conversation_history=None,
        question="What does the scanned policy say about invoices?",
        system_prompt="Answer only from retrieved context.",
        token_counter=TinyTokenCounter(),
        max_tokens=500,
    )
    registry = build_prompt_source_registry(context_items=selected.items, max_sources=8)
    validated = map_validated_citations(
        answer="Invoices require approval. [SOURCE_1]",
        ordered_markers=("[SOURCE_1]",),
        source_registry=registry,
        document_titles_by_id={document_id: "Scanned Policy"},
        excerpt_max_characters=200,
    )

    assert selected.selected_chunk_count == 1
    assert registry.sources[0].chunk_id == chunk_id
    assert registry.sources[0].page_numbers == (1,)
    assert validated.answer == "Invoices require approval. [1]"
    assert validated.citations[0].document_id == document_id
    assert validated.citations[0].chunk_id == chunk_id
    assert validated.citations[0].page_number == 1
    assert "OCR image policy text" in validated.citations[0].excerpt
