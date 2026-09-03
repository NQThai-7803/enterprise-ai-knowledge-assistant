from __future__ import annotations

from uuid import UUID

import pytest

from app.chat.models import SelectedContextItem
from app.citations.errors import CitationMappingError
from app.citations.evidence import extract_exact_evidence
from app.citations.excerpt import build_evidence_centered_excerpt, build_excerpt
from app.citations.mapper import map_validated_citations, rewrite_internal_markers
from app.citations.registry import build_prompt_source_registry


def item(
    index: int,
    *,
    semantic_score: float | None = 0.87,
    text: str = "Nhân viên chính thức được hưởng 12 ngày nghỉ phép theo HD-2026-AL.",
) -> SelectedContextItem:
    return SelectedContextItem(
        ordinal=index,
        text=text,
        token_count=10,
        chunk_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
        document_id=UUID(f"00000000-0000-0000-0001-{index:012d}"),
        document_title=f"Quy chế {index}",
        page_numbers=(index,),
        start_page=index,
        end_page=index,
        semantic_score=semantic_score,
        keyword_score=1.2 if semantic_score is None else None,
        hybrid_score=1.0,
    )


def registry():
    return build_prompt_source_registry(context_items=(item(1), item(2)), max_sources=8)


def test_internal_marker_rewritten_to_public_number() -> None:
    assert rewrite_internal_markers("A [SOURCE_1].", {"[SOURCE_1]": "[1]"}) == "A [1]."


def test_non_contiguous_internal_markers_are_renumbered() -> None:
    answer = "A [SOURCE_4]. B [SOURCE_2]. A again [SOURCE_4]."

    rewritten = rewrite_internal_markers(answer, {"[SOURCE_4]": "[1]", "[SOURCE_2]": "[2]"})

    assert rewritten == "A [1]. B [2]. A again [1]."


def test_rewrite_preserves_non_marker_text_and_vietnamese() -> None:
    answer = "Nhân viên được nghỉ phép [SOURCE_1]. [SOURCE_X]"

    rewritten = rewrite_internal_markers(answer, {"[SOURCE_1]": "[1]"})

    assert rewritten == "Nhân viên được nghỉ phép [1]. [SOURCE_X]"


def test_excerpt_preserves_vietnamese_and_business_identifier() -> None:
    excerpt = build_excerpt(
        source_text="  Nhân viên dùng mã HD-2026-AL được nghỉ phép.  ",
        max_characters=80,
    )

    assert excerpt == "Nhân viên dùng mã HD-2026-AL được nghỉ phép."


def test_excerpt_respects_maximum_length_and_adds_ellipsis() -> None:
    excerpt = build_excerpt(source_text="Một hai ba bốn năm sáu", max_characters=12)

    assert len(excerpt) <= 12
    assert excerpt.endswith("…")


def test_excerpt_rejects_blank_source() -> None:
    with pytest.raises(ValueError):
        build_excerpt(source_text="   ", max_characters=20)


def test_evidence_centered_excerpt_keeps_late_numeric_fact() -> None:
    source_text = (
        "Unrelated document preface. " * 30
        + "Lam them ngay nghi hang tuan it nhat 200%. "
        + "Unrelated appendix. " * 20
    )

    excerpt = build_evidence_centered_excerpt(
        source_text=source_text,
        evidence_text="200%",
        max_characters=200,
    )

    assert len(excerpt) <= 200
    assert "nghi hang tuan" in excerpt
    assert "200%" in excerpt


def test_mapping_centers_excerpt_on_shared_value_when_markers_are_joined() -> None:
    source_registry = build_prompt_source_registry(
        context_items=(
            item(
                1,
                text="Preface " * 90 + "Lam them ngay nghi hang tuan it nhat 200%.",
            ),
        ),
        max_sources=8,
    )

    mapped = map_validated_citations(
        answer="Thoi gian duoc ghi nhan. Muc OT la 200%. [SOURCE_1]",
        ordered_markers=("[SOURCE_1]",),
        source_registry=source_registry,
        document_titles_by_id={item(1).document_id: "Policy"},
        excerpt_max_characters=180,
    )

    assert "nghi hang tuan" in mapped.citations[0].excerpt
    assert "200%" in mapped.citations[0].excerpt


