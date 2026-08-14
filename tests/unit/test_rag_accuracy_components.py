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
from app.retrieval.models import HybridRetrievalHit
from app.retrieval.question_analysis import analyze_question
from app.retrieval.reranker import (
    HeuristicRetrievalReranker,
    SentenceTransformerCrossEncoderReranker,
)
from app.retrieval.reranker_factory import create_retrieval_reranker
from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    ClaimEvidenceValidationService,
)
from app.services.grounded_answer_service import (
    _question_focused_time_ranges_from_text,
    _rank_hits_for_prompt,
    _should_retry_incomplete_answer,
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


def source(text: str) -> PromptSourceRegistry:
    return PromptSourceRegistry(
        sources=(
            PromptSource(
                marker="[SOURCE_1]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Policy",
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
    assert analyze_question("Gio cot loi la may gio?").answer_type == "TIME_RANGE"
    assert analyze_question("Dong bao nhieu phan tram?").answer_type == "PERCENTAGE"
    assert analyze_question("Co tu dong tinh lam them gio khong?").answer_type == "YES_NO"


def test_question_analysis_distinguishes_percentage_amount_and_duration() -> None:
    percentage = analyze_question("Cong ty dong BHXH bao nhieu phan tram?")
    duration = analyze_question("Hybrid duoc remote toi da bao nhieu ngay moi tuan?")

    assert percentage.answer_type == "PERCENTAGE"
    assert percentage.asks_for_percentage is True
    assert percentage.asks_for_amount is False
    assert duration.answer_type == "DURATION"
    assert duration.asks_for_duration is True


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
    assert settings.reranker_candidate_k == 24
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
