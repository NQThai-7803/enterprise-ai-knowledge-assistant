from __future__ import annotations

from uuid import UUID

import pytest

from app.chat.context_builder import (
    query_focused_excerpt,
    render_context,
    select_context_for_prompt,
)
from app.citations.evidence import extract_exact_evidence
from app.models import CitationSourceType
from app.retrieval.models import HybridRetrievalHit
from app.retrieval.question_analysis import analyze_question
from app.retrieval.structured import selected_structural_line_indexes
from app.services.grounded_answer_service import _is_salary_band_request
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


def test_business_area_excerpt_restores_pdf_interleaved_list_field() -> None:
    text = (
        "Ho so tong quan\n"
        "Ten doanh nghiep Aster Cloud Joint Stock Company\n"
        "Phan mem doanh nghiep, AI va du lieu, dien toan dam may, an toan\n"
        "Linh vuc hoat dong\n"
        "thong tin, dich vu van hanh so\n"
        "Website https://aster.example\n"
    )

    excerpt = query_focused_excerpt(text, "Cong ty Aster Cloud dang lam nhung mang gi?")

    assert excerpt.startswith("Answer-focused evidence:\nLinh vuc hoat dong: ")
    assert "Phan mem doanh nghiep, AI va du lieu, dien toan dam may" in excerpt
    assert "an toan thong tin, dich vu van hanh so" in excerpt
    assert "Joint Stock Company" not in excerpt
    evidence = extract_exact_evidence(
        answer=(
            "Aster Cloud lam phan mem doanh nghiep, AI va du lieu, dien toan dam may, "
            "an toan thong tin va dich vu van hanh so. [SOURCE_1]"
        ),
        marker="[SOURCE_1]",
        source_text=excerpt,
    )
    assert evidence is not None
    assert "Linh vuc hoat dong" in evidence
    assert "dich vu van hanh so" in evidence


def test_organization_percentage_excerpt_preserves_split_subject_and_value() -> None:
    text = (
        "Ho so tong quan\n"
        "Khoang 140 nguoi; 47% thuoc khoi ky thuat, du lieu va an toan thong\n"
        "Quy mo nhan su\n"
        "tin\n"
        "Phuc loi 12% theo bang rieng\n"
    )

    excerpt = query_focused_excerpt(
        text,
        "Khoang bao nhieu phan tram nhan su lam ky thuat, data voi security?",
    )

    assert excerpt == (
        "Answer-focused evidence:\n"
        "Quy mo nhan su: Khoang 140 nguoi; 47% thuoc khoi ky thuat, "
        "du lieu va an toan thong tin"
    )
    assert "12%" not in excerpt


def test_office_location_excerpt_excludes_unrelated_headquarters_and_policy() -> None:
    text = (
        "Tru so chinh Tang 8, Toa nha Aster Hub, Thanh pho Bac Son\n"
        "Van phong Thanh pho Bac Son, Thanh pho Nam Son va Tinh Hai Son\n"
        "Nhan vien co the lam viec tai van phong theo quy dinh.\n"
    )

    excerpt = query_focused_excerpt(text, "Aster Cloud co van phong o dau?")

    assert excerpt == (
        "Answer-focused evidence:\nVăn phòng: Thanh pho Bac Son, Thanh pho Nam Son va Tinh Hai Son"
    )
    assert "Tang 8" not in excerpt


def test_person_acronym_name_wording_keeps_late_requested_role_record() -> None:
    text = (
        "Nguyen Anh Khoa - accountable for company results\n"
        "Chief Executive Officer (CEO)\n"
        "Le Thu Ha - accountable for technology\n"
        "Chief Technology Officer (CTO)\n"
        "Vo Ngoc Linh - accountable for operations\n"
        "Chief Operating Officer (COO)\n"
        "Pham Gia Minh - accountable for finance and legal\n"
        "Chief Financial Officer (CFO)\n"
        "Truong Thanh An - accountable for people and culture\n"
        "Chief Human Resources Officer (CHRO)\n"
    )

    excerpt = query_focused_excerpt(text, "CFO ben cong ty ten gi?")

    assert "Pham Gia Minh - Chief Financial Officer (CFO)" in excerpt
    assert "Le Thu Ha" not in excerpt
    assert "Chief Technology Officer (CTO)" not in excerpt


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


