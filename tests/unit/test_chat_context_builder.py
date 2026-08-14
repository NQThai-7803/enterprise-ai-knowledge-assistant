from __future__ import annotations

from uuid import UUID

import pytest

from app.chat.context_builder import (
    query_focused_excerpt,
    render_context,
    select_context_for_prompt,
)
from app.models import CitationSourceType
from app.retrieval.models import HybridRetrievalHit
from app.web_search.models import WebSearchResult


class FakeCounter:
    def count(self, text: str) -> int:
        if "huge chunk" in text:
            return 10_000
        return len(text.split())

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens) -> str:  # noqa: ANN001
        return " ".join("x" for _ in tokens)


def hit(index: int, text: str, token_count: int = 3) -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
        document_id=UUID(f"00000000-0000-0000-0001-{index:012d}"),
        document_title="Document",
        chunk_index=index,
        text=text,
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=token_count,
        hybrid_score=1.0,
        semantic_score=0.9,
        semantic_rank=index + 1,
        keyword_score=None,
        keyword_rank=None,
        matched_by=("semantic",),
    )


def test_person_acronym_excerpt_keeps_requested_role_record() -> None:
    text = (
        "Alice Minh Nguyen - accountable for company results and operations\n"
        "Chief Executive Officer (CEO)\n"
        "Bob Thu Tran - accountable for technology platforms\n"
        "Chief Technology Officer (CTO)\n"
        "Carol Linh Pham - accountable for operations\n"
        "Chief Operating Officer (COO)\n"
    )

    excerpt = query_focused_excerpt(text, "CTO Nova Digital la ai?")

    assert "Bob Thu Tran" in excerpt
    assert "Chief Technology Officer (CTO)" in excerpt
    assert "Alice Minh Nguyen" not in excerpt
    assert "Chief Executive Officer (CEO)" not in excerpt


def test_person_acronym_excerpt_formats_wrapped_role_records() -> None:
    text = (
        "Executive team\n"
        "Alice Minh Nguyen - accountable for company results and operations\n"
        "Chief Executive Officer (CEO)\n"
        "overall\n"
        "Bob Thu Tran - accountable for technology platforms\n"
        "Chief Technology Officer (CTO)\n"
        "delivery\n"
    )

    excerpt = query_focused_excerpt(text, "CEO Example Digital la Bob Thu Tran dung khong?")

    assert "Alice Minh Nguyen - Chief Executive Officer (CEO)" in excerpt
    assert "accountable for company results and operations overall" in excerpt
    assert "Bob Thu Tran - Chief Technology Officer (CTO)" in excerpt


def test_multi_value_excerpt_reconstructs_wrapped_number_rows() -> None:
    text = (
        "Annual leave table\n"
        "12 days Work in normal conditions\n"
        "Protected workers or hazardous work\n"
        "14 days\n"
        "under the legal list\n"
        "16 days Especially hazardous work under the legal list\n"
    )

    excerpt = query_focused_excerpt(text, "Does every worker receive 12 days?")

    assert "- 12 days Work in normal conditions" in excerpt
    assert "- 14 days Protected workers or hazardous work under the legal list" in excerpt
    assert "- 16 days Especially hazardous work under the legal list" in excerpt


def test_context_selects_highest_ranked_hits_first() -> None:
    selected = select_context_for_prompt(
        hits=(hit(0, "first chunk"), hit(1, "second chunk")),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=100,
    )
    assert [item.text for item in selected.items] == ["first chunk", "second chunk"]


def test_context_respects_token_budget_and_uses_whole_chunks() -> None:
    selected = select_context_for_prompt(
        hits=(hit(0, "small"), hit(1, "too many tokens for remaining budget")),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=25,
    )
    assert [item.text for item in selected.items] == ["small"]


def test_context_returns_empty_when_no_chunk_fits() -> None:
    selected = select_context_for_prompt(
        hits=(hit(0, "too many tokens for budget"),),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=5,
    )
    assert selected.items == ()
    assert selected.selected_chunk_count == 0


def test_context_does_not_reorder_hits_after_skip() -> None:
    selected = select_context_for_prompt(
        hits=(
            hit(0, "huge chunk that cannot fit because it has many many many many words"),
            hit(1, "small"),
            hit(2, "third"),
        ),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=40,
    )
    assert [item.text for item in selected.items] == ["small", "third"]


def test_context_does_not_return_embeddings() -> None:
    selected = select_context_for_prompt(
        hits=(hit(0, "context"),),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=100,
    )
    assert not hasattr(selected.items[0], "embedding")


def test_context_does_not_log_chunk_text(caplog: pytest.LogCaptureFixture) -> None:
    select_context_for_prompt(
        hits=(hit(0, "CONFIDENTIAL_CONTEXT_BUILDER"),),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=100,
    )
    assert "CONFIDENTIAL_CONTEXT_BUILDER" not in caplog.text


def test_history_and_question_are_counted_in_budget() -> None:
    selected = select_context_for_prompt(
        hits=(hit(0, "small"),),
        history_messages=(
            type("Message", (), {"role": "USER", "content": "many history tokens"})(),
        ),
        question="many question tokens",
        system_prompt="many system tokens",
        token_counter=FakeCounter(),
        max_tokens=10,
    )
    assert selected.items == ()


def test_render_context_uses_delimiters() -> None:
    selected = select_context_for_prompt(
        hits=(hit(0, "context"),),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=100,
    )
    rendered = render_context(selected.items)
    assert rendered.startswith("<retrieved_context>")
    assert rendered.endswith("</retrieved_context>")


def web_result(index: int, text: str = "web content") -> WebSearchResult:
    return WebSearchResult(
        title=f"Web Source {index}",
        url=f"https://example.com/result-{index}",
        snippet=text,
        content=text,
        provider="mock",
        rank=index + 1,
        score=1.0,
    )


def test_context_merges_internal_and_web_results_in_prompt_order() -> None:
    selected = select_context_for_prompt(
        hits=(hit(0, "internal chunk"),),
        web_results=(web_result(0, "web chunk"),),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=100,
    )

    assert [item.source_type for item in selected.items] == [
        CitationSourceType.INTERNAL,
        CitationSourceType.WEB,
    ]
    assert selected.items[1].source_url == "https://example.com/result-0"
    assert selected.items[1].document_id is None
    assert selected.items[1].chunk_id is None


def test_context_budget_applies_to_web_results() -> None:
    selected = select_context_for_prompt(
        hits=(),
        web_results=(web_result(0, "too many tokens for budget"),),
        history_messages=(),
        question="question",
        system_prompt="system",
        token_counter=FakeCounter(),
        max_tokens=5,
    )

    assert selected.items == ()
