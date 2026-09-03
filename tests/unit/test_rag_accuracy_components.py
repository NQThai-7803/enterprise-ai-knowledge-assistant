from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from typing import Any
from uuid import UUID

from app.chat.context_builder import query_focused_excerpt
from app.citations.models import PromptSource, PromptSourceRegistry
from app.core.config import Settings
from app.models import CitationSourceType
from app.retrieval.evidence_quality import EvidenceContextKind, classify_evidence_context
from app.retrieval.models import HybridRetrievalHit
from app.retrieval.question_analysis import analyze_question, retrieval_query_variants
from app.retrieval.reranker import (
    HeuristicRetrievalReranker,
    SentenceTransformerCrossEncoderReranker,
)
from app.retrieval.reranker_factory import create_retrieval_reranker
from app.retrieval.structured import build_structured_records
from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    ClaimEvidenceValidationService,
)
from app.services.grounded_answer_service import (
    _claim_validation_should_reselect_citations,
    _numeric_answer_missing_source_unit,
    _question_focused_time_ranges_from_text,
    _rank_hits_for_prompt,
    _should_retry_incomplete_answer,
    _source_has_multi_value_duration_evidence,
    _structured_policy_clause_repair_generation,
    _structured_value_repair_generation,
)


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


def uid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def hit(value: int, text: str, *, title: str = "Policy") -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=uid(value),
        document_id=uid(1000 + value),
        document_title=title,
        chunk_index=value,
        text=text,
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=max(1, len(text.split())),
        hybrid_score=1.0 / (value + 1),
        semantic_score=0.7,
        semantic_rank=value + 1,
        keyword_score=None,
        keyword_rank=None,
        matched_by=("semantic",),
    )


def source(text: str, *, title: str = "Policy") -> PromptSourceRegistry:
    return PromptSourceRegistry(
        sources=(
            PromptSource(
                marker="[SOURCE_1]",
                source_type=CitationSourceType.INTERNAL,
                document_title=title,
                text=text,
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                hybrid_score=1.0,
                chunk_id=uid(1),
                document_id=uid(2),
            ),
        )
    )


def rerank(query: str, *hits: HybridRetrievalHit) -> tuple[HybridRetrievalHit, ...]:
    async def scenario() -> tuple[HybridRetrievalHit, ...]:
        return await HeuristicRetrievalReranker().rerank(query=query, hits=hits, top_k=len(hits))

    return run_async(scenario())


def test_question_analysis_detects_generic_answer_types() -> None:
    assert analyze_question("CTO Nova Digital la ai?").answer_type == "PERSON"
    assert analyze_question("Cong ty thanh lap nam nao?").answer_type == "YEAR"
    assert analyze_question("Co bao nhieu nhan su?").answer_type == "COUNT"


def test_remote_may_ngay_is_a_duration_request() -> None:
    analysis = analyze_question("Lam hybrid thi moi tuan duoc o nha may ngay?")

    assert analysis.asks_for_duration is True
    assert analysis.answer_type == "DURATION"


def test_salary_ngay_may_is_a_date_request() -> None:
    analysis = analyze_question("Ngay tra luong cua Nova Digital la ngay may?")

    assert analysis.answer_type == "DATE"
    assert analysis.asks_for_explicit_value is True


