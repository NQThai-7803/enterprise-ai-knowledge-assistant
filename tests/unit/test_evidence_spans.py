"""BR-15: evidence_spans, where a citation's evidence sits in its excerpt (display only).

Invented texts with the shapes seen on the demo stack: UAT Q016 (evidence that skips a heading,
several spans), Q043 (a value that occurs twice, one span) and Q084 (evidence that ends inside
an excerpt word, one span).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from app.citations.excerpt import evidence_spans
from app.schemas.chat import CitationRead


def pieces(excerpt: str, evidence: str | None) -> list[str]:
    return [excerpt[start:end] for start, end in evidence_spans(excerpt, evidence)]


def test_evidence_that_skips_a_heading_gives_one_span_per_part() -> None:  # Q016 shape
    excerpt = (
        "…ẾU MỤC 03 QUY ĐỊNH HỌP Quy tắc cho nhóm làm việc từ xa của văn phòng Điều 7. "
        "Thời lượng họp định kỳ •Mỗi buổi họp kéo dài 45 phút, tối đa 2 buổi/tuần, trừ lịch "
        "riêng được duyệt. •Biên bản gửi trong ngày…"
    )
    evidence = (
        "Quy tắc cho nhóm làm việc từ xa của văn phòng Thời lượng họp định kỳ •Mỗi buổi họp "
        "kéo dài 45 phút, tối đa 2 buổi/tuần, trừ lịch riêng được"
    )

    assert pieces(excerpt, evidence) == [
        "Quy tắc cho nhóm làm việc từ xa của văn phòng",
        "Thời lượng họp định kỳ •Mỗi buổi họp kéo dài 45 phút, tối đa 2 buổi/tuần, trừ lịch "
        "riêng được",
    ]


def test_a_value_that_occurs_twice_gives_one_span_at_its_first_place() -> None:  # Q043 shape
    excerpt = "…Trường hợp Thời gian Chuyển nhà 05 ngày Đi công tác xa 02 ngày Tang lễ; 05 ngày…"

    spans = evidence_spans(excerpt, "05 ngày")

    assert len(spans) == 1
    assert excerpt[spans[0][0] : spans[0][1]] == "05 ngày"
    assert spans[0][0] == excerpt.index("05 ngày")


def test_evidence_ending_inside_an_excerpt_word_gives_one_exact_span() -> None:  # Q084 shape
    excerpt = "…3. Phụ cấp Khoản Hạn mức Đi lại 3.600.000 đ/năm có hóa đơn hợp lệ…"

    assert pieces(excerpt, "3.600.000 đ") == ["3.600.000 đ"]


def test_bullet_and_leading_ellipsis_keep_offsets_exact() -> None:
    excerpt = "…•Phụ cấp gửi xe 300.000 đồng mỗi tháng. •Tiếp theo"

    spans = evidence_spans(excerpt, "•Phụ cấp gửi xe 300.000 đồng")

    assert spans == [(1, 1 + len("•Phụ cấp gửi xe 300.000 đồng"))]


def test_symbol_font_characters_in_an_older_stored_citation_still_match() -> None:
    excerpt = "Danh mục Phụ cấp gửi xe 300.000 đồng mỗi tháng."

    assert pieces(excerpt, "•Phụ cấp gửi xe 300.000 đồng") == ["Phụ cấp gửi xe 300.000 đồng"]


def test_evidence_not_in_the_excerpt_gives_no_span() -> None:
    excerpt = "…Lịch trực được chia theo tuần và công bố trên bảng tin…"

    assert evidence_spans(excerpt, "Phụ cấp gửi xe 300.000 đồng") == []
    assert evidence_spans(excerpt, None) == []
    assert evidence_spans(excerpt, "") == []
    # One common word is not evidence: a chance match of "và" is not highlighted.
    assert evidence_spans(excerpt, "Ngày nghỉ và giờ làm thêm được cộng dồn") == []


def test_citation_read_returns_spans_and_keeps_evidence_text() -> None:
    citation = SimpleNamespace(
        document_id=UUID(int=1),
        document_title="Quy chế",
        chunk_id=UUID(int=2),
        page_number=3,
        excerpt="…Chuyển nhà 05 ngày Đi công tác xa 02 ngày…",
        evidence_text="05 ngày",
        relevance_score=0.8,
        citation_order=1,
    )

    data = CitationRead.from_citation(citation).model_dump(mode="json")

    assert data["evidence_text"] == "05 ngày"
    start = citation.excerpt.index("05 ngày")
    assert data["evidence_spans"] == [{"start": start, "end": start + len("05 ngày")}]

    no_evidence = CitationRead.from_citation(
        SimpleNamespace(**{**vars(citation), "evidence_text": None})
    )
    assert no_evidence.model_dump(mode="json")["evidence_spans"] == []