def test_person_acronym_excerpt_supports_explicit_confirmation_wording() -> None:
    text = (
        "Nguyen Anh Khoa - chiu trach nhiem dieu hanh\n"
        "Tong Giam doc (CEO)\n"
        "Le Thu Ha - phu trach ky thuat\n"
        "Giam doc Cong nghe (CTO)\n"
    )

    excerpt = query_focused_excerpt(
        text,
        "Toi biet chac CEO Nova Digital la Le Thu Ha, hay xac nhan.",
    )

    assert "Nguyen Anh Khoa - Tong Giam doc (CEO)" in excerpt
    assert "Le Thu Ha - Giam doc Cong nghe (CTO)" in excerpt


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


def test_holiday_ot_excerpt_keeps_bound_base_rate_not_adjacent_night_premium() -> None:
    text = (
        "Muc tra toi thieu tham chieu\n"
        "Lam them ngay lam viec binh thuong\n"
        "It nhat 150%.\n"
        "Lam them ngay nghi hang tuan\n"
        "It nhat 200%.\n"
        "It nhat 300%, chua bao gom tien luong ngay le/ngay nghi.\n"
        "Lam them ngay le, Tet, ngay nghi co huong luong\n"
        "Duoc tra them it nhat 30% tien luong.\n"
        "Lam viec ban dem\n"
    )

    excerpt = query_focused_excerpt(text, "Lam ngay le thi OT toi thieu bao nhieu?")

    assert "300%" in excerpt
    assert "Lam them ngay le" in excerpt
    assert "30%" not in excerpt
    assert "150%" not in excerpt
    assert "200%" not in excerpt


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


_SALARY_ROW_FIXTURE = (
    "Salary band reference\n"
    "Grade Roles Range\n"
    "Product Associate / Associate Analyst\n"
    "P2 14 - 22 trieu dong\n"
    "Product Specialist\n"
    "P3 23 - 35 trieu dong\n"
    "Platform Lead / Engineering Manager\n"
    "P5 44 - 72 trieu dong\n"
    "Regional Director\n"
    "P6 75 - 115 trieu dong\n"
)


def test_salary_band_rows_are_atomic_for_role_range_questions() -> None:
    associate = query_focused_excerpt(
        _SALARY_ROW_FIXTURE, "Product Associate salary band range bao nhieu?"
    )
    assert "Product Associate / Associate Analyst" in associate
    assert "P2 14 - 22 trieu dong" in associate
    assert "P3 23 - 35 trieu dong" not in associate
    manager = query_focused_excerpt(
        _SALARY_ROW_FIXTURE, "Engineering Manager salary range bao nhieu?"
    )
    assert "Platform Lead / Engineering Manager" in manager
    assert "P5 44 - 72 trieu dong" in manager
    lead = query_focused_excerpt(_SALARY_ROW_FIXTURE, "Platform Lead salary range bao nhieu?")
    assert "P5 44 - 72 trieu dong" in lead
    assert "P6 75 - 115 trieu dong" not in lead
    conversational = query_focused_excerpt(
        _SALARY_ROW_FIXTURE, "Platform Lead thi range luong bao nhieu?"
    )
    assert "Platform Lead / Engineering Manager" in conversational
    assert "P5 44 - 72 trieu dong" in conversational
    assert "Product Specialist" not in conversational


def test_salary_band_row_matching_rejects_or_matching_and_unsupported_roles() -> None:
    text = (
        "Salary band reference\nDelivery Lead\nD4 30 - 40 trieu dong\n"
        "Platform Lead\nP5 44 - 72 trieu dong"
    )
    excerpt = query_focused_excerpt(text, "Platform Lead salary range bao nhieu?")
    assert "Platform Lead" in excerpt
    assert "P5 44 - 72 trieu dong" in excerpt
    assert "Delivery Lead" not in excerpt
    unsupported_question = "Unsupported Consultant salary range bao nhieu?"
    indexes = selected_structural_line_indexes(
        text, unsupported_question, analyze_question(unsupported_question)
    )
    assert indexes == ()
    assert not _is_salary_band_request("What is the annual salary budget?")


def test_structural_excerpt_budgets_wrapped_priority_clause_before_source_order() -> None:
    filler = "\n".join(
        f"Earlier unrelated policy row {index} with enough detail to consume context space."
        for index in range(24)
    )
    text = (
        f"{filler}\n"
        "Employees may not disclose another employee's salary without authorization.\n"
        "The policy does not prohibit an employee from discussing their own salary when\n"
        "exercising a lawful right.\n"
        "Later unrelated payroll row."
    )

    excerpt = query_focused_excerpt(
        text,
        "May I discuss my own salary with a colleague?",
    )

    assert "does not prohibit" in excerpt
    assert "exercising a lawful right" in excerpt
    assert len(excerpt) <= 1400