def test_mapping_uses_backend_metadata_and_order() -> None:
    source_registry = registry()

    mapped = map_validated_citations(
        answer="Nghỉ phép là 12 ngày [SOURCE_2]. Chính sách áp dụng [SOURCE_1].",
        ordered_markers=("[SOURCE_2]", "[SOURCE_1]"),
        source_registry=source_registry,
        document_titles_by_id={
            source.document_id: f"Current {source.document_title}"
            for source in source_registry.sources
        },
        excerpt_max_characters=500,
    )

    assert mapped.answer == "Nghỉ phép là 12 ngày [1]. Chính sách áp dụng [2]."
    assert [citation.citation_order for citation in mapped.citations] == [1, 2]
    assert mapped.citations[0].document_id == item(2).document_id
    assert mapped.citations[0].chunk_id == item(2).chunk_id
    assert mapped.citations[0].page_number == 2
    assert mapped.citations[0].document_title == "Current Quy chế 2"
    assert "Nhân viên chính thức" in mapped.citations[0].excerpt
    assert mapped.citations[0].relevance_score == 0.87
    assert mapped.citations[0].evidence_text is not None


def test_mapping_uses_null_relevance_for_keyword_only() -> None:
    source_registry = build_prompt_source_registry(
        context_items=(item(1, semantic_score=None),),
        max_sources=8,
    )

    mapped = map_validated_citations(
        answer="A [SOURCE_1].",
        ordered_markers=("[SOURCE_1]",),
        source_registry=source_registry,
        document_titles_by_id={source_registry.sources[0].document_id: "Current"},
        excerpt_max_characters=500,
    )

    assert mapped.citations[0].relevance_score is None


def test_mapping_fails_when_page_metadata_is_invalid() -> None:
    source_registry = build_prompt_source_registry(context_items=(item(1),), max_sources=8)
    bad_source = source_registry.sources[0]
    object.__setattr__(bad_source, "page_numbers", (2,))

    with pytest.raises(CitationMappingError):
        map_validated_citations(
            answer="A [SOURCE_1].",
            ordered_markers=("[SOURCE_1]",),
            source_registry=source_registry,
            document_titles_by_id={bad_source.document_id: "Current"},
            excerpt_max_characters=500,
        )


def web_item(index: int) -> SelectedContextItem:
    from app.models import CitationSourceType

    return SelectedContextItem(
        ordinal=index,
        text="OpenAI Docs describe the Responses API.",
        token_count=10,
        document_title="OpenAI Docs",
        source_type=CitationSourceType.WEB,
        source_url="https://platform.openai.com/docs/api-reference/responses",
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        hybrid_score=1.0,
    )


def test_mapping_web_citation_uses_backend_url_and_no_internal_ids() -> None:
    from app.models import CitationSourceType

    source_registry = build_prompt_source_registry(context_items=(web_item(1),), max_sources=8)

    mapped = map_validated_citations(
        answer="Responses are documented online [SOURCE_1].",
        ordered_markers=("[SOURCE_1]",),
        source_registry=source_registry,
        document_titles_by_id={},
        excerpt_max_characters=500,
    )

    citation = mapped.citations[0]
    assert mapped.answer == "Responses are documented online [1]."
    assert citation.source_type == CitationSourceType.WEB
    assert citation.document_id is None
    assert citation.chunk_id is None
    assert citation.document_title == "OpenAI Docs"
    assert citation.source_url == "https://platform.openai.com/docs/api-reference/responses"
    assert citation.relevance_score is None


def test_extract_exact_evidence_prefers_matching_time_value() -> None:
    answer = "Thời gian làm việc là 8:00 - 16:00 [SOURCE_1]."

    source_text = (
        "Ngày làm việc từ Thứ Hai đến Thứ Sáu.\n"
        "Thời gian làm việc 8:00 - 16:00.\n"
        "Thời gian nghỉ trưa 12:00 - 13:00."
    )

    evidence = extract_exact_evidence(
        answer=answer,
        marker="[SOURCE_1]",
        source_text=source_text,
    )

    assert evidence == "8:00 - 16:00"