def test_remote_duration_repair_uses_remote_days_value() -> None:
    generation = _structured_value_repair_generation(
        question="Lam hybrid thi moi tuan duoc o nha may ngay?",
        source_registry=source(
            "So ngay remote thong thuong Toi da 02 ngay/tuan, tuy vi tri va phe duyet cua quan ly."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "02 ngay/tuan" in payload["answer"]


def test_temporal_moi_does_not_strip_specific_value_field_from_excerpt() -> None:
    excerpt = query_focused_excerpt(
        (
            "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh\n"
            "Noi tru 150 trieu dong/nam\n"
            "Ngoai tru 12 trieu dong/nam"
        ),
        "Bao hiem NovaCare chi tra noi tru toi da bao nhieu moi nam?",
    )

    assert "Noi tru" in excerpt


def test_claim_validation_accepts_remote_duration_when_label_precedes_excerpt() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Remote toi da may ngay moi tuan?",
            answer="Thoi luong la 02 ngay/tuan.",
            source_registry=source(
                "02 ngay/tuan, tuy vi tri va phe duyet.\nDieu kien khong phu hop de remote."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_structured_person_repair_uses_role_bound_name() -> None:
    generation = _structured_value_repair_generation(
        question="Ai la CEO cua Nova Digital?",
        source_registry=source(
            "Nguyen Anh Khoa - chiu trach nhiem dieu hanh\n"
            "Tong Giam doc (CEO) chung\n"
            "Le Thu Ha - phu trach ky thuat\n"
            "Giam doc Cong nghe (CTO)",
            title="Nova Digital Policy",
        ),
    )

    assert generation is not None
    assert "Nguyen Anh Khoa" in generation.content


def test_structured_grouped_duration_repair_preserves_all_policy_categories() -> None:
    generation = _structured_value_repair_generation(
        question="So ngay nghi hang nam theo nhom cong viec la bao nhieu?",
        source_registry=source(
            "Cong viec trong dieu kien binh thuong 12 ngay lam viec/nam.\n"
            "Nguoi chua thanh nien, nguoi khuyet tat hoac cong viec nang nhoc, "
            "doc hai, nguy hiem\n"
            "14 ngay\n"
            "16 ngay Cong viec dac biet nang nhoc, doc hai, nguy hiem."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert all(value in payload["answer"] for value in ("12", "14", "16"))


def test_structured_grouped_duration_repair_accepts_plain_annual_leave_wording() -> None:
    generation = _structured_value_repair_generation(
        question="Nhan vien Nova Digital co bao nhieu ngay phep nam?",
        source_registry=source(
            "Cong viec trong dieu kien binh thuong 12 ngay lam viec/nam.\n"
            "Nguoi chua thanh nien, nguoi khuyet tat hoac cong viec nang nhoc, "
            "doc hai, nguy hiem\n"
            "14 ngay\n"
            "16 ngay Cong viec dac biet nang nhoc, doc hai, nguy hiem."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert all(value in payload["answer"] for value in ("12", "14", "16"))


def test_structured_grouped_duration_repair_handles_value_then_condition_wrap() -> None:
    generation = _structured_value_repair_generation(
        question="Nhan vien Nova Digital co bao nhieu ngay phep nam?",
        source_registry=source(
            "Muc nghi Doi tuong ap dung\n"
            "12 ngay\n"
            "Cong viec trong dieu kien binh thuong\n"
            "14 ngay\n"
            "Nguoi chua thanh nien hoac cong viec nang nhoc, doc hai\n"
            "16 ngay\n"
            "Cong viec dac biet nang nhoc, doc hai, nguy hiem"
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert all(value in payload["answer"] for value in ("12", "14", "16"))


def test_specific_value_validation_prefers_field_over_generic_heading() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Muc ho tro an trua hien tai la bao nhieu?",
            answer="Gia tri la 900.000 dong/thang.",
            source_registry=source(
                "Phu cap va ho tro hang 04 thang\n"
                "An trua 900.000 dong/thang\n"
                "Dien thoai 300.000 - 800.000 dong/thang"
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_remote_days_claim_rejects_unrelated_weekly_rest_value() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Lam hybrid thi moi tuan duoc o nha may ngay?",
            answer="Moi tuan duoc nghi it nhat 24 gio lien tuc.",
            source_registry=source("Moi tuan duoc nghi it nhat 24 gio lien tuc."),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_remote_days_claim_accepts_equivalent_remote_topic_wording() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Lam hybrid thi moi tuan duoc o nha may ngay?",
            answer="Toi da 02 ngay/tuan.",
            source_registry=source(
                "So ngay remote thong thuong Toi da 02 ngay/tuan, tuy vi tri va phe duyet."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_security_control_claim_accepts_a_concrete_shared_control() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Khi lam o nha phai bao dam an toan gi?",
            answer="Phai su dung thiet bi duoc phe duyet va VPN/MFA khi ap dung.",
            source_registry=source(
                "An toan thong tin: Su dung thiet bi duoc phe duyet, VPN/MFA khi ap dung."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())
    assert analyze_question("Gio cot loi la may gio?").answer_type == "TIME_RANGE"


def test_question_analysis_treats_ot_rate_wording_as_percentage_request() -> None:
    analysis = analyze_question("Nhân viên on-call làm Chủ nhật thì mức OT thế nào?")

    assert analysis.answer_type == "PERCENTAGE"
    assert analysis.asks_for_percentage is True
    assert analyze_question("Dong bao nhieu phan tram?").answer_type == "PERCENTAGE"
    assert analyze_question("Neu on-call thi OT bao nhieu?").answer_type == "PERCENTAGE"
    assert analyze_question("Co tu dong tinh lam them gio khong?").answer_type == "YES_NO"


def test_retrieval_query_variants_preserve_original_and_negation() -> None:
    variants = retrieval_query_variants("  phu cap an trua bn vay, khong?  ")

    assert variants.original == "phu cap an trua bn vay, khong?"
    assert "bao nhieu" in variants.diacritic_insensitive
    assert "khong" in variants.diacritic_insensitive
    assert variants.original != variants.diacritic_insensitive


def test_retrieval_query_variants_canonicalize_conversational_security_request() -> None:
    compliance = retrieval_query_variants(
        "Nhan vien hybrid can tuan thu bao mat nao khi lam o nha?"
    )
    safety = retrieval_query_variants("Lam hybrid thi phai bao dam an toan gi?")

    assert compliance.original.startswith("Nhan vien hybrid can tuan thu")
    assert compliance.normalized == "lam viec tu xa yeu cau bao mat"
    assert compliance.diacritic_insensitive == "lam viec tu xa yeu cau bao mat"
    assert safety.normalized == "lam viec tu xa yeu cau bao mat"


def test_retrieval_query_variants_canonicalize_inpatient_conversation_phrase() -> None:
    variants = retrieval_query_variants("Neu toi nam vien thi NovaCare toi da bao nhieu mot nam?")

    assert "noi tru" in variants.diacritic_insensitive
    assert "nam vien" not in variants.diacritic_insensitive
    assert (
        analyze_question("Neu toi nam vien thi NovaCare toi da bao nhieu mot nam?").answer_type
        == "AMOUNT"
    )


def test_question_analysis_distinguishes_percentage_amount_and_duration() -> None:
    percentage = analyze_question("Cong ty dong BHXH bao nhieu phan tram?")
    amount = analyze_question("Tien an trua duoc ho tro bao nhieu moi thang?")
    inpatient_amount = analyze_question("Bao hiem noi tru toi da bao nhieu mot nam?")
    night_percentage = analyze_question("Lam viec ban dem duoc cong them bao nhieu?")
    duration = analyze_question("Hybrid duoc remote toi da bao nhieu ngay moi tuan?")

    assert percentage.answer_type == "PERCENTAGE"
    assert percentage.asks_for_percentage is True
    assert percentage.asks_for_amount is False
    assert amount.answer_type == "AMOUNT"
    assert amount.asks_for_amount is True
    assert amount.asks_for_duration is False
    assert inpatient_amount.answer_type == "AMOUNT"
    assert inpatient_amount.asks_for_amount is True
    assert inpatient_amount.asks_for_duration is False
    assert night_percentage.answer_type == "PERCENTAGE"
    assert night_percentage.asks_for_percentage is True
    assert duration.answer_type == "DURATION"
    assert duration.asks_for_duration is True


def test_structured_records_keep_row_value_and_condition_together() -> None:
    records = build_structured_records(
        "Allowances\nLunch | 730000 dong | Full-time employees\nRemote | 500000 dong | Approved WFH"
    )

    lunch = next(record for record in records if record.row_label == "Lunch")
    remote = next(record for record in records if record.row_label == "Remote")
    assert lunch.row_value == "730000 dong"
    assert lunch.row_condition == "Full-time employees"
    assert remote.row_value == "500000 dong"
    assert remote.row_condition == "Approved WFH"


def test_question_analysis_treats_paid_leave_days_as_duration_not_amount() -> None:
    paid_leave = analyze_question("Nhan vien ket hon duoc nghi huong luong bao nhieu ngay?")

    assert paid_leave.answer_type == "DURATION"
    assert paid_leave.asks_for_duration is True
    assert paid_leave.asks_for_amount is False


def test_rag_accuracy_settings_defaults_and_constraints() -> None:
    settings = Settings(_env_file=None)

    assert settings.reranker_enabled is True
    assert settings.reranker_provider == "sentence_transformers"
    assert settings.reranker_model == "BAAI/bge-reranker-v2-m3"
    assert settings.reranker_local_files_only is True
    assert settings.reranker_candidate_k == 50
    assert settings.reranker_top_k == 6
    assert settings.claim_validation_enabled is True
    assert settings.rag_diagnostics_enabled is False


def test_person_role_candidate_outranks_topical_non_answer_candidate() -> None:
    direct = hit(1, "Leadership\nLe Thu Ha - Giam doc Cong nghe (CTO)")
    topical = hit(0, "AI and Data teams operate NovaAssist technology platforms.")

    ranked = rerank("CTO Nova Digital la ai?", topical, direct)

    assert ranked[0].chunk_id == direct.chunk_id
    assert ranked[0].reranker_score is not None


def test_person_role_candidate_ignores_committee_name_false_positive() -> None:
    direct = hit(
        1, "Le Thu Ha - accountable for technology platforms\nChief Technology Officer (CTO)"
    )
    committee = hit(
        0,
        "Hoi dong Kien truc Cong nghe\nCTO chairs architecture governance decisions.",
    )

    ranked = rerank("CTO Nova Digital la ai?", committee, direct)

    assert ranked[0].chunk_id == direct.chunk_id


def test_year_count_amount_percentage_and_yes_no_alignment() -> None:
    assert (
        rerank(
            "Cong ty duoc thanh lap nam nao?",
            hit(0, "Company overview and mission."),
            hit(1, "Profile\nFounded year: 2021"),
        )[0].chunk_index
        == 1
    )
    assert (
        rerank(
            "Cong ty co khoang bao nhieu nhan su?",
            hit(0, "Hiring policy for employees."),
            hit(1, "Profile\nHeadcount: about 120 employees"),
        )[0].chunk_index
        == 1
    )
    assert (
        rerank(
            "Phu cap an trua la bao nhieu?",
            hit(0, "Allowance principles."),
            hit(1, "Allowance | Lunch allowance | 730000 dong per month"),
        )[0].chunk_index
        == 1
    )
    assert (
        rerank(
            "Lam them ngay nghi hang tuan duoc tra toi thieu bao nhieu?",
            hit(0, "Overtime approval workflow."),
            hit(1, "Weekly rest day overtime: at least 200%"),
        )[0].chunk_index
        == 1
    )
    assert (
        rerank(
            "On-call co tu dong duoc tinh toan bo la lam them gio khong?",
            hit(0, "On-call scheduling."),
            hit(1, "On-call time does not automatically count fully as overtime."),
        )[0].chunk_index
        == 1
    )


def test_structural_excerpt_prioritizes_scored_value_rows_past_toc() -> None:
    text = "\n".join(
        (
            "doanh nghiep 3",
            "2 Tam nhin, su menh, gia tri cot loi va van hoa 4",
            "3 San pham, dich vu va khach hang muc tieu 5",
            "4 Mo hinh co cau to chuc 6",
            "5 Chuc nang cac don vi chuyen mon 7-8",
            "6 Co che quan tri, phoi hop va dau moi lien he 9",
            "A Phu luc tra cuu, tai lieu lien quan va lich su sua doi 10",
            "ND-CORP-001 | Trang 2",
            "NOVA DIGITAL TECHNOLOGY JSC TAI LIEU NOI BO",
            "01 HO SO TONG QUAN DOANH NGHIEP",
            "Mot cong ty cong nghe Viet Nam",
            "Thong tin nhan dien",
            "Ten tieng Viet Cong ty Co phan Cong nghe Nova Digital",
            "Ten tieng Anh Nova Digital Technology Joint Stock Company",
            "Ten viet tat NOVA DIGITAL",
            "Loai hinh Cong ty co phan cong nghe",
            "Nam thanh lap 2021",
            "Tang 8, Toa nha Nova Hub",
            "Tru so chinh",
            "Thanh pho Ho Chi Minh",
            "Van phong Thanh pho Ho Chi Minh, Ha Noi va Da Nang",
            "Khoang 180 nguoi; 60% thuoc khoi ky thuat, du lieu va an toan thong tin",
            "Quy mo nhan su",
        )
    )

    excerpt = query_focused_excerpt(text, "Nova Digital co khoang bao nhieu nhan su?")

    assert "Khoang 180 nguoi" in excerpt
    assert "Quy mo nhan su" in excerpt


def test_time_range_and_duration_excerpt_preserve_values_and_rows() -> None:
    time_text = (
        "Working schedule\n"
        "Flexible start time: employees may start between 08:00-09:30\n"
        "Core hours morning: 09:30-11:30\n"
        "Core hours afternoon: 13:30-16:30\n"
    )
    deadline_text = (
        "Timesheet correction\n"
        "Forgot check-out: employee must submit a correction request within 03 working days.\n"
        "Manager reviews the request.\n"
    )

    time_excerpt = query_focused_excerpt(time_text, "Gio cot loi la may gio?")
    deadline_excerpt = query_focused_excerpt(
        deadline_text,
        "Neu quen check-out thi phai gui yeu cau dieu chinh trong bao lau?",
    )

    assert "09:30-11:30" in time_excerpt
    assert "13:30-16:30" in time_excerpt
    assert "Forgot check-out" in deadline_excerpt
    assert "03 working days" in deadline_excerpt


def test_prompt_ranking_prefers_direct_limit_rule_over_scenario_question() -> None:
    scenario = hit(
        0,
        "Tinh huong mau va cau hoi kiem thu RAG\n"
        "Nhan vien remote khan cap va gui yeu cau dieu chinh trong 03 ngay lam viec.\n"
        "Nhan vien hybrid duoc remote toi da bao nhieu ngay moi tuan?",
    )
    direct = hit(
        1,
        "Che do hybrid/remote\n"
        "So ngay remote toi da: 02 ngay/tuan, tuy vi tri va phe duyet cua quan ly.",
    )

    ranked = _rank_hits_for_prompt(
        (scenario, direct),
        question="Nhan vien hybrid duoc remote toi da bao nhieu ngay moi tuan?",
    )

    assert ranked[0].chunk_id == direct.chunk_id


def test_prompt_ranking_prefers_remote_days_over_weekly_rest_value() -> None:
    weekly_rest = hit(
        0,
        "Nghi hang nam huong nguyen luong. Muc nghi Doi tuong ap dung. "
        "12 ngay Cong viec trong dieu kien binh thuong. "
        "14 ngay Cong viec nang nhoc, doc hai. "
        "16 ngay Cong viec dac biet nang nhoc, doc hai. "
        "Moi tuan duoc nghi it nhat 24 gio lien tuc.",
    )
    remote_days = hit(
        1,
        "Che do hybrid/remote. So ngay remote thong thuong toi da 02 ngay/tuan.",
    )

    ranked = _rank_hits_for_prompt(
        (weekly_rest, remote_days),
        question="Hay tom tat: so ngay remote moi tuan",
    )

    assert ranked[0].chunk_id == remote_days.chunk_id


def test_prompt_ranking_excludes_numeric_expected_answer_scenario() -> None:
    scenario = hit(
        2,
        "Tinh huong va cau hoi kiem thu RAG. Ky vong cau tra loi: "
        "NovaCare co han muc noi tru 150 trieu dong.",
        title="Chinh sach bao hiem va phuc loi",
    )
    direct = hit(
        3,
        "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh. "
        "Noi tru 150 trieu dong. Nhan vien chinh thuc sau khi hoan thanh thu viec.",
        title="Chinh sach bao hiem va phuc loi",
    )

    ranked = _rank_hits_for_prompt(
        (scenario, direct),
        question="han muc noi tru NovaCare moi nam",
    )

    assert [item.chunk_id for item in ranked] == [direct.chunk_id]


def test_prompt_ranking_prefers_founding_year_over_planning_year() -> None:
    planning = hit(
        0,
        "Tam nhin\nDen nam 2030 tro thanh doanh nghiep cong nghe duoc tin cay.",
        title="Gioi thieu Nova Digital",
    )
    direct = hit(
        1,
        "Thong tin nhan dien\nNam thanh lap 2021\nQuy mo nhan su khoang 180 nguoi.",
        title="Gioi thieu Nova Digital",
    )

    ranked = _rank_hits_for_prompt(
        (planning, direct),
        question="Nova Digital duoc thanh lap nam nao?",
    )

    assert ranked[0].chunk_id == direct.chunk_id


def test_prompt_ranking_prefers_explicit_named_policy_title() -> None:
    related_policy = hit(
        0,
        "Nhan vien linh hoat co the bat dau 08:00-09:30.",
        title="Noi quy lao dong Cong ty Cong nghe Nova Digital",
    )
    named_policy = hit(
        1,
        "Khung bat dau linh hoat 08:00 - 09:00\nKhung ket thuc tuong ung 17:00 - 18:00",
        title="Chinh sach lam viec va cham cong Cong ty Cong nghe Nova Digital",
    )

    ranked = _rank_hits_for_prompt(
        (related_policy, named_policy),
        question=(
            "Theo chinh sach lam viec va cham cong, nhan vien co the "
            "bat dau lam viec linh hoat trong khoang nao?"
        ),
    )

    assert ranked[0].chunk_id == named_policy.chunk_id
    assert related_policy.chunk_id not in {hit.chunk_id for hit in ranked[:1]}


def test_prompt_ranking_prefers_direct_non_automatic_rule_over_question_list() -> None:
    question_list = hit(
        0,
        "Tinh huong mau va cau hoi kiem thu RAG\n"
        "Ky su on-call xu ly incident va chuyen quan ly phe duyet.\n"
        "Lam on-call co tu dong duoc tinh toan bo la lam them gio khong?",
    )
    direct = hit(
        1,
        "Ca truc, on-call va lam them gio\n"
        "On-call khong tu dong duoc coi la thoi gian lam them; "
        "thoi gian thuc te xu ly su co phai duoc ghi nhan.",
    )

    ranked = _rank_hits_for_prompt(
        (question_list, direct),
        question="On-call co tu dong duoc tinh toan bo la lam them gio khong?",
    )

    assert ranked[0].chunk_id == direct.chunk_id


def test_quality_gate_accepts_cited_founding_year_answer() -> None:
    assert not _should_retry_incomplete_answer(
        question="Nova Digital duoc thanh lap nam nao?",
        answer="Nova Digital duoc thanh lap vao nam 2021. [1]",
        source_registry=source("Nam thanh lap 2021\nTang 8, Toa nha Nova Hub"),
    )


def test_quality_gate_accepts_cited_time_range_answer() -> None:
    assert not _should_retry_incomplete_answer(
        question=(
            "Theo chinh sach lam viec va cham cong, nhan vien co the "
            "bat dau lam viec linh hoat trong khoang nao?"
        ),
        answer="Nhan vien co the bat dau linh hoat tu 08:00 - 09:00. [1]",
        source_registry=source(
            "Khung bat dau linh hoat 08:00 - 09:00\n"
            "Tong thoi gian lam viec 08 gio/ngay; 40 gio/tuan"
        ),
    )


def test_quality_gate_retries_time_range_answer_missing_requested_range() -> None:
    assert _should_retry_incomplete_answer(
        question=(
            "Theo chinh sach lam viec va cham cong, nhan vien co the "
            "bat dau lam viec linh hoat trong khoang nao?"
        ),
        answer="Ngay lam viec Thu Hai - Thu Sau. [1]",
        source_registry=source(
            "Ngay lam viec Thu Hai - Thu Sau\n"
            "Khung bat dau linh hoat 08:00 - 09:00\n"
            "Khung ket thuc tuong ung 17:00 - 18:00"
        ),
    )


def test_source_explicit_not_specified_is_supported_explanation() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            answer="Tai lieu khong quy dinh mot ty le co dinh.",
            source_registry=source(
                "This policy does not specify a fixed insurance percentage; "
                "the value follows current law and payroll configuration."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_negation_contradiction_is_detected() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            answer="Nhan vien khong can gui yeu cau dieu chinh trong 03 ngay lam viec.",
            source_registry=source(
                "If an employee forgets check-out, the employee must submit a "
                "correction request within 03 working days."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.CONTRADICTED

    run_async(scenario())


class FakeCrossEncoderModel:
    instance_count = 0

    def __init__(self, model_name: str, **kwargs: object) -> None:
        self.model_name = model_name
        self.kwargs = kwargs
        FakeCrossEncoderModel.instance_count += 1

    def predict(
        self,
        pairs: list[list[str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[float]:
        assert batch_size == 2
        assert show_progress_bar is False
        assert all(pair[0] == "unmatched query" for pair in pairs)
        return [0.1, 0.9]


def failing_model_loader(model_name: str, **kwargs: object) -> object:
    raise RuntimeError("model unavailable")


def test_sentence_transformer_reranker_uses_model_scores_and_reuses_model() -> None:
    async def scenario() -> None:
        FakeCrossEncoderModel.instance_count = 0
        reranker = SentenceTransformerCrossEncoderReranker(
            model_name="local-reranker",
            model_revision="",
            device="cpu",
            batch_size=2,
            max_length=128,
            timeout_seconds=5.0,
            local_files_only=True,
            cache_folder="./data/models",
            model_loader=FakeCrossEncoderModel,
        )

        first = await reranker.rerank(
            query="unmatched query",
            hits=(hit(0, "first candidate"), hit(1, "second candidate")),
            top_k=1,
        )
        second = await reranker.rerank(
            query="unmatched query",
            hits=(hit(0, "first candidate"), hit(1, "second candidate")),
            top_k=1,
        )

        assert first[0].chunk_index == 1
        assert second[0].chunk_index == 1
        assert FakeCrossEncoderModel.instance_count == 1

    run_async(scenario())


def test_sentence_transformer_reranker_falls_back_to_alignment_on_model_failure() -> None:
    async def scenario() -> None:
        reranker = SentenceTransformerCrossEncoderReranker(
            model_name="missing-local-reranker",
            model_revision="",
            device="cpu",
            batch_size=2,
            max_length=128,
            timeout_seconds=5.0,
            local_files_only=True,
            cache_folder="./data/models",
            model_loader=failing_model_loader,
        )
        ranked = await reranker.rerank(
            query="CTO Nova Digital la ai?",
            hits=(
                hit(0, "Technology platform planning."),
                hit(1, "Le Thu Ha - Chief Technology Officer (CTO)."),
            ),
            top_k=2,
        )

        assert ranked[0].chunk_index == 1
        assert ranked[0].reranker_score is not None

    run_async(scenario())


def test_reranker_factory_cache_respects_timeout_setting() -> None:
    first_settings = Settings(
        _env_file=None,
        reranker_provider="heuristic",
        reranker_timeout_seconds=3.0,
    )
    second_settings = Settings(
        _env_file=None,
        reranker_provider="heuristic",
        reranker_timeout_seconds=4.0,
    )

    assert create_retrieval_reranker(first_settings) is create_retrieval_reranker(first_settings)
    assert create_retrieval_reranker(first_settings) is not create_retrieval_reranker(
        second_settings
    )


def test_time_range_excerpt_preserves_en_dash_ranges() -> None:
    text = (
        "Working schedule\n"
        "Core hours morning: 09:30\u201311:30\n"
        "Core hours afternoon: 13:30\u201316:30\n"
    )

    excerpt = query_focused_excerpt(text, "Gio cot loi la may gio?")

    assert "09:30\u201311:30" in excerpt
    assert "13:30\u201316:30" in excerpt


def test_structured_time_range_repair_selects_requested_row() -> None:
    text = (
        "Ngay lam viec Thu Hai - Thu Sau "
        "Tong thoi gian lam viec 08 gio/ngay; 40 gio/tuan "
        "Khung bat dau linh hoat 08:00 - 09:00 "
        "Khung ket thuc tuong ung 17:00 - 18:00 "
        "Gio cot loi 09:30 - 11:30 va 13:30 - 16:30"
    )

    assert _question_focused_time_ranges_from_text(
        question=(
            "Theo chinh sach lam viec va cham cong, nhan vien co the "
            "bat dau lam viec linh hoat trong khoang nao?"
        ),
        source_text=text,
    ) == ("08:00 - 09:00",)

    assert _question_focused_time_ranges_from_text(
        question="Gio cot loi cua Nova Digital la may gio?",
        source_text=text,
    ) == ("09:30 - 11:30", "13:30 - 16:30")


def test_numeric_unit_guard_accepts_equivalent_currency_units() -> None:
    assert not _numeric_answer_missing_source_unit(
        answer="Phu cap an trua la 900.000 d/thang. [1]",
        source_registry=source("Phu cap an trua 900.000 dong/thang."),
    )


def test_structured_value_repair_selects_focused_amount_with_period_unit() -> None:
    generation = _structured_value_repair_generation(
        question="Phu cap an trua la bao nhieu?",
        source_registry=source(
            "Phu cap internet 300.000 d/thang\n"
            "Phu cap an trua 900.000 d/thang\n"
            "Phu cap remote 500.000 d/thang"
        ),
    )
    assert generation is not None
    payload = json.loads(generation.content)
    assert "900.000 d/thang" in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]
    bleed_generation = _structured_value_repair_generation(
        question="Phu cap an trua la bao nhieu?",
        source_registry=source(
            "An trua, kham suc khoe, thiet bi, hoat dong noi bo.\n"
            "Dai Base Salary tham khao (gross/thang).\n"
            "N1 Entry-level / Support / Junior QA 8 - 14 trieu dong.\n"
            "Bang phu cap mo phong.\n"
            "An trua 900.000 d/thang."
        ),
    )
    assert bleed_generation is not None
    bleed_payload = json.loads(bleed_generation.content)
    assert "900.000 d/thang" in bleed_payload["answer"]
    support_generation = _structured_value_repair_generation(
        question="Tien an trua duoc ho tro bao nhieu moi thang?",
        source_registry=source(
            "Tien luong toi thieu 500 dong/gio.\n"
            "Chinh sach tien luong can cap nhat theo van ban moi.\n"
            "Bang phu cap mo phong.\n"
            "An trua 900.\n- 000 d/thang."
        ),
    )
    assert support_generation is not None
    support_payload = json.loads(support_generation.content)
    assert "900.000 d/thang" in support_payload["answer"]


def test_claim_validation_supports_ocr_split_amount_group() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Tien an trua duoc ho tro bao nhieu moi thang?",
            answer="Gia tri la 900.000 d/thang.",
            source_registry=source("An trua 900.\n- 000 d/thang."),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_claim_validation_rejects_nearby_fact_for_wrong_requested_field() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Nhan vien hybrid co yeu cau bao mat gi?",
            answer=("Nhan vien hybrid phai bao dam thoi luong, lich hop va dau ra khi lam viec."),
            source_registry=source(
                "Nhan vien hybrid phai bao dam thoi luong, lich hop va dau ra khi lam viec. "
                "Yeu cau bao mat: lam viec tai dia diem phu hop va co ket noi an toan."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_claim_validation_accepts_answer_clause_under_matching_attribute_header() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Nhan vien hybrid co yeu cau bao mat gi?",
            answer="Phai lam tai dia diem phu hop va co ket noi an toan.",
            source_registry=source(
                "Yeu cau bao mat\nPhai lam tai dia diem phu hop va co ket noi an toan."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_claim_validation_rejects_reversed_passive_action_polarity() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Thoi gian xu ly su co on-call duoc ghi nhan the nao?",
            answer="Thoi gian xu ly su co khong duoc ghi nhan de danh gia OT.",
            source_registry=source(
                "Thoi gian thuc te xu ly ticket/su co duoc ghi nhan rieng de danh gia OT."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.CONTRADICTED

    run_async(scenario())


def test_claim_validation_requires_matching_numeric_policy_condition() -> None:
    evidence = (
        "Lam them ngay nghi hang tuan: it nhat 200%.\n"
        "It nhat 300%, chua bao gom tien luong ngay le.\n"
        "Lam them ngay le, Tet, ngay nghi co huong luong."
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        supported = await service.validate(
            question="Lam them vao Chu nhat thi muc OT the nao?",
            answer="It nhat 200%.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        wrong_condition = await service.validate(
            question="Lam them vao Chu nhat thi muc OT the nao?",
            answer="It nhat 300%.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert supported.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_condition.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_structured_repair_keeps_requested_condition_bound_to_preceding_outcome() -> None:
    generation = _structured_value_repair_generation(
        question="Ngay phep nam neu chua du 12 thang thi sao?",
        source_registry=source(
            "12 ngay lam viec/nam khi du 12 thang lam viec.\n"
            "Tinh theo ty le tuong ung voi thoi gian lam viec theo quy\n"
            "Nguoi lao dong chua du 12 thang\n"
            "dinh phap luat.\n"
            "Cu du 05 nam lam viec, tang them 01 ngay\n"
            "Tham nien nghi hang nam."
        ),
    )

    assert generation is not None
    answer = json.loads(generation.content)["answer"].casefold()
    assert "ty le tuong ung" in answer
    assert "chua du 12 thang" in answer
    assert "05 nam" not in answer
    assert "01 ngay" not in answer


def test_structured_repair_copies_named_policy_topic_clause_without_inventing_counts() -> None:
    generation = _structured_value_repair_generation(
        question="salary review được quy định như thế nào?",
        source_registry=source(
            "Việc tham gia salary review không tạo quyền đương nhiên được tăng lương.\n"
            "Chu kỳ salary review gồm đánh giá hiệu suất và phê duyệt ngân sách."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["citations"] == ["SOURCE_1"]
    assert "salary review" in payload["answer"].casefold()
    assert "3 giai đoạn" not in payload["answer"].casefold()


def test_claim_validation_prefers_complete_verbatim_clause_over_chunk_wide_polarity() -> None:
    answer = (
        "Participation in the review does not guarantee an adjustment. "
        "The documented legal minimum still applies."
    )

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="How is the compensation review defined?",
            answer=answer,
            source_registry=source(
                "An unrelated promotion may automatically change compensation.\n"
                f"{answer}\n"
                "Other benefits may be approved separately."
            ),
            cited_source_labels=("SOURCE_1",),
        )

        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_claim_validation_keeps_pay_date_bound_to_its_wrapped_label() -> None:
    evidence = (
        "Ky cong Tu ngay 01 den het ngay cuoi cung cua thang.\n"
        "Han quan ly xac nhan dieu chinh Ngay lam viec thu 4 cua thang ke tiep.\n"
        "Ngay 10 cua thang ke tiep; neu trung ngay nghi/le, Finance\n"
        "Ngay tra luong thuc hien vao ngay lam viec lien truoc."
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        supported = await service.validate(
            question="Luong thuong ve ngay nao?",
            answer="Ngay 10 cua thang ke tiep.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )
        wrong_field = await service.validate(
            question="Luong thuong ve ngay nao?",
            answer="Ngay lam viec thu 4 cua thang ke tiep.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )
        mixed_fields = await service.validate(
            question="Luong thuong ve ngay nao?",
            answer="Ngay 10 cua thang ke tiep, neu nghi thi vao ngay 1.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )

        assert supported.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_field.status == ClaimEvidenceStatus.INSUFFICIENT
        assert mixed_fields.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_claim_validation_requires_clock_range_for_time_range_question() -> None:
    async def scenario() -> None:
        evidence = (
            "Khung gio lam viec tieu chuan: 08:30 - 17:30. "
            "Chu ky xem xet chinh sach: 12 thang mot lan."
        )
        service = ClaimEvidenceValidationService()
        supported = await service.validate(
            question="Khung gio lam viec tieu chuan la khi nao?",
            answer="Tu 08:30 den 17:30.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )
        wrong_shape = await service.validate(
            question="Khung gio lam viec tieu chuan la khi nao?",
            answer="Khung gio duoc xem xet 12 thang mot lan.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )

        assert supported.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_shape.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_structured_value_repair_selects_focused_duration_date_and_percentage() -> None:
    duration_generation = _structured_value_repair_generation(
        question="Nhan vien ket hon duoc nghi huong luong bao nhieu ngay?",
        source_registry=source(
            "Ket hon cua nhan vien 2.000.000 d\n"
            "Nghi viec rieng huong luong\n"
            "Ket hon 03 ngay\n"
            "Con ket hon 01 ngay"
        ),
    )
    assert duration_generation is not None
    duration_payload = json.loads(duration_generation.content)
    assert "03 ngay" in duration_payload["answer"]

    date_generation = _structured_value_repair_generation(
        question="Nova Digital tra luong vao ngay nao?",
        source_registry=source(
            "Ky cong Tu ngay 01 den het ngay cuoi cung cua thang.\n"
            "Han quan ly xac nhan dieu chinh Ngay lam viec thu 4 cua thang ke tiep.\n"
            "Ngay 10 cua thang ke tiep; neu trung ngay nghi/le, Finance "
            "Ngay tra luong thuc hien vao ngay lam viec lien truoc."
        ),
    )
    assert date_generation is not None
    date_payload = json.loads(date_generation.content)
    assert "ngay 10 cua thang ke tiep" in date_payload["answer"]

    percentage_generation = _structured_value_repair_generation(
        question="Lam viec ban dem duoc tra them it nhat bao nhieu?",
        source_registry=source(
            "Lam them ngay nghi hang tuan It nhat 200%.\n"
            "Duoc tra them it nhat 30% tien luong tinh theo don gia/tien "
            "Lam viec ban dem luong gio cua ngay lam viec binh thuong.\n"
            "Ngoai tien OT va khoan 30% ban dem, con tra them it nhat 20% "
            "Lam them vao ban dem theo co so phap luat ap dung."
        ),
    )
    assert percentage_generation is not None
    percentage_payload = json.loads(percentage_generation.content)
    assert "30%" in percentage_payload["answer"]
    assert "20%" not in percentage_payload["answer"]


def test_structured_policy_clause_repair_copies_failed_claim_action_only() -> None:
    generation = _structured_policy_clause_repair_generation(
        question="Thoi gian xu ly su co on-call duoc ghi nhan the nao?",
        source_registry=source(
            "Phu cap on-call bu cho trang thai san sang theo lich; "
            "thoi gian thuc te xu ly ticket/su co duoc ghi nhan rieng de\n"
            "danh gia OT hoac che do khac theo chinh sach."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "thoi gian thuc te" in payload["answer"].casefold()
    assert "duoc ghi nhan rieng" in payload["answer"].casefold()
    assert "danh gia OT" in payload["answer"]
    assert "Phu cap on-call" not in payload["answer"]


def test_structured_policy_clause_repair_handles_table_action_word_order() -> None:
    generation = _structured_policy_clause_repair_generation(
        question="Thoi gian xu ly duoc ghi nhan ra sao?",
        source_registry=source(
            "On-call da duoc phan lich Ap dung lich truc da cong bo, "
            "ghi nhan thoi gian thuc te xu ly va che do lien quan."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "ghi nhan thoi gian thuc te" in payload["answer"].casefold()


def test_structured_policy_clause_repair_copies_oncall_allowance_meaning() -> None:
    generation = _structured_policy_clause_repair_generation(
        question="Voi ca on-call vao ngay nghi hang tuan, phu cap truc",
        source_registry=source(
            "3. On-call\n"
            "Phu cap on-call bu cho trang thai san sang theo lich; "
            "thoi gian thuc te xu ly ticket/su co duoc ghi nhan rieng."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "Phu cap on-call bu cho trang thai san sang theo lich" in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]

    async def scenario() -> None:
        validation = await ClaimEvidenceValidationService().validate(
            question="Voi ca on-call vao ngay nghi hang tuan, phu cap truc",
            answer=payload["answer"],
            source_registry=source(
                "3. On-call\n"
                "Phu cap on-call bu cho trang thai san sang theo lich; "
                "thoi gian thuc te xu ly ticket/su co duoc ghi nhan rieng."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert validation.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_security_requirement_needs_a_concrete_source_control() -> None:
    registry = source(
        "Lam viec tu xa duoc quan ly phe duyet theo vi tri va yeu cau bao mat.\n"
        "Nhan vien phai co ket noi an toan va khong de nguoi khong co tham quyen truy cap."
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        generic = await service.validate(
            question="Nhan vien hybrid co yeu cau bao mat gi?",
            answer="Phai duoc quan ly phe duyet theo vi tri va yeu cau bao mat.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        concrete = await service.validate(
            question="Nhan vien hybrid co yeu cau bao mat gi?",
            answer="Phai co ket noi an toan va khong de nguoi khong co tham quyen truy cap.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert generic.status == ClaimEvidenceStatus.INSUFFICIENT
        assert concrete.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_ascii_security_wording_needs_a_concrete_source_control() -> None:
    registry = source(
        "Lam viec tu xa toi da 02 ngay/tuan. "
        "Nhan vien phai co ket noi an toan va khong de nguoi khong co tham quyen truy cap."
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        for question in (
            "Nhan vien hybrid can tuan thu bao mat nao khi lam o nha?",
            "Lam hybrid thi phai bao dam an toan gi?",
        ):
            generic = await service.validate(
                question=question,
                answer="Nhan vien hybrid duoc lam o nha 02 ngay/tuan.",
                source_registry=registry,
                cited_source_labels=("SOURCE_1",),
                require_subject_attribute_alignment=True,
            )
            assert generic.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_structured_policy_clause_repair_copies_concrete_security_control() -> None:
    analysis = analyze_question("Nhan vien hybrid co yeu cau bao mat gi?")
    assert analysis.asks_for_explicit_value is False
    assert analysis.asks_for_person is False
    assert analysis.is_yes_no is False
    generation = _structured_policy_clause_repair_generation(
        question="Nhan vien hybrid co yeu cau bao mat gi?",
        source_registry=source(
            "Lam viec tu xa duoc quan ly phe duyet theo vi tri va yeu cau bao mat.\n"
            "Nhan vien phai co ket noi an toan va khong de nguoi khong co tham quyen truy cap."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "ket noi an toan" in payload["answer"].casefold()
    assert "khong co tham quyen" in payload["answer"].casefold()


def test_structured_value_repair_maps_sunday_to_weekly_rest_percentage() -> None:
    generation = _structured_value_repair_generation(
        question="Nhan vien on-call xu ly su co vao Chu nhat muc OT the nao?",
        source_registry=source(
            "Lam them ngay nghi hang tuan It nhat 200%.\n"
            "It nhat 300%, chua bao gom tien luong ngay le.\n"
            "Lam them ngay le, Tet, ngay nghi co huong luong."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "200%" in payload["answer"]


def test_structured_value_repair_handles_explicit_first_day_eligibility_table() -> None:
    generation = _structured_value_repair_generation(
        question="NovaCare co tu ngay dau khong?",
        source_registry=source(
            "Quyen loi Tu ngay nhan viec Sau thu viec Sau ngay nghi viec\n"
            "NovaCare Khong Co Ket thuc theo ngay hieu luc bao hiem"
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Không")
    assert "NovaCare" in payload["answer"]
    assert "sau thử việc" in payload["answer"]


def test_structured_value_repair_handles_from_hire_date_wording() -> None:
    generation = _structured_value_repair_generation(
        question="NovaCare co ngay tu luc nhan viec khong?",
        source_registry=source(
            "Quyen loi Tu ngay nhan viec Sau thu viec Sau ngay nghi viec\n"
            "NovaCare Khong Co\n"
            "Khong neu dang tam hoan"
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "NovaCare" in payload["answer"]
    assert "sau thử việc" in payload["answer"]


def test_structured_value_repair_handles_flattened_eligibility_condition() -> None:
    generation = _structured_value_repair_generation(
        question="NovaCare khi nao duoc tham gia?",
        source_registry=source(
            "2. NovaCare - bao hiem suc khoe bo sung\n"
            "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh\n"
            "Nhan vien chinh thuc sau khi hoan thanh\n"
            "Noi tru 150 trieu dong thu viec; theo danh sach bao hiem va\n"
            "dieu khoan loai tru."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "hoàn thành thử việc" in payload["answer"]
    assert "danh sách bảo hiểm" in payload["answer"]


def test_claim_validation_supports_eligibility_split_across_claim_packed_table() -> None:
    async def scenario() -> None:
        evidence = source(
            "Claim-focused evidence:\n"
            "CLAIM_1 evidence:\n"
            "2. NovaCare - bao hiem suc khoe bo sung\n"
            "Nhan vien chinh thuc sau khi hoan thanh\n"
            "CLAIM_2 evidence:\n"
            "HR dang ky nguoi lao dong thuoc dien tham gia.\n"
            "2. NovaCare - bao hiem suc khoe bo sung\n"
            "CLAIM_3 evidence:\n"
            "Nhan vien chinh thuc sau khi hoan thanh\n"
            "Noi tru 150 trieu dong thu viec; theo danh sach bao hiem va\n"
            "dieu khoan loai tru."
        )
        result = await ClaimEvidenceValidationService().validate(
            question="NovaCare khi nao duoc tham gia?",
            answer=(
                "NovaCare: dieu kien tham gia la nhan vien chinh thuc sau khi "
                "hoan thanh thu viec, theo danh sach bao hiem va dieu khoan loai tru."
            ),
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_eligibility_validation_requires_primary_employment_condition() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="NovaCare khi nao duoc tham gia?",
            answer="NovaCare tham gia khi du dieu kien va theo danh sach bao hiem.",
            source_registry=source(
                "NovaCare: nhan vien chinh thuc sau khi hoan thanh thu viec; "
                "theo danh sach bao hiem va dieu khoan loai tru."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert result.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_structured_value_repair_selects_short_inpatient_field_terms() -> None:
    generation = _structured_value_repair_generation(
        question="NovaCare noi tru toi da bao nhieu moi nam?",
        source_registry=source(
            "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh\n"
            "Nhan vien chinh thuc sau khi hoan thanh\n"
            "Noi tru 150 trieu dong thu viec; theo danh sach bao hiem va\n"
            "dieu khoan loai tru."
        ),
    )

    assert generation is not None


def test_inpatient_value_stays_bound_to_inpatient_row_in_flattened_excerpt() -> None:
    evidence = (
        "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh "
        "Noi tru 150 trieu dong thu viec; theo danh sach bao hiem va "
        "Toi da 1,2 trieu dong/lan; yeu cau chung tu hop le Ngoai tru 12 trieu dong."
    )
    generation = _structured_value_repair_generation(
        question="NovaCare noi tru toi da bao nhieu moi nam?",
        source_registry=source(evidence),
    )

    assert generation is not None
    assert "150 trieu dong" in json.loads(generation.content)["answer"]

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        correct = await service.validate(
            question="NovaCare noi tru toi da bao nhieu moi nam?",
            answer="Han muc noi tru la 150 trieu dong moi nam.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        wrong_field = await service.validate(
            question="NovaCare noi tru toi da bao nhieu moi nam?",
            answer="Han muc noi tru la 1,2 trieu dong moi lan.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert correct.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_field.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())
    payload = json.loads(generation.content)
    assert "150 trieu dong" in payload["answer"]


def test_inpatient_repair_prefers_requested_field_over_adjacent_benefit_value() -> None:
    registry = PromptSourceRegistry(
        sources=(
            PromptSource(
                marker="[SOURCE_1]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Benefits",
                text="Noi tru 150 trieu dong. Ngoai tru 1,2 trieu dong/lan.",
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                hybrid_score=1.0,
                chunk_id=uid(31),
                document_id=uid(32),
            ),
            PromptSource(
                marker="[SOURCE_2]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Benefits continuation",
                text="Tai nan ca nhan 200 trieu dong. Ten NovaCare duoc tao de kiem thu.",
                page_numbers=(2,),
                start_page=2,
                end_page=2,
                hybrid_score=1.0,
                chunk_id=uid(33),
                document_id=uid(32),
            ),
        )
    )

    generation = _structured_value_repair_generation(
        question="Han muc noi tru NovaCare moi nam la bao nhieu?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "150 trieu dong" in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]


def test_conversational_inpatient_wording_uses_canonical_field_for_repair() -> None:
    evidence = (
        "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh "
        "Noi tru 150 trieu dong thu viec; theo danh sach bao hiem va "
        "Toi da 1,2 trieu dong/lan; yeu cau chung tu hop le Ngoai tru 12 trieu dong."
    )
    question = "Neu toi nam vien thi NovaCare toi da bao nhieu mot nam?"
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(evidence),
    )

    assert generation is not None
    assert "150 trieu dong" in json.loads(generation.content)["answer"]

    async def scenario() -> None:
        validation = await ClaimEvidenceValidationService().validate(
            question=question,
            answer="Han muc noi tru la 150 trieu dong moi nam.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert validation.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_remote_stipend_repair_rejects_unrelated_monthly_support() -> None:
    registry = PromptSourceRegistry(
        sources=(
            PromptSource(
                marker="[SOURCE_1]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Salary and allowances",
                text="An trua 900.000 dong/thang. Hybrid stipend 500.000 dong/thang.",
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                hybrid_score=1.0,
                chunk_id=uid(21),
                document_id=uid(22),
            ),
            PromptSource(
                marker="[SOURCE_2]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Benefits",
                text="Ergonomic support 1.500.000 dong/24 thang.",
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                hybrid_score=1.0,
                chunk_id=uid(23),
                document_id=uid(24),
            ),
        )
    )

    generation = _structured_value_repair_generation(
        question="Khoan ho tro hang thang cho che do hybrid la bao nhieu?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "500.000 dong/thang" in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]

    async def scenario() -> None:
        correct = await ClaimEvidenceValidationService().validate(
            question="Khoan ho tro hang thang cho che do hybrid la bao nhieu?",
            answer="Khoan ho tro hybrid la 500.000 dong/thang.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        wrong_field = await ClaimEvidenceValidationService().validate(
            question="Khoan ho tro hang thang cho che do hybrid la bao nhieu?",
            answer="Khoan ho tro hybrid la 900.000 dong/thang.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert correct.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_field.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_question_analysis_treats_the_nao_as_manner_not_numeric_value() -> None:
    analysis = analyze_question("Thoi gian phat sinh xu ly the nao?")

    assert analysis.answer_type == "OTHER"
    assert analysis.asks_for_explicit_value is False


def test_question_analysis_treats_security_nao_as_policy_not_numeric_value() -> None:
    analysis = analyze_question("Nhan vien hybrid can tuan thu bao mat nao khi lam o nha?")

    assert analysis.answer_type != "NUMBER"
    assert analysis.asks_for_explicit_value is False


def test_question_analysis_classifies_compound_field_fragments() -> None:
    lunch = analyze_question("phu cap an trua moi thang")
    inpatient = analyze_question("han muc noi tru NovaCare moi nam")
    remote_days = analyze_question("so ngay remote moi tuan")
    eligibility = analyze_question("NovaCare khi nao duoc tham gia")

    assert lunch.answer_type == "AMOUNT"
    assert inpatient.answer_type == "AMOUNT"
    assert remote_days.answer_type == "DURATION"
    assert eligibility.answer_type == "POLICY_CONDITION"


def test_claim_focused_excerpt_keeps_values_for_compound_field_fragments() -> None:
    excerpt = query_focused_excerpt(
        (
            "2. NovaCare - bao hiem suc khoe bo sung\n"
            "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh\n"
            "Nhan vien chinh thuc sau khi hoan thanh\n"
            "Noi tru 150 trieu dong thu viec; theo danh sach bao hiem va\n"
            "dieu khoan loai tru."
        ),
        "Hay tom tat ba moc: so ngay remote moi tuan va phu cap an trua moi thang "
        "va han muc noi tru NovaCare moi nam.",
        information_needs=(
            "so ngay remote moi tuan",
            "phu cap an trua moi thang",
            "han muc noi tru NovaCare moi nam",
        ),
    )

    assert "150 trieu dong" in excerpt


def test_claim_validation_supports_leave_incident_policy_fields() -> None:
    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        leave = await service.validate(
            question=("Nhan vien dang nghi phep nhung phai ho tro su co thi quyen nghi"),
            answer=(
                "Quan ly kich hoat nguoi thay the truoc; chi lien he nhan vien nghi "
                "khi khong con phuong an hop ly va co su dong y."
            ),
            source_registry=source(
                "Nhan vien dang nghi phep nhung la dau moi duy nhat\n"
                "Quan ly kich hoat nguoi thay the truoc; chi lien he nhan vien "
                "nghi khi khong con phuong an hop ly va co su dong y."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        incident_time = await service.validate(
            question=(
                "Nhan vien dang nghi phep nhung phai ho tro su co thoi gian phat sinh xu ly the nao"
            ),
            answer=("Ap dung lich truc da cong bo, ghi nhan thoi gian thuc te xu ly."),
            source_registry=source(
                "On-call da duoc phan lich\n"
                "Ap dung lich truc da cong bo, ghi nhan thoi gian thuc te xu ly "
                "va che do lien quan."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert (leave.status, incident_time.status) == (
            ClaimEvidenceStatus.SUPPORTED,
            ClaimEvidenceStatus.SUPPORTED,
        )

    run_async(scenario())


def test_claim_validation_requires_policy_action_ordered_first() -> None:
    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        registry = source(
            "Nhan vien dang nghi phep nhung la dau moi duy nhat. "
            "Quan ly kich hoat nguoi thay the truoc; chi lien he nhan vien nghi "
            "khi khong con phuong an hop ly va co su dong y."
        )
        question = "Dang nghi phep ma production co su co thi quan ly phai lam gi truoc?"
        incomplete = await service.validate(
            question=question,
            answer="Quan ly can doi nhu cau nghi voi ke hoach cong viec.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        complete = await service.validate(
            question=question,
            answer="Quan ly kich hoat nguoi thay the truoc.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert incomplete.status == ClaimEvidenceStatus.INSUFFICIENT
        assert complete.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_structured_policy_clause_repair_copies_action_ordered_first() -> None:
    generation = _structured_policy_clause_repair_generation(
        question="Dang nghi phep ma production co su co thi quan ly phai lam gi truoc?",
        source_registry=source(
            "Nhan vien dang nghi phep nhung la dau moi duy nhat.\n"
            "Quan ly kich hoat nguoi thay the truoc; chi lien he nhan vien nghi "
            "khi khong con phuong an hop ly va co su dong y."
        ),
    )

    assert generation is not None
    assert "kich hoat nguoi thay the truoc" in generation.content.casefold()


def test_claim_validation_returns_insufficient_for_ungrounded_substantive_answer() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            answer="The payroll policy is flexible and generous for everyone.",
            source_registry=source(
                "Employees must submit timesheet corrections within 03 working days."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_negation_deadline_not_within_is_contradicted() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            answer="The employee is not required to submit the request within 03 working days.",
            source_registry=source(
                "The employee must submit the correction request within 03 working days."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.CONTRADICTED

    run_async(scenario())


def test_negation_allowed_not_allowed_and_may_not_are_contradicted() -> None:
    async def scenario() -> None:
        cases = (
            (
                "Employees may use flexible start time.",
                "Employees may not use flexible start time.",
            ),
            (
                "Employees are allowed to work remotely under the policy.",
                "Employees are not allowed to work remotely under the policy.",
            ),
            (
                "Employees are not allowed to skip attendance records.",
                "Employees are allowed to skip attendance records.",
            ),
            (
                "On-call time does not automatically count fully as overtime.",
                "On-call time automatically counts fully as overtime.",
            ),
        )
        for evidence, answer in cases:
            result = await ClaimEvidenceValidationService().validate(
                answer=answer,
                source_registry=source(evidence),
                cited_source_labels=("SOURCE_1",),
            )
            assert result.status == ClaimEvidenceStatus.CONTRADICTED

    run_async(scenario())


def sources(*texts: str) -> PromptSourceRegistry:
    return PromptSourceRegistry(
        sources=tuple(
            PromptSource(
                marker=f"[SOURCE_{index}]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Policy",
                text=text,
                page_numbers=(index,),
                start_page=index,
                end_page=index,
                hybrid_score=1.0,
                chunk_id=uid(2000 + index),
                document_id=uid(3000 + index),
            )
            for index, text in enumerate(texts, start=1)
        )
    )


def test_claim_validation_uses_self_clause_not_other_party_restriction() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        answer = "Co. Nguoi lao dong duoc trao doi thong tin luong cua chinh minh."
        question = "Nhan vien co duoc noi ve muc luong cua chinh minh khong?"

        other_only = await validator.validate(
            question=question,
            answer=answer,
            source_registry=source(
                "Nhan vien khong duoc truy cap, sao chep hoac phat tan "
                "du lieu luong cua nguoi khac neu khong co phe duyet."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert other_only.status == ClaimEvidenceStatus.INSUFFICIENT

        mixed = await validator.validate(
            question=question,
            answer=answer,
            source_registry=source(
                "Nhan vien khong duoc truy cap, sao chep hoac phat tan "
                "du lieu luong cua nguoi khac neu khong co phe duyet. "
                "Chinh sach khong cam nguoi lao dong su dung, trao doi "
                "hoac cung cap thong tin luong cua chinh minh khi thuc hien "
                "quyen hop phap."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert mixed.status == ClaimEvidenceStatus.SUPPORTED
        assert mixed.polarity == "YES"

    run_async(scenario())


def test_supporting_source_selection_prefers_policy_clause_over_sample_question() -> None:
    registry = sources(
        "B. Cau hoi mau\nNhan vien co duoc noi ve muc luong cua chinh minh khong?",
        "Chia se thong tin luong\n"
        "Chinh sach khong cam nguoi lao dong su dung, trao doi "
        "hoac cung cap thong tin luong cua chinh minh khi thuc hien "
        "quyen hop phap.",
    )

    labels = ClaimEvidenceValidationService().select_supporting_source_labels(
        question="Nhan vien co duoc noi ve muc luong cua chinh minh khong?",
        answer="Co. Nguoi lao dong duoc trao doi thong tin luong cua chinh minh.",
        source_registry=registry,
        preferred_source_labels=("SOURCE_1",),
        max_sources=2,
    )

    assert labels == ("SOURCE_2",)


def test_direct_fact_source_reselection_uses_answer_bearing_evidence() -> None:
    registry = sources(
        "Document control and purpose. This source identifies the organization only.",
        (
            "Executive team\n"
            "Le Thu Ha - phu trach ky thuat, kien truc va nen tang\n"
            "Giam doc Cong nghe (CTO)"
        ),
    )

    should_reselect = _claim_validation_should_reselect_citations(
        status=ClaimEvidenceStatus.INSUFFICIENT,
        question="Giam doc cong nghe cua Nova Digital la ai?",
        answer="Giam doc Cong nghe (CTO) cua Nova Digital la Le Thu Ha.",
        cited_source_labels=("SOURCE_1",),
        source_registry=registry,
    )
    labels = ClaimEvidenceValidationService().select_supporting_source_labels(
        question="Giam doc cong nghe cua Nova Digital la ai?",
        answer="Giam doc Cong nghe (CTO) cua Nova Digital la Le Thu Ha.",
        source_registry=registry,
        preferred_source_labels=("SOURCE_1",),
        max_sources=2,
    )

    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        wrong_source = await validator.validate(
            question="Giam doc cong nghe cua Nova Digital la ai?",
            answer="Giam doc Cong nghe (CTO) cua Nova Digital la Le Thu Ha.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        answer_source = await validator.validate(
            question="Giam doc cong nghe cua Nova Digital la ai?",
            answer="Giam doc Cong nghe (CTO) cua Nova Digital la Le Thu Ha.",
            source_registry=registry,
            cited_source_labels=("SOURCE_2",),
        )

        assert wrong_source.status == ClaimEvidenceStatus.INSUFFICIENT
        assert answer_source.status == ClaimEvidenceStatus.SUPPORTED

    assert should_reselect is True
    assert labels == ("SOURCE_2",)
    run_async(scenario())


def test_supported_related_citation_is_reselected_for_complete_answer_source() -> None:
    answer = "Việc tham gia salary review không tạo quyền đương nhiên được tăng lương."
    registry = sources(
        f"KHÔNG BẢO ĐẢM TĂNG LƯƠNG\n{answer}",
        ("Chu kỳ salary review mô phỏng. Review định kỳ không đồng nghĩa tăng lương tự động."),
    )

    should_reselect = _claim_validation_should_reselect_citations(
        status=ClaimEvidenceStatus.SUPPORTED,
        question="salary review được quy định như thế nào?",
        answer=answer,
        cited_source_labels=("SOURCE_2",),
        source_registry=registry,
    )
    labels = ClaimEvidenceValidationService().select_supporting_source_labels(
        question="salary review được quy định như thế nào?",
        answer=answer,
        source_registry=registry,
        preferred_source_labels=("SOURCE_2",),
        max_sources=2,
    )

    assert should_reselect is True
    assert labels[0] == "SOURCE_1"


def test_verbatim_policy_clause_is_not_contradicted_by_unrelated_chunk_polarity() -> None:
    answer = "Việc tham gia salary review không tạo quyền đương nhiên được tăng lương."

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="salary review được quy định như thế nào?",
            answer=answer,
            source_registry=source(
                "Một thay đổi khác không được tăng lương tự động.\n"
                f"{answer}\n"
                "Các nghĩa vụ pháp lý bắt buộc vẫn áp dụng."
            ),
            cited_source_labels=("SOURCE_1",),
        )

        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_verbatim_policy_clause_support_normalizes_pdf_line_wraps() -> None:
    answer = (
        "Việc tham gia salary review không tạo quyền đương nhiên "
        "được tăng lương. Tuy nhiên, công ty phải tuân thủ mức lương "
        "tối thiểu, thỏa thuận HĐLĐ và các nghĩa vụ pháp lý bắt buộc."
    )

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="salary review được quy định như thế nào?",
            answer=answer,
            source_registry=source(answer.replace("mức lương ", "mức lương\n ")),
            cited_source_labels=("SOURCE_1",),
        )

        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_replacement_relation_supports_supplemental_not_replacing_mandatory() -> None:
    async def scenario() -> None:
        evidence = (
            "Health coverage\n"
            "BHYT: mandatory statutory health insurance required by law.\n"
            "CarePlus: supplementary additional health insurance for employees."
        )
        validator = ClaimEvidenceValidationService()

        supported = await validator.validate(
            question="CarePlus co thay the BHYT bat buoc khong?",
            answer=("Khong. CarePlus la bao hiem suc khoe bo sung; BHYT van la bao hiem bat buoc."),
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )
        assert supported.status == ClaimEvidenceStatus.SUPPORTED
        assert supported.polarity == "NO"

        contradicted = await validator.validate(
            question="CarePlus co thay the BHYT bat buoc khong?",
            answer="Co. CarePlus thay the BHYT bat buoc.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )
        assert contradicted.status == ClaimEvidenceStatus.CONTRADICTED

    run_async(scenario())


def test_relation_excerpt_preserves_mandatory_and_supplemental_rows() -> None:
    text = (
        "Health coverage\n"
        "BHYT: mandatory statutory health insurance required by law.\n"
        "CarePlus: supplementary additional health insurance for employees.\n"
        "Claims are submitted through the HR portal."
    )

    excerpt = query_focused_excerpt(
        text,
        "CarePlus co thay the BHYT bat buoc khong?",
    )

    assert "BHYT" in excerpt
    assert "mandatory" in excerpt
    assert "CarePlus" in excerpt
    assert "supplementary" in excerpt


def test_expected_answer_scenario_is_non_answer_context() -> None:
    assert (
        classify_evidence_context("Tinh huong Ky vong cau tra loi AI phai phan biet hai che do.")
        == EvidenceContextKind.QUESTION_LIST
    )


def test_yes_no_support_requires_named_question_anchor() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        question = "EAP co gui noi dung tu van cho quan ly khong?"
        answer = "Khong. EAP khong gui noi dung tu van cho quan ly."

        generic = await validator.validate(
            question=question,
            answer=answer,
            source_registry=source("Thong tin noi dung nhay cam khong duoc gui cho quan ly."),
            cited_source_labels=("SOURCE_1",),
        )
        assert generic.status == ClaimEvidenceStatus.INSUFFICIENT

        anchored = await validator.validate(
            question=question,
            answer=answer,
            source_registry=source(
                "Suc khoe tinh than - EAP. Thong tin noi dung tu van "
                "khong duoc chuyen cho quan ly; cong ty chi nhan "
                "du lieu tong hop khong dinh danh."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert anchored.status == ClaimEvidenceStatus.SUPPORTED
        assert anchored.polarity == "NO"

    run_async(scenario())


def test_prompt_ranking_prefers_named_yes_no_policy_clause_over_generic_negative() -> None:
    generic = hit(
        301,
        "Thong tin noi dung nhay cam khong duoc gui cho quan ly trong kenh lam viec.",
    )
    policy = hit(
        302,
        "Suc khoe tinh than - EAP. Thong tin noi dung tu van khong duoc "
        "chuyen cho quan ly; cong ty chi nhan du lieu tong hop khong dinh danh.",
    )

    ranked = _rank_hits_for_prompt(
        (generic, policy),
        question="EAP co gui noi dung tu van cho quan ly khong?",
    )

    assert ranked[0].chunk_id == policy.chunk_id


def test_prompt_ranking_prefers_role_salary_row_over_unrelated_amounts() -> None:
    bonus = hit(
        303,
        "Meets Expectations 0,5 - 1,0 thang Base Salary. Project Delivery Bonus 5 - 30 trieu dong.",
    )
    salary_band = hit(
        304,
        "Dai Base Salary tham khao. Grade Vi du chuc danh. "
        "N5 Tech Lead / Engineering Manager / Functional Manager "
        "42 - 70 trieu dong. N6 Head / Director 65 - 110 trieu dong.",
    )

    ranked = _rank_hits_for_prompt(
        (bonus, salary_band),
        question="Engineering Manager thuoc grade nao va dai luong bao nhieu?",
    )

    assert ranked[0].chunk_id == salary_band.chunk_id


def test_prompt_ranking_prefers_lunch_allowance_row_for_compound_field_need() -> None:
    unrelated_benefit = hit(
        309,
        "Wellness allowance 2.400.000 dong/nam. Ergonomic support 1.500.000 dong/24 thang.",
        title="Chinh sach bao hiem va phuc loi",
    )
    lunch_allowance = hit(
        310,
        "Bang phu cap mo phong. An trua 900.000 d/thang. Hybrid stipend 500.000 d/thang.",
        title="Chinh sach tien luong va dai ngo",
    )

    ranked = _rank_hits_for_prompt(
        (unrelated_benefit, lunch_allowance),
        question="phu cap an trua moi thang",
    )

    assert ranked[0].chunk_id == lunch_allowance.chunk_id


def test_numeric_expected_answer_scenario_remains_non_answer_context() -> None:
    assert (
        classify_evidence_context(
            "Tinh huong va cau hoi kiem thu RAG. Ky vong cau tra loi: "
            "NovaCare co han muc noi tru 150 trieu dong."
        )
        == EvidenceContextKind.QUESTION_LIST
    )


def test_split_heading_numeric_expected_answer_scenario_is_non_answer_context() -> None:
    assert (
        classify_evidence_context(
            "TINH HUONG VA CAU HOI KIEM\n12 THU RAG\n"
            "Tinh huong Ky vong\ncau tra loi\n"
            "NovaCare co han muc noi tru 150 trieu dong."
        )
        == EvidenceContextKind.QUESTION_LIST
    )


def test_prompt_ranking_prefers_inpatient_limit_row_for_compound_field_need() -> None:
    unrelated_benefit = hit(
        311,
        "Nha khoa co ban 3 trieu dong. Thai san bo sung 20 trieu dong. "
        "Tai nan ca nhan 200 trieu dong.",
        title="Chinh sach bao hiem va phuc loi",
    )
    inpatient_limit = hit(
        312,
        "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh. "
        "Noi tru 150 trieu dong. Nhan vien chinh thuc sau khi hoan thanh thu viec.",
        title="Chinh sach bao hiem va phuc loi",
    )

    ranked = _rank_hits_for_prompt(
        (unrelated_benefit, inpatient_limit),
        question="han muc noi tru NovaCare moi nam",
    )

    assert ranked[0].chunk_id == inpatient_limit.chunk_id


def test_prompt_ranking_prefers_multi_value_yes_no_policy_table() -> None:
    benefits = hit(
        305,
        "Moi nhan vien chinh thuc co 04 phien EAP moi nam. "
        "Sinh nhat duoc 500.000 dong/nguoi. NovaCare co the tam dung "
        "sau ngay nghi viec dai ngay.",
    )
    annual_leave = hit(
        306,
        "Nghi hang nam huong nguyen luong. Muc nghi Doi tuong ap dung. "
        "12 ngay Cong viec trong dieu kien binh thuong. "
        "14 ngay Nguoi chua thanh nien hoac cong viec nang nhoc, doc hai. "
        "16 ngay Cong viec dac biet nang nhoc, doc hai.",
    )

    ranked = _rank_hits_for_prompt(
        (benefits, annual_leave),
        question="Moi nhan vien deu co 12 ngay nghi phep nam dung khong?",
    )

    assert ranked[0].chunk_id == annual_leave.chunk_id


def test_multi_value_duration_detection_accepts_broad_duration_table() -> None:
    table = (
        "Muc nghi Doi tuong ap dung. "
        "12 ngay Cong viec trong dieu kien binh thuong. "
        "14 ngay Nguoi chua thanh nien hoac cong viec nang nhoc, doc hai. "
        "16 ngay Cong viec dac biet nang nhoc, doc hai."
    )
    single_value = "Cong viec trong dieu kien binh thuong 12 ngay lam viec moi nam."

    assert _source_has_multi_value_duration_evidence(
        question="Nhan vien co bao nhieu ngay phep nam?",
        text=table,
    )
    assert not _source_has_multi_value_duration_evidence(
        question="Nhan vien co bao nhieu ngay phep nam?",
        text=single_value,
    )


def test_multi_value_duration_detection_ignores_unrelated_seniority_increment() -> None:
    source_text = (
        "12 ngay lam viec moi nam khi du 12 thang lam viec. "
        "Cu du 05 nam lam viec thi tang them 01 ngay nghi hang nam."
    )

    assert not _source_has_multi_value_duration_evidence(
        question="Nhan vien Nova Digital co bao nhieu ngay phep nam?",
        text=source_text,
    )


def test_prompt_ranking_prefers_multi_value_duration_table_for_broad_question() -> None:
    single_value = hit(
        307,
        "Cong viec trong dieu kien binh thuong 12 ngay lam viec moi nam.",
    )
    multi_value = hit(
        308,
        "Muc nghi Doi tuong ap dung. "
        "12 ngay Cong viec trong dieu kien binh thuong. "
        "14 ngay Nguoi chua thanh nien hoac cong viec nang nhoc, doc hai. "
        "16 ngay Cong viec dac biet nang nhoc, doc hai.",
    )

    ranked = _rank_hits_for_prompt(
        (single_value, multi_value),
        question="Nhan vien Nova Digital co bao nhieu ngay phep nam?",
    )

    assert ranked[0].chunk_id == multi_value.chunk_id


def test_multi_value_yes_no_negative_supported_by_alternative_values() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        evidence = (
            "Nghi hang nam huong nguyen luong. Muc nghi Doi tuong ap dung. "
            "12 ngay Cong viec trong dieu kien binh thuong. "
            "14 ngay Nguoi chua thanh nien hoac cong viec nang nhoc, doc hai. "
            "16 ngay Cong viec dac biet nang nhoc, doc hai."
        )

        result = await validator.validate(
            question="Moi nhan vien deu co 12 ngay nghi phep nam dung khong?",
            answer="Khong. Khong phai moi nhan vien deu co 12 ngay phep nam.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )

        assert result.status == ClaimEvidenceStatus.SUPPORTED
        assert result.polarity == "NO"

    run_async(scenario())


def test_replacement_relation_uses_full_numbered_source_before_polarity() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        evidence = (
            "03 Health\n"
            "BHYT bat buoc ket hop chuong trinh bao hiem suc khoe bo sung.\n"
            "1. Bao hiem y te bat buoc theo quy dinh phap luat.\n"
            "2. CarePlus - bao hiem suc khoe bo sung cho nhan vien."
        )

        result = await validator.validate(
            question="CarePlus co thay the BHYT bat buoc khong?",
            answer="Khong. CarePlus khong thay the BHYT bat buoc.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )

        assert result.status == ClaimEvidenceStatus.SUPPORTED
        assert result.polarity == "NO"

    run_async(scenario())