def test_attendance_correction_excerpt_keeps_event_and_deadline_together() -> None:
    text = (
        "Ngoai le va dieu chinh cham cong\n"
        "Quen check-in hoac check-out nhung co bang chung hop ly ve viec lam viec.\n"
        "Su co he thong duoc IT xac nhan.\n"
        "Quy trinh yeu cau\n"
        "Nhan vien tao yeu cau dieu chinh tren HRM.\n"
        "Yeu cau nen duoc gui trong vong 04 ngay lam viec ke tu ngay phat sinh; "
        "truong hop dac biet phai giai trinh ly do gui muon."
    )

    excerpt = query_focused_excerpt(
        text,
        "Quen cham cong thi trong bao lau nen gui yeu cau chinh?",
    )

    assert "Quen check-in hoac check-out" in excerpt
    assert "04 ngay lam viec ke tu ngay phat sinh" in excerpt
    assert "Su co he thong" not in excerpt
    assert "truong hop dac biet" not in excerpt


def test_remote_attendance_excerpt_keeps_policy_scope_and_obligation() -> None:
    text = (
        "05 LAM VIEC TU XA VA HYBRID Dieu kien va lich dang ky\n"
        "So ngay remote thong thuong toi da 02 ngay/tuan.\n"
        "Dang ky lich truoc gio quy dinh.\n"
        "Giu nguyen thoi luong, gio cot loi va nghia vu cham cong\n"
        "Gio lam viec\n"
        "nhu khi lam tai van phong"
    )

    excerpt = query_focused_excerpt(
        text,
        "Toi lam o nha thi co can cham cong nhu di van phong khong?",
    )

    assert "LAM VIEC TU XA VA HYBRID" in excerpt
    assert "nghia vu cham cong" in excerpt
    assert "nhu khi lam tai van phong" in excerpt


def test_ordinary_annual_leave_excerpt_keeps_allocation_not_nearby_durations() -> None:
    text = (
        "02 NGHI HANG NAM - Phep nam, tham nien va su dung\n"
        "Cong viec trong dieu kien binh thuong 17 ngay lam viec/nam khi du 12 thang.\n"
        "Cu du 04 nam lam viec, tang them 02 ngay nghi hang nam.\n"
        "Dang ky nghi phep truoc it nhat 03 ngay lam viec."
    )

    excerpt = query_focused_excerpt(
        text,
        "Mot nam nhan vien binh thuong co bao nhieu ngay phep?",
    )

    assert "binh thuong 17 ngay lam viec/nam" in excerpt
    assert "tang them 02 ngay" not in excerpt
    assert "truoc it nhat 03 ngay" not in excerpt


def test_annual_leave_seniority_excerpt_keeps_duration_and_increment() -> None:
    text = (
        "02 NGHI HANG NAM - Phep nam, tham nien va su dung\n"
        "Cong viec trong dieu kien binh thuong 17 ngay lam viec/nam.\n"
        "Cu du 04 nam lam viec cho cong ty, tang them 02 ngay\n"
        "Tham nien\n"
        "nghi hang nam theo quy dinh.\n"
        "Dang ky truoc 03 ngay lam viec."
    )

    excerpt = query_focused_excerpt(
        text,
        "Toi lam o day du 4 nam roi thi duoc them ngay phep khong?",
    )

    assert "04 nam lam viec" in excerpt
    assert "tang them 02 ngay" in excerpt
    assert "nghi hang nam" in excerpt
    assert "17 ngay" not in excerpt
    assert "03 ngay" not in excerpt


def test_attendance_deadline_excerpt_keeps_value_after_interleaved_table_label() -> None:
    text = (
        "Nội dung Quy định\n"
        "Trước 16:00 của ngày làm việc liền trước hoặc theo lịch cố\n"
        "Đăng ký lịch\n"
        "định của bộ phận\n"
        "Giờ làm việc giữ nguyên thời lượng."
    )
    excerpt = query_focused_excerpt(
        text,
        "Muốn remote ngày mai thì hôm nay phải đăng ký trước mấy giờ?",
    )
    assert "lịch cố" in excerpt
    assert "định của bộ phận" in excerpt