def test_extract_exact_evidence_prefers_named_ceo_passage() -> None:
    answer = "CEO của Nova Digital là Nguyễn Anh Khoa [SOURCE_1]."

    source_text = (
        "TỔNG GIÁM ĐỐC (CEO) BAN ĐIỀU HÀNH.\n"
        "Nguyễn Anh Khoa - Tổng Giám đốc (CEO) - "
        "chịu trách nhiệm kết quả kinh doanh và điều hành chung."
    )

    evidence = extract_exact_evidence(
        answer=answer,
        marker="[SOURCE_1]",
        source_text=source_text,
    )

    assert evidence is not None
    assert "Nguyễn Anh Khoa" in evidence
    assert "Tổng Giám đốc" in evidence


def test_extract_exact_evidence_returns_none_for_weak_match() -> None:
    evidence = extract_exact_evidence(
        answer="CEO là ai? [SOURCE_1]",
        marker="[SOURCE_1]",
        source_text="Thông tin hoàn toàn không liên quan.",
    )

    assert evidence is None


def test_extract_exact_evidence_keeps_verbatim_topic_clause_over_nearby_overlap() -> None:
    clause = (
        "Participation in the review does not guarantee an adjustment. "
        "The documented legal minimum still applies."
    )
    evidence = extract_exact_evidence(
        answer=f"{clause} [SOURCE_1]",
        marker="[SOURCE_1]",
        source_text=(
            "A nearby transfer may not change compensation when roles are equivalent.\n"
            f"{clause}\n"
            "An unrelated appendix follows."
        ),
    )

    assert evidence == clause


def test_extract_exact_evidence_preserves_rate_unit() -> None:
    evidence = extract_exact_evidence(
        answer=("Nhân viên làm việc 8 giờ/ngày [SOURCE_1]."),
        marker="[SOURCE_1]",
        source_text=("Tổng thời gian làm việc 8 giờ/ngày; 40 giờ/tuần."),
    )

    assert evidence == "8 giờ/ngày"


def test_extract_exact_evidence_preserves_weekly_rate_unit() -> None:
    evidence = extract_exact_evidence(
        answer=("Tổng thời gian làm việc là 40 giờ/tuần [SOURCE_1]."),
        marker="[SOURCE_1]",
        source_text=("Tổng thời gian làm việc 8 giờ/ngày; 40 giờ/tuần."),
    )

    assert evidence == "40 giờ/tuần"


def test_mapping_deduplicates_same_document_same_evidence() -> None:
    first = item(1)
    second = item(2)

    object.__setattr__(
        first,
        "text",
        "Quy mô nhân sự khoảng 180 người.",
    )

    object.__setattr__(
        second,
        "text",
        "Công ty hiện có khoảng 180 người.",
    )

    object.__setattr__(
        first,
        "document_id",
        UUID("00000000-0000-0000-0001-000000000001"),
    )

    object.__setattr__(
        second,
        "document_id",
        first.document_id,
    )

    object.__setattr__(
        first,
        "semantic_score",
        0.90,
    )

    object.__setattr__(
        second,
        "semantic_score",
        0.80,
    )

    source_registry = build_prompt_source_registry(
        context_items=(first, second),
        max_sources=8,
    )

    mapped = map_validated_citations(
        answer=("Quy mô nhân sự là 180 người [SOURCE_1] [SOURCE_2]."),
        ordered_markers=(
            "[SOURCE_1]",
            "[SOURCE_2]",
        ),
        source_registry=source_registry,
        document_titles_by_id={
            first.document_id: "Nova Digital",
        },
        excerpt_max_characters=500,
    )

    assert mapped.answer == ("Quy mô nhân sự là 180 người [1].")

    assert len(mapped.citations) == 1

    assert mapped.citations[0].evidence_text == "180 người"


