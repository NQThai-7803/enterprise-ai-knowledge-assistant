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


def test_descriptive_person_excerpt_keeps_matching_wrapped_role_record() -> None:
    text = (
        "Nguyen Anh Khoa - chiu trach nhiem ket qua kinh doanh va dieu hanh\n"
        "Tong Giam doc (CEO)\n"
        "chung\n"
        "Le Thu Ha - phu trach ky thuat, kien truc, nen tang va nang luc cong\n"
        "Giam doc Cong nghe (CTO)\n"
        "nghe\n"
        "Vo Ngoc Linh - phu trach trien khai va van hanh\n"
        "Giam doc Van hanh (COO)\n"
    )

    excerpt = query_focused_excerpt(
        text,
        "Nguoi phu trach cong nghe cua Nova Digital ten gi?",
    )

    assert "Le Thu Ha" in excerpt
    assert "Giam doc Cong nghe (CTO)" in excerpt
    assert "Nguyen Anh Khoa" not in excerpt


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


def test_broad_duration_excerpt_preserves_condition_value_rows_without_every_cue() -> None:
    text = (
        "Muc nghi Doi tuong ap dung\n"
        "12 ngay Cong viec trong dieu kien binh thuong\n"
        "Nguoi chua thanh nien hoac cong viec nang nhoc, doc hai\n"
        "14 ngay\n"
        "16 ngay Cong viec dac biet nang nhoc, doc hai\n"
        "Dang ky truoc 03 ngay; nghi 05 ngay lien tuc dang ky truoc 10 ngay.\n"
    )

    excerpt = query_focused_excerpt(
        text,
        "So ngay nghi hang nam theo nhom cong viec la bao nhieu?",
    )

    assert all(value in excerpt for value in ("12 ngay", "14 ngay", "16 ngay"))


def test_broad_duration_excerpt_keeps_wrapped_condition_before_scored_value() -> None:
    text = (
        "binh thuong\n"
        "Nguoi chua thanh nien, nguoi khuyet tat hoac cong viec nang nhoc, "
        "doc hai, nguy\n"
        "14 ngay\n"
        "hiem theo danh muc phap luat\n"
        "16 ngay Cong viec dac biet nang nhoc, doc hai, nguy hiem theo danh muc phap luat\n"
        "Nguoi lao dong lam viec chua du 12 thang. Cu du 05 nam tang them 01 ngay. "
        "Nghi nhieu lan hoac gop toi da 03 nam. Dang ky truoc 03 ngay; "
        "nghi 05 ngay lien tuc dang ky truoc 10 ngay."
    )

    excerpt = query_focused_excerpt(
        text,
        "So ngay nghi hang nam theo nhom cong viec la bao nhieu?",
    )

    assert "14 ngay" in excerpt
    assert "16 ngay" in excerpt
    assert "Nguoi chua thanh nien" in excerpt


def test_compound_excerpt_preserves_evidence_for_each_information_need() -> None:
    text = (
        "Thông tin payroll khác\n"
        "Làm thêm ngày nghỉ hằng tuần: ít nhất 200%.\n"
        "Phụ cấp on-call bù cho trạng thái sẵn sàng theo lịch.\n"
        "Thời gian thực tế xử lý ticket/sự cố được ghi nhận riêng để đánh giá OT.\n"
        + "Nội dung không liên quan. "
        * 200
    )

    excerpt = query_focused_excerpt(
        text,
        "Nhân viên on-call xử lý sự cố vào Chủ nhật thì thời gian và mức OT thế nào?",
        information_needs=(
            "Nhân viên on-call xử lý sự cố vào Chủ nhật thì thời gian",
            "Nhân viên on-call xử lý sự cố vào Chủ nhật mức OT thế nào",
        ),
    )

    assert "thời gian thực tế xử lý ticket/sự cố" in excerpt.casefold()
    assert "ít nhất 200%" in excerpt.casefold()


