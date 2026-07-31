from __future__ import annotations

from collections.abc import Sequence

from app.chat.models import SelectedContext, SelectedContextItem
from app.citations.models import PromptSource
from app.document_processing.tokenization.base import TokenCounter
from app.retrieval.models import HybridRetrievalHit

CONTEXT_START = "<retrieved_context>"
CONTEXT_END = "</retrieved_context>"


def render_context_item(ordinal: int, text: str) -> str:
    return f"--- CONTEXT ITEM {ordinal} START ---\n{text}\n--- CONTEXT ITEM {ordinal} END ---"


def render_context(items: Sequence[SelectedContextItem]) -> str:
    if not items:
        return f"{CONTEXT_START}\n{CONTEXT_END}"
    rendered_items = "\n\n".join(render_context_item(item.ordinal, item.text) for item in items)
    return f"{CONTEXT_START}\n{rendered_items}\n{CONTEXT_END}"


def render_source_context(sources: Sequence[PromptSource]) -> str:
    if not sources:
        return f"{CONTEXT_START}\n{CONTEXT_END}"
    rendered_items = "\n\n".join(render_source_context_item(source) for source in sources)
    return f"{CONTEXT_START}\n{rendered_items}\n{CONTEXT_END}"


def render_source_context_item(source: PromptSource) -> str:
    return (
        f"--- {source.label} START ---\n"
        f"Document title: {source.document_title}\n"
        f"Page: {source.start_page}\n"
        "Content:\n"
        f"{source.text}\n"
        f"--- {source.label} END ---"
    )


def render_hit_source_context_item(ordinal: int, hit: HybridRetrievalHit) -> str:
    label = f"SOURCE_{ordinal}"
    return (
        f"--- {label} START ---\n"
        f"Document title: {hit.document_title}\n"
        f"Page: {hit.start_page}\n"
        "Content:\n"
        f"{hit.text}\n"
        f"--- {label} END ---"
    )


def select_context_for_prompt(
    *,
    hits: Sequence[HybridRetrievalHit],
    history_messages: Sequence[object],
    question: str,
    system_prompt: str,
    token_counter: TokenCounter,
    max_tokens: int,
) -> SelectedContext:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be greater than zero.")
    selected: list[SelectedContextItem] = []
    base_text = _base_budget_text(
        system_prompt=system_prompt,
        history_messages=history_messages,
        question=question,
    )
    used_tokens = token_counter.count(base_text) + token_counter.count(render_source_context(()))
    for hit in hits:
        candidate_text = render_hit_source_context_item(len(selected) + 1, hit)
        candidate_tokens = token_counter.count(candidate_text)
        if used_tokens + candidate_tokens > max_tokens:
            continue
        selected.append(
            SelectedContextItem(
                ordinal=len(selected) + 1,
                text=hit.text,
                token_count=candidate_tokens,
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                document_title=hit.document_title,
                page_numbers=hit.page_numbers,
                start_page=hit.start_page,
                end_page=hit.end_page,
                semantic_score=hit.semantic_score,
                keyword_score=hit.keyword_score,
                hybrid_score=hit.hybrid_score,
            )
        )
        used_tokens += candidate_tokens
    return SelectedContext(
        items=tuple(selected),
        selected_chunk_count=len(selected),
        estimated_token_count=used_tokens,
    )


def _base_budget_text(
    *,
    system_prompt: str,
    history_messages: Sequence[object],
    question: str,
) -> str:
    history_text = "\n".join(
        f"{getattr(message, 'role', '')}: {getattr(message, 'content', '')}"
        for message in history_messages
    )
    return (
        f"{system_prompt}\n"
        f"<recent_history>\n{history_text}\n</recent_history>\n"
        f"<current_question>\n{question}\n</current_question>"
    )