def test_mapping_keeps_different_evidence_in_same_document() -> None:
    first = item(1)
    second = item(2)

    shared_document_id = UUID("00000000-0000-0000-0001-000000000001")

    object.__setattr__(
        first,
        "document_id",
        shared_document_id,
    )

    object.__setattr__(
        second,
        "document_id",
        shared_document_id,
    )

    object.__setattr__(
        first,
        "text",
        "Nguyễn Anh Khoa - Tổng Giám đốc (CEO).",
    )

    object.__setattr__(
        second,
        "text",
        "Lê Thu Hà - Giám đốc Công nghệ (CTO).",
    )

    source_registry = build_prompt_source_registry(
        context_items=(first, second),
        max_sources=8,
    )

    mapped = map_validated_citations(
        answer=("CEO là Nguyễn Anh Khoa [SOURCE_1]. CTO là Lê Thu Hà [SOURCE_2]."),
        ordered_markers=(
            "[SOURCE_1]",
            "[SOURCE_2]",
        ),
        source_registry=source_registry,
        document_titles_by_id={
            shared_document_id: "Nova Digital",
        },
        excerpt_max_characters=500,
    )

    assert len(mapped.citations) == 2

    assert mapped.answer == ("CEO là Nguyễn Anh Khoa [1]. CTO là Lê Thu Hà [2].")


def test_mapping_preserves_three_claims_from_three_documents_and_public_order() -> None:
    sources = [item(index) for index in range(1, 4)]
    texts = (
        "Remote limit is 2 days per week.",
        "Lunch allowance is 900,000 VND per month.",
        "Inpatient coverage is 150 million VND per year.",
    )
    for index, source in enumerate(sources, start=1):
        object.__setattr__(source, "text", texts[index - 1])
        object.__setattr__(
            source,
            "document_id",
            UUID(f"00000000-0000-0000-0002-{index:012d}"),
        )

    source_registry = build_prompt_source_registry(
        context_items=tuple(sources),
        max_sources=8,
    )
    mapped = map_validated_citations(
        answer=(
            "Remote is limited to 2 days per week [SOURCE_1]. "
            "Lunch allowance is 900,000 VND per month [SOURCE_2]. "
            "Inpatient coverage is 150 million VND per year [SOURCE_3]."
        ),
        ordered_markers=("[SOURCE_1]", "[SOURCE_2]", "[SOURCE_3]"),
        source_registry=source_registry,
        document_titles_by_id={
            source.document_id: f"Document {index}" for index, source in enumerate(sources, start=1)
        },
        excerpt_max_characters=500,
    )

    assert mapped.answer.endswith("[3].")
    assert len(mapped.citations) == 3
    assert [citation.citation_order for citation in mapped.citations] == [1, 2, 3]
    assert len({citation.document_id for citation in mapped.citations}) == 3


def test_extract_exact_evidence_can_return_adjacent_relationship_passage() -> None:
    evidence = extract_exact_evidence(
        answer=("Khong. CarePlus la bao hiem bo sung; BHYT la bao hiem bat buoc [SOURCE_1]."),
        marker="[SOURCE_1]",
        source_text=(
            "Health coverage\n"
            "BHYT: bao hiem y te bat buoc theo quy dinh phap luat.\n"
            "CarePlus: bao hiem suc khoe bo sung cho nhan vien.\n"
            "Claims are submitted through HR."
        ),
    )

    assert evidence is not None
    assert "BHYT" in evidence
    assert "bat buoc" in evidence
    assert "CarePlus" in evidence
    assert "bo sung" in evidence


def test_extract_exact_evidence_supports_terse_replacement_answer() -> None:
    evidence = extract_exact_evidence(
        answer="Khong. CarePlus khong thay the BHYT bat buoc [SOURCE_1].",
        marker="[SOURCE_1]",
        source_text=(
            "Health coverage\n"
            "BHYT: bao hiem y te bat buoc theo quy dinh phap luat.\n"
            "CarePlus: bao hiem suc khoe bo sung cho nhan vien.\n"
            "Claims are submitted through HR."
        ),
    )

    assert evidence is not None
    assert "BHYT" in evidence
    assert "bat buoc" in evidence
    assert "CarePlus" in evidence
    assert "bo sung" in evidence