def test_compound_excerpt_preserves_concrete_security_control_for_ascii_need() -> None:
    text = (
        "So ngay remote thong thuong Toi da 02 ngay/tuan.\n"
        "Dang ky lich Truoc 16:00 cua ngay lam viec lien truoc.\n"
        "Nhan vien hybrid duy tri kha nang lien lac khi lam o nha.\n"
        "Nhan vien hybrid tham gia hop trong thoi gian lam viec.\n"
        "Nhan vien onboarding can kem cap truc tiep.\n"
        "Dieu kien remote tuy thuoc vi tri va phe duyet quan ly.\n"
        "An toan thong tin\n"
        "Su dung thiet bi duoc phe duyet, VPN/MFA khi ap dung; "
        "khong de nguoi khong co tham quyen tiep can tai lieu.\n"
    )

    excerpt = query_focused_excerpt(
        text,
        "Nhan vien hybrid can tuan thu bao mat nao va duoc phu cap bao nhieu?",
        information_needs=(
            "Nhan vien hybrid can tuan thu bao mat nao",
            "Nhan vien hybrid duoc phu cap bao nhieu",
        ),
    )

    assert "thiet bi duoc phe duyet" in excerpt.casefold()
    assert "vpn/mfa" in excerpt.casefold()
    assert "khong co tham quyen" in excerpt.casefold()


def test_compound_excerpt_preserves_named_eligibility_row_and_header() -> None:
    text = (
        "Quyền lợi Từ ngày nhận việc Sau thử việc Sau ngày nghỉ việc\n"
        "Bảo hiểm bắt buộc Theo điều kiện pháp luật Có Tiếp tục\n"
        "Có thể tạm dừng theo hợp đồng bảo hiểm\n"
        "NovaCare Không Có Kết thúc theo ngày hiệu lực bảo hiểm\n"
        + "Nội dung phúc lợi khác. "
        * 100
    )

    excerpt = query_focused_excerpt(
        text,
        "NovaCare có từ ngày đầu không và nội trú tối đa bao nhiêu?",
        information_needs=(
            "NovaCare có từ ngày đầu không",
            "NovaCare nội trú tối đa bao nhiêu",
        ),
    )

    assert "quyền lợi từ ngày nhận việc sau thử việc" in excerpt.casefold()
    assert "novacare không có" in excerpt.casefold()


def test_night_work_excerpt_prefers_regular_night_rate_over_night_overtime() -> None:
    text = (
        "Lam them ngay nghi hang tuan It nhat 200%.\n"
        "Duoc tra them it nhat 30% tien luong tinh theo don gia/tien\n"
        "Lam viec ban dem luong gio cua ngay lam viec binh thuong.\n"
        "Ngoai tien OT va khoan 30% ban dem, con tra them it nhat 20%\n"
        "Lam them vao ban dem theo co so phap luat ap dung.\n"
    )

    excerpt = query_focused_excerpt(text, "Lam viec ban dem duoc cong them bao nhieu?")

    assert "30%" in excerpt
    assert "Lam viec ban dem" in excerpt
    assert "20%" not in excerpt


def test_pay_date_excerpt_rebinds_value_before_wrapped_field_label() -> None:
    text = (
        "Moc Quy dinh noi bo\n"
        "Ky cong Tu ngay 01 den het ngay cuoi cung cua thang.\n"
        "Han quan ly xac nhan dieu chinh Ngay lam viec thu 4 cua thang ke tiep.\n"
        "Ngay 10 cua thang ke tiep; neu trung ngay nghi/le, Finance\n"
        "Ngay tra luong thuc hien vao ngay lam viec lien truoc.\n"
    )

    excerpt = query_focused_excerpt(text, "Luong thuong ve ngay nao?")

    assert excerpt.startswith("Answer-focused evidence:\nNgay tra luong")
    assert "Ngay 10 cua thang ke tiep" in excerpt.splitlines()[1]


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
