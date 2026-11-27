"""BR-14: citation excerpts as shown to the user (display only; chunks and prompts unchanged)."""

from __future__ import annotations

from uuid import UUID

from app.chat.context_builder import select_context_for_prompt
from app.chat.models import SelectedContextItem
from app.citations.excerpt import build_evidence_centered_excerpt, display_text
from app.citations.mapper import map_validated_citations
from app.citations.registry import build_prompt_source_registry
from app.retrieval.models import HybridRetrievalHit

# A later chunk as the chunker stores it: its token overlap starts inside a word ("BẠCH").
CUT_CHUNK = "ẠCH VẬN HÀNH\n\n03 QUY TRÌNH KHO\n Phiếu xuất kho được duyệt trong 2 ngày."


def test_display_text_maps_symbol_font_bullets_and_keeps_length() -> None:
    text = " một  hai  ba • bốn - năm"

    shown = display_text(text)

    assert shown == "• một • hai • ba • bốn - năm"
    assert len(shown) == len(text)
    assert display_text("Tiếng Việt có dấu, 12% và 1.500.000 đồng") == (
        "Tiếng Việt có dấu, 12% và 1.500.000 đồng"
    )


def test_excerpt_drops_the_partial_first_word_of_an_overlap_chunk() -> None:
    excerpt = build_evidence_centered_excerpt(
        source_text=CUT_CHUNK,
        evidence_text="Phiếu xuất kho được duyệt trong 2 ngày.",
        max_characters=200,
        starts_mid_word=True,
    )

    assert excerpt.startswith("…VẬN HÀNH 03 QUY TRÌNH KHO")
    assert "Phiếu xuất kho được duyệt trong 2 ngày." in excerpt


def test_excerpt_keeps_the_start_without_the_overlap_flag_or_when_evidence_starts_there() -> None:
    old = build_evidence_centered_excerpt(
        source_text=CUT_CHUNK, evidence_text=None, max_characters=200
    )
    evidence_at_start = build_evidence_centered_excerpt(
        source_text=CUT_CHUNK,
        evidence_text="ẠCH VẬN HÀNH",
        max_characters=200,
        starts_mid_word=True,
    )

    assert old.startswith("ẠCH VẬN HÀNH")
    assert evidence_at_start.startswith("ẠCH VẬN HÀNH")


def test_long_overlap_excerpt_has_one_leading_ellipsis_and_fits_the_budget() -> None:
    source = "ỜNG " + "Nội dung dẫn nhập của quy trình. " * 30 + "Hạn chót nộp báo cáo là 36 giờ."

    excerpt = build_evidence_centered_excerpt(
        source_text=source,
        evidence_text="Hạn chót nộp báo cáo là 36 giờ.",
        max_characters=120,
        starts_mid_word=True,
    )

    assert excerpt.startswith("…") and not excerpt.startswith("……")
    assert "ỜNG" not in excerpt
    assert "36 giờ." in excerpt
    assert len(excerpt) <= 120


def test_mapping_shows_bullets_and_word_boundary_for_an_overlap_source() -> None:
    item = SelectedContextItem(
        ordinal=1,
        text=CUT_CHUNK,
        token_count=10,
        chunk_id=UUID(int=1),
        document_id=UUID(int=2),
        document_title="Quy trình kho",
        page_numbers=(3,),
        start_page=3,
        end_page=3,
        semantic_score=0.9,
        hybrid_score=1.0,
        starts_mid_word=True,
    )
    registry = build_prompt_source_registry(context_items=(item,), max_sources=8)

    mapped = map_validated_citations(
        answer="Phiếu xuất kho được duyệt trong 2 ngày. [SOURCE_1]",
        ordered_markers=("[SOURCE_1]",),
        source_registry=registry,
        document_titles_by_id={item.document_id: "Quy trình kho"},
        excerpt_max_characters=300,
    )

    citation = mapped.citations[0]
    assert citation.excerpt.startswith("…VẬN HÀNH")
    assert "• Phiếu xuất kho" in citation.excerpt
    assert not any("" <= ch <= "" for ch in citation.excerpt)
    assert citation.evidence_text is None or citation.evidence_text in citation.excerpt
    assert registry.sources[0].text == CUT_CHUNK  # the prompt/validation text is untouched


def _hit(chunk_index: int, *, group_id: UUID | None = None) -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=UUID(int=10 + chunk_index),
        document_id=UUID(int=99),
        document_title="Quy trình kho",
        chunk_index=chunk_index,
        text=CUT_CHUNK,
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=3,
        hybrid_score=1.0,
        semantic_score=0.9,
        semantic_rank=1,
        keyword_score=None,
        keyword_rank=None,
        matched_by=("semantic",),
        group_id=group_id,
    )


class _Counter:
    def count(self, text: str) -> int:
        return len(text.split())


def test_context_marks_only_later_text_chunks_as_starting_with_overlap() -> None:
    hits = (_hit(0), _hit(4), _hit(5, group_id=UUID(int=500)))

    selected = select_context_for_prompt(
        hits=hits,
        history_messages=(),
        question="phiếu xuất kho",
        system_prompt="system",
        token_counter=_Counter(),
        max_tokens=1000,
        whole_chunks=True,
    )

    assert [item.starts_mid_word for item in selected.items] == [False, True, False]
