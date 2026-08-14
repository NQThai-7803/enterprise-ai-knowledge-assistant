from __future__ import annotations

from collections.abc import Sequence

from app.chat.models import SelectedContextItem
from app.citations.models import PromptSource, PromptSourceRegistry
from app.models import CitationSourceType


def build_prompt_source_registry(
    *,
    context_items: Sequence[SelectedContextItem],
    max_sources: int,
) -> PromptSourceRegistry:
    if max_sources <= 0:
        msg = "max_sources must be greater than zero."
        raise ValueError(msg)
    sources: list[PromptSource] = []
    for index, item in enumerate(tuple(context_items)[:max_sources], start=1):
        source_type = CitationSourceType(item.source_type)
        if source_type == CitationSourceType.INTERNAL:
            sources.append(
                PromptSource(
                    marker=f"[SOURCE_{index}]",
                    source_type=source_type,
                    chunk_id=_require(item.chunk_id, "chunk_id"),
                    document_id=_require(item.document_id, "document_id"),
                    document_title=_require(item.document_title, "document_title"),
                    text=item.text,
                    page_numbers=_require(item.page_numbers, "page_numbers"),
                    start_page=_require(item.start_page, "start_page"),
                    end_page=_require(item.end_page, "end_page"),
                    semantic_score=item.semantic_score,
                    keyword_score=item.keyword_score,
                    hybrid_score=_require(item.hybrid_score, "hybrid_score"),
                    reranker_score=item.reranker_score,
                )
            )
            continue
        sources.append(
            PromptSource(
                marker=f"[SOURCE_{index}]",
                source_type=source_type,
                document_title=_require(item.document_title, "document_title"),
                text=item.text,
                page_numbers=item.page_numbers or (1,),
                start_page=item.start_page or 1,
                end_page=item.end_page or 1,
                source_url=_require(item.source_url, "source_url"),
                semantic_score=None,
                keyword_score=None,
                hybrid_score=_require(item.hybrid_score, "hybrid_score"),
                reranker_score=item.reranker_score,
            )
        )
    return PromptSourceRegistry(sources=tuple(sources))


def _require(value, field_name: str):  # noqa: ANN001, ANN202
    if value is None:
        msg = f"selected context item is missing {field_name}."
        raise ValueError(msg)
    return value
