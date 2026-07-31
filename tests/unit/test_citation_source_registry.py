from __future__ import annotations

from uuid import UUID

from app.chat.models import SelectedContextItem
from app.citations.registry import build_prompt_source_registry


def item(index: int, text: str = "source text") -> SelectedContextItem:
    return SelectedContextItem(
        ordinal=index,
        text=text,
        token_count=10,
        chunk_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
        document_id=UUID(f"00000000-0000-0000-0001-{index:012d}"),
        document_title=f"Document {index}",
        page_numbers=(index,),
        start_page=index,
        end_page=index,
        semantic_score=0.8,
        keyword_score=None,
        hybrid_score=1.0,
    )


def test_source_markers_start_at_one() -> None:
    registry = build_prompt_source_registry(context_items=(item(1),), max_sources=8)

    assert [source.marker for source in registry.sources] == ["[SOURCE_1]"]


def test_source_markers_follow_context_order() -> None:
    registry = build_prompt_source_registry(
        context_items=(item(1, "first"), item(2, "second")),
        max_sources=8,
    )

    assert [source.text for source in registry.sources] == ["first", "second"]
    assert [source.marker for source in registry.sources] == ["[SOURCE_1]", "[SOURCE_2]"]


def test_source_registry_contains_only_selected_context() -> None:
    registry = build_prompt_source_registry(
        context_items=(item(1), item(2), item(3)),
        max_sources=2,
    )

    assert [source.chunk_id for source in registry.sources] == [item(1).chunk_id, item(2).chunk_id]


def test_source_registry_does_not_include_embeddings() -> None:
    registry = build_prompt_source_registry(context_items=(item(1),), max_sources=8)

    assert not hasattr(registry.sources[0], "embedding")


def test_source_text_not_in_repr() -> None:
    registry = build_prompt_source_registry(
        context_items=(item(1, "CONFIDENTIAL_SOURCE_EXCERPT"),),
        max_sources=8,
    )

    assert "CONFIDENTIAL_SOURCE_EXCERPT" not in repr(registry.sources[0])
    assert "CONFIDENTIAL_SOURCE_EXCERPT" not in repr(registry)


def test_source_markers_are_deterministic() -> None:
    context_items = (item(1), item(2))

    first = build_prompt_source_registry(context_items=context_items, max_sources=8)
    second = build_prompt_source_registry(context_items=context_items, max_sources=8)

    assert [source.marker for source in first.sources] == [
        source.marker for source in second.sources
    ]


def test_source_count_is_bounded() -> None:
    registry = build_prompt_source_registry(
        context_items=(item(1), item(2), item(3)),
        max_sources=2,
    )

    assert len(registry.sources) == 2
