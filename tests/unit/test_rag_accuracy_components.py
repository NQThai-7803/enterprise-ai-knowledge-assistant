from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from typing import Any
from uuid import UUID

from app.chat.context_builder import query_focused_excerpt, select_context_for_prompt
from app.citations.grounded_output import GroundedLLMOutput
from app.citations.models import PromptSource, PromptSourceRegistry
from app.core.config import Settings
from app.models import CitationSourceType
from app.retrieval.evidence_quality import EvidenceContextKind, classify_evidence_context
from app.retrieval.models import HybridRetrievalHit
from app.retrieval.question_analysis import analyze_question, retrieval_query_variants
from app.retrieval.reranker import (
    HeuristicRetrievalReranker,
    SentenceTransformerCrossEncoderReranker,
    _important_term_coverage_score,
)
from app.retrieval.reranker_factory import create_retrieval_reranker
from app.retrieval.structured import (
    build_structured_records,
    monetary_example_rows,
    monetary_value_period_pairs,
    requested_monetary_period,
)
from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    ClaimEvidenceValidationService,
    _validate_answer_against_evidence,
)
from app.services.grounded_answer_service import (
    _MONEY_VALUE_PATTERN,
    _canonicalize_yes_no_output,
    _claim_validation_should_reselect_citations,
    _filter_non_answer_context_hits,
    _filter_to_salary_band_hits,
    _filter_to_specific_term_hits,
    _focus_leave_policy_hit,
    _is_salary_band_request,
    _numeric_answer_missing_source_unit,
    _prompt_attendance_policy_score,
    _prompt_policy_relation_score,
    _prompt_query_needles,
    _prompt_sensitive_policy_score,
    _question_focused_time_ranges_from_text,
    _rank_hits_for_prompt,
    _reason_evidence_is_missing,
    _role_terms_for_prompt_question,
    _salary_band_role_query_terms,
    _salary_band_role_terms_match,
    _scored_question_focused_direct_value_from_text,
    _sensitive_policy_retrieval_phrases,
    _should_retry_incomplete_answer,
    _source_has_multi_value_duration_evidence,
    _structured_attendance_policy_answer,
    _structured_consultation_session_answer,
    _structured_credential_sharing_answer,
    _structured_direct_value_answer,
    _structured_example_expense_amount_answer,
    _structured_leave_approval_workflow_answer,
    _structured_leave_incident_time_answer,
    _structured_policy_clause_repair_generation,
    _structured_public_ai_input_answer,
    _structured_remote_accident_answer,
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


def test_retrieval_normalizes_developer_repository_vocabulary_without_changing_question() -> None:
    variants = retrieval_query_variants("Can I put source code on GitHub?")
    assert variants.original == "Can I put source code on GitHub?"
    assert "ma nguon" in variants.normalized
    assert "kho ma nguon" in variants.normalized


def test_policy_relation_ranking_requires_event_and_outcome_in_same_source() -> None:
    assert _prompt_policy_relation_score(
        question="If payday falls on a rest day, what happens?",
        text="pay date on a rest day moves to the preceding workday",
    ) > _prompt_policy_relation_score(
        question="If payday falls on a rest day, what happens?",
        text="employees have a weekly rest day",
    )
    assert (
        _prompt_policy_relation_score(
            question="Is an accident while working remotely automatically occupational?",
            text="remote accident is assessed by task, time, place, and evidence",
        )
        > 0
    )
    assert (
        _prompt_sensitive_policy_score(
            question="May I give a colleague my password?",
            text="Personal accounts: do not share passwords or access tokens.",
        )
        > 0
    )


def test_material_validation_rejects_unrelated_policy_clauses() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        payroll = await validator.validate(
            question="If my pay date falls on a holiday, what happens?",
            answer="Employees receive a weekly rest of at least 36 hours.",
            source_registry=source("Employees receive a weekly rest of at least 36 hours."),
            cited_source_labels=("SOURCE_1",),
        )
        assert payroll.status == ClaimEvidenceStatus.INSUFFICIENT
        accident = await validator.validate(
            question="Is an accident while remote at home automatically occupational?",
            answer="No. The conduct is not automatically sanctioned.",
            source_registry=source("The conduct is not automatically sanctioned."),
            cited_source_labels=("SOURCE_1",),
        )
        assert accident.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_credential_transfer_is_bound_to_explicit_sharing_prohibition() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        result = await validator.validate(
            question="Tôi đưa mật khẩu cho đồng nghiệp đăng nhập giúp được không?",
            answer="Không. Tài khoản cá nhân không được chia sẻ mật khẩu.",
            source_registry=source(
                "Mỗi người sử dụng tài khoản cá nhân; cấm chia sẻ mật khẩu, "
                "mã OTP, khóa API hoặc token truy cập."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_personal_repository_policy_outranks_unrelated_remote_schedule() -> None:
    schedule = hit(814, "Remote work requires prior registration and manager approval.")
    repository = hit(
        815,
        "Mã nguồn phải lưu trong kho được phê duyệt; không đưa mã nguồn lên kho cá nhân "
        "hoặc dịch vụ công cộng.",
    )
    ranked = _rank_hits_for_prompt(
        (schedule, repository),
        question="Tôi copy source code công ty lên GitHub cá nhân để làm ở nhà được không?",
    )
    assert ranked[0].chunk_id == repository.chunk_id


def test_sensitive_policy_supplement_uses_topic_not_benchmark_identity() -> None:
    assert "mã nguồn" in _sensitive_policy_retrieval_phrases(
        "May I copy source code to a personal repository?"
    )
    assert "mật khẩu" in _sensitive_policy_retrieval_phrases("Can I give a coworker my password?")
    assert _sensitive_policy_retrieval_phrases("How many vacation days remain?") == ()


def test_credential_transfer_rejects_wrong_object_and_unprohibited_source() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        for text in (
            "Do not share access badges with colleagues.",
            "Passwords may be reset by the help desk on request.",
        ):
            result = await validator.validate(
                question="Can I give my password to a coworker?",
                answer="No, I cannot share my password.",
                source_registry=source(text),
                cited_source_labels=("SOURCE_1",),
            )
            assert result.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_credential_transfer_rejects_exception_borrowed_from_adjacent_rule() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        result = await validator.validate(
            question="Can I give a coworker my password?",
            answer="No, do not share your password unless approved by a manager.",
            source_registry=source(
                "Do not share passwords or access tokens. Third-party data sharing "
                "may occur with manager approval."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status != ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_remote_schedule_bonus_requires_schedule_intent() -> None:
    schedule = "remote work core hours remain the same as office work."
    assert (
        _prompt_attendance_policy_score(
            text=schedule,
            question="If I work remote, do I keep the same core hours?",
        )
        > 0
    )
    assert (
        _prompt_attendance_policy_score(
            text=schedule,
            question="Can I copy source code to my personal repository while working remote?",
        )
        == 0
    )


def test_structured_credential_repair_copies_only_same_object_prohibition() -> None:
    registry = source(
        "Personal accounts; do not share passwords or access tokens.\n"
        "Third-party data may be shared with manager approval."
    )
    result = _structured_credential_sharing_answer(
        question="Can I give my password to a coworker?",
        source_registry=registry,
    )
    assert result is not None
    assert "do not share passwords" in result[0]
    assert "approval" not in result[0]
    assert (
        _structured_credential_sharing_answer(
            question="Can I give my password to a coworker?",
            source_registry=source("Access badges must not be shared with coworkers."),
        )
        is None
    )


def test_complete_amount_row_outranks_mid_row_chunk() -> None:
    complete = hit(816, "Dental care 7 million dong per year; basic coverage.", title="Benefits")
    truncated = hit(817, "tal care 7 million dong per year; basic coverage.", title="Benefits")
    ranked = _rank_hits_for_prompt(
        (truncated, complete),
        question="How much is dental care supported per year?",
    )
    assert ranked[0].chunk_id == complete.chunk_id


def test_example_expense_row_binds_its_own_amount_and_period() -> None:
    text = (
        "Category Limit Eligible expense examples\n"
        "Yoga, swimming, walking\n"
        "Wellness activity 8.000.000 dong/year\n"
        "Keyboard, mouse\n"
        "Ergonomic equipment 1.100.000 dong/24 months"
    )
    assert monetary_example_rows(
        text,
        focus_terms=("yoga", "swimming"),
        requested_period="nam",
    )
    registry = source(text)
    question = "Công ty hỗ trợ yoga/swimming mỗi năm bao nhiêu?"
    result = _structured_example_expense_amount_answer(
        question=question,
        source_registry=registry,
    )
    assert result is not None
    assert "8.000.000" in result[0]
    assert "year" in result[0]
    assert "1.100.000" not in result[0]

    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        good = await validator.validate(
            question=question,
            answer=result[0],
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert good.status == ClaimEvidenceStatus.SUPPORTED
        wrong = await validator.validate(
            question=question,
            answer="Yoga/swimming gets 1.100.000 dong/24 months.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert wrong.status != ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())
    assert (
        _structured_example_expense_amount_answer(
            question="Công ty hỗ trợ cycling mỗi năm bao nhiêu?",
            source_registry=registry,
        )
        is None
    )


def test_example_expense_header_stripped_by_focused_excerpt_keeps_row_binding() -> None:
    excerpt = (
        "Answer-focused evidence:\n"
        "Yoga, swimming, walking\n"
        "Wellness activity 8.000.000 dong/year\n"
        "Keyboard, mouse\n"
        "Ergonomic equipment 1.100.000 dong/24 months"
    )
    rows = monetary_example_rows(excerpt, focus_terms=("yoga", "swimming"))
    assert len(rows) == 1
    assert rows[0].row_value == "Wellness activity 8.000.000 dong/year"
    neighboring_rows = monetary_example_rows(excerpt, focus_terms=("keyboard", "mouse"))
    assert len(neighboring_rows) == 1
    assert neighboring_rows[0].row_value == "Ergonomic equipment 1.100.000 dong/24 months"
    assert (
        monetary_example_rows(
            excerpt.removeprefix("Answer-focused evidence:\n"),
            focus_terms=("yoga", "swimming"),
        )
        == ()
    )


def test_unpaid_leave_notice_is_not_a_salary_band_question() -> None:
    assert analyze_question("Nghỉ không lương dài ngày nên báo trước bao lâu?").answer_type == (
        "DURATION"
    )
    assert analyze_question("Dải lương tham khảo của kỹ sư là bao nhiêu?").answer_type == ("AMOUNT")


def test_unpaid_leave_notice_repair_reads_named_or_narrative_policy_deadline() -> None:
    question = "Nghỉ không lương dài ngày nên báo trước bao lâu?"
    for policy in (
        "Nghỉ không lương dài ngày Trước ít nhất 08 ngày làm việc, nếu tình huống cho phép",
        "Nghỉ không hưởng lương theo thỏa thuận: Đề nghị từ 04 ngày làm việc liên tục "
        "trở lên nên gửi trước ít nhất 08 ngày làm việc, trừ trường hợp khẩn cấp.",
    ):
        generation = _structured_value_repair_generation(
            question=question,
            source_registry=source(policy),
        )
        assert generation is not None
        assert "08 ngay lam viec" in json.loads(generation.content)["answer"]


def test_hospitalization_intent_does_not_depend_on_plan_brand() -> None:
    question = "CloverCare nằm viện thì hạn mức bao nhiêu?"

    assert analyze_question(question).asks_for_amount
    assert "noi tru" in retrieval_query_variants(question).normalized


def test_retrieval_coverage_retains_organization_name_as_evidence_term() -> None:
    terms = ("nova",)

    assert _important_term_coverage_score("nova digital ceo", terms) > (
        _important_term_coverage_score("orion digital ceo", terms)
    )
    assert _important_term_coverage_score("novaassist platform", terms) == -90.0


def test_benefit_retrieval_normalizes_conversational_childbirth_topic() -> None:
    variants = retrieval_query_variants("Co con thi cong ty ho tro bao nhieu tien?")

    assert "sinh con" in variants.normalized


def test_benefit_structured_repairs_bind_named_rows_and_grouped_money() -> None:
    benefits = source(
        "Ty le cu the duoc cap nhat theo phap luat tai ky payroll.\n"
        "Ergonomic support 1.500.000 d/24 thang.\n"
        "Ket hon cua nhan vien 2.000.000 d De nghi tren HRM.\n"
        "Sinh con / nhan con nuoi hop phap 2.000.000 d/lan.\n"
        "Tang che - cha/me/vo/chong/con 3.000.000 d."
    )

    bhxh = _structured_value_repair_generation(
        question="Trong policy co ghi co dinh ty le BHXH cong ty dong khong?",
        source_registry=benefits,
    )
    ergonomic_question = "Tien mua do ergonomic duoc ho tro bao nhieu va bao lau mot lan?"
    ergonomic_analysis = analyze_question(ergonomic_question)
    assert ergonomic_analysis.asks_for_amount
    assert _MONEY_VALUE_PATTERN.search("ergonomic support 1.500.000 d/24 thang") is not None
    assert "ergonomic" in _prompt_query_needles(ergonomic_question)[1]
    ergonomic_candidate = _scored_question_focused_direct_value_from_text(
        question=ergonomic_question,
        source_text="Ergonomic support 1.500.000 d/24 thang.",
        analysis=ergonomic_analysis,
    )
    ergonomic = _structured_value_repair_generation(
        question=ergonomic_question,
        source_registry=benefits,
    )
    marriage = _structured_value_repair_generation(
        question="Nhan vien ket hon co khoan ho tro rieng cua cong ty khong?",
        source_registry=benefits,
    )
    childbirth = _structured_value_repair_generation(
        question="Co con thi cong ty ho tro bao nhieu tien?",
        source_registry=benefits,
    )

    assert bhxh is not None
    assert "không quy định một tỷ lệ cố định" in json.loads(bhxh.content)["answer"]
    assert ergonomic_candidate is not None, (
        ergonomic_analysis,
        _prompt_query_needles(ergonomic_question),
        _MONEY_VALUE_PATTERN.search("ergonomic support 1.500.000 d/24 thang").group(0),
    )
    assert ergonomic is not None
    assert "1.500.000 d/24 thang" in json.loads(ergonomic.content)["answer"]
    assert marriage is not None
    marriage_answer = json.loads(marriage.content)["answer"]
    assert marriage_answer.startswith("Có.")
    assert "2.000.000 d" in marriage_answer
    assert childbirth is not None
    childbirth_answer = json.loads(childbirth.content)["answer"]
    assert "2.000.000 d/lan" in childbirth_answer
    assert "3.000.000" not in childbirth_answer


def test_prompt_ranking_prefers_named_monetary_benefit_row() -> None:
    unrelated = hit(
        901,
        "Khoan ho tro khac khong ap dung cho truong hop rieng.",
        title="Compensation policy",
    )
    marriage = hit(
        902,
        "Ket hon cua nhan vien 2.000.000 d De nghi tren HRM.",
        title="Benefits policy",
    )

    ranked = _rank_hits_for_prompt(
        (unrelated, marriage),
        question="Nhan vien ket hon co khoan ho tro rieng cua cong ty khong?",
    )

    assert ranked[0].chunk_id == marriage.chunk_id


def test_runtime_shaped_benefit_excerpts_survive_repair_and_validation() -> None:
    benefit_chunk = (
        "Quan ly khong duoc su dung viec nhan vien tham gia EAP lam can cu danh gia.\n"
        "3. Wellness allowance\n"
        "Khoan Han muc mo phong Vi du chi phi hop le\n"
        "Suc khoe/van dong 2.400.000 d/nam\n"
        "Gym, yoga, boi, chay bo, ung dung suc khoe co hoa don.\n"
        "Ergonomic support 1.500.000 d/24 thang\n"
        "Ban phim, chuot cong thai hoc, ke laptop; thiet bi phu hop danh muc.\n"
        "1. Cac khoan ho tro mo phong\n"
        "Su kien Muc ho tro mo phong Ho so toi thieu\n"
        "Ket hon cua nhan vien 2.000.000 d De nghi tren HRM + xac nhan phu hop.\n"
        "Sinh con / nhan con nuoi hop phap 2.000.000 d/lan.\n"
        "Tang che - cha/me/vo/chong/con 3.000.000 d."
    )
    cases = (
        (
            "Tien mua do ergonomic duoc ho tro bao nhieu va bao lau mot lan?",
            "Ergonomic support 1.500.000 d/24 thang",
        ),
        (
            "Nhan vien ket hon co khoan ho tro rieng cua cong ty khong?",
            "Ket hon cua nhan vien 2.000.000 d",
        ),
    )

    async def scenario() -> None:
        for question, expected_row in cases:
            excerpt = query_focused_excerpt(benefit_chunk, question)
            assert expected_row in excerpt, excerpt
            registry = source(excerpt, title="Benefits")
            generation = _structured_value_repair_generation(
                question=question,
                source_registry=registry,
            )
            assert generation is not None, excerpt
            payload = json.loads(generation.content)
            validation = await ClaimEvidenceValidationService().validate(
                question=question,
                answer=payload["answer"],
                source_registry=registry,
                cited_source_labels=tuple(payload["citations"]),
                require_subject_attribute_alignment=True,
            )
            assert validation.status == ClaimEvidenceStatus.SUPPORTED, (
                question,
                excerpt,
                payload,
                validation.status,
            )

    run_async(scenario())


def test_split_explicit_unfixed_percentage_clause_survives_excerpt_and_validation() -> None:
    policy = (
        "Doi soat co quan bao hiem; sai lech phai bao HR Benefits.\n"
        "Ty le cu the duoc cap nhat\n"
        "theo phap luat tai ky payroll.\n"
        "Thay doi du lieu dinh danh phai duoc cap nhat kip thoi."
    )
    question = "Trong policy co ghi co dinh ty le bao hiem cong ty dong khong?"
    excerpt = query_focused_excerpt(policy, question)

    assert "Ty le cu the duoc cap nhat" in excerpt
    assert "theo phap luat tai ky payroll" in excerpt
    assert "Thay doi du lieu dinh danh" not in excerpt
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(excerpt),
    )
    assert generation is not None
    payload = json.loads(generation.content)

    async def scenario() -> None:
        validation = await ClaimEvidenceValidationService().validate(
            question=question,
            answer=payload["answer"],
            source_registry=source(excerpt),
            cited_source_labels=tuple(payload["citations"]),
            require_subject_attribute_alignment=True,
        )
        assert validation.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_acronym_in_percentage_confirmation_does_not_trigger_person_excerpt() -> None:
    policy = (
        "BHXH duoc doi soat qua co quan bao hiem.\n"
        "Ty le cu the duoc cap nhat\n"
        "theo phap luat tai ky payroll."
    )

    excerpt = query_focused_excerpt(
        policy,
        "Trong policy co ghi co dinh ty le BHXH cong ty dong khong?",
    )

    assert "Ty le cu the duoc cap nhat theo phap luat tai ky payroll" in excerpt


def test_named_monetary_benefit_validation_does_not_bypass_scenario_binding() -> None:
    registry = source(
        "Home office allowance 1200000 dong/nam for approved regular remote work; "
        "does not apply to a single ad hoc remote day."
    )

    async def scenario() -> None:
        direct = await ClaimEvidenceValidationService().validate(
            question="Does the company provide a home office allowance benefit?",
            answer="Yes. The home office allowance is 1200000 dong/nam.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        scenario_claim = await ClaimEvidenceValidationService().validate(
            question="Does one ad hoc remote day receive the home office allowance?",
            answer="Yes. One ad hoc remote day receives 1200000 dong/nam.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert direct.status == ClaimEvidenceStatus.SUPPORTED
        assert scenario_claim.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_question_analysis_does_not_read_cong_ty_len_as_ty_le_percentage() -> None:
    analysis = analyze_question(
        "Toi copy source code cong ty len GitHub ca nhan de lam o nha duoc khong?"
    )

    assert analysis.answer_type == "YES_NO"
    assert analysis.asks_for_percentage is False


def test_question_analysis_does_not_read_public_ai_as_vietnamese_who() -> None:
    analysis = analyze_question(
        "Toi co the paste source code noi bo vao ChatGPT/public AI de hoi loi khong?"
    )

    assert analysis.answer_type == "YES_NO"
    assert analysis.asks_for_person is False


def test_structured_policy_repair_copies_sensitive_action_and_reporting_clauses() -> None:
    registry = source(
        "Ma nguon phai luu trong kho duoc phe duyet; khong dua ma nguon len kho ca nhan.\n"
        "Bao ngay cho Service Desk va Security Operations khi nghi ngo lo thong tin xac thuc."
    )

    repository = _structured_policy_clause_repair_generation(
        question="Toi copy source code cong ty len GitHub ca nhan duoc khong?",
        source_registry=registry,
    )
    reporting = _structured_policy_clause_repair_generation(
        question="Neu nghi tai khoan bi lo thi phai bao ai?",
        source_registry=registry,
    )

    assert repository is not None
    assert "khong dua ma nguon" in repository.content
    assert reporting is not None
    assert "Service Desk" in reporting.content


def test_sensitive_policy_validation_accepts_named_service_category_evidence() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        repository = await validator.validate(
            question="Toi copy source code cong ty len GitHub ca nhan duoc khong?",
            answer=(
                "Khong dua ma nguon, secret, du lieu khach hang hoac cau hinh san xuat "
                "len kho ca nhan hoac dich vu cong cong."
            ),
            source_registry=source(
                "Answer-focused evidence:\n"
                "Ma nguon phai luu trong kho duoc phe duyet; khong dua ma nguon, secret, "
                "du lieu khach hang hoac cau hinh san\n"
                "xuat len kho ca nhan hoac dich vu cong cong."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        public_ai = await validator.validate(
            question="Toi co the paste source code noi bo vao ChatGPT/public AI khong?",
            answer="Khong nhap ma nguon doc quyen vao dich vu AI cong cong.",
            source_registry=source(
                "Khong nhap ma nguon doc quyen vao dich vu AI cong cong chua duoc danh gia."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert repository.status is ClaimEvidenceStatus.SUPPORTED
        assert public_ai.status is ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_security_escalation_excerpt_keeps_reporting_recipient_clause() -> None:
    excerpt = query_focused_excerpt(
        "Dieu 13. Tai khoan va kiem soat truy cap\n"
        "Moi nguoi su dung tai khoan ca nhan; cam chia se mat khau va ma OTP.\n"
        "Bat xac thuc da yeu to khi he thong ho tro.\n"
        "Bao ngay cho Service Desk va Security Operations khi nghi ngo lo thong tin "
        "xac thuc hoac co dang nhap bat thuong.",
        "Neu nghi tai khoan bi lo thi phai bao ai?",
    )

    assert "Service Desk" in excerpt
    assert "Security Operations" in excerpt


def test_named_public_ai_service_accepts_direct_policy_category_evidence() -> None:
    assert not _reason_evidence_is_missing(
        question="Toi co the paste source code vao ChatGPT/public AI khong?",
        source_registry=source(
            "Khong nhap ma nguon doc quyen vao dich vu AI cong cong chua duoc danh gia."
        ),
    )
    assert _reason_evidence_is_missing(
        question="Toi co the paste source code vao ChatGPT/public AI khong?",
        source_registry=source("Quy trinh phe duyet nghi phep tren HRM."),
    )


def test_question_analysis_treats_approval_who_as_workflow_role() -> None:
    analysis = analyze_question("Ai duyet yeu cau sua cham cong cua minh?")

    assert analysis.answer_type == "OTHER"
    assert analysis.asks_for_person is False


def test_question_analysis_does_not_confuse_tieng_with_money() -> None:
    analysis = analyze_question("Mot tuan binh thuong lam bao nhieu tieng?")

    assert analysis.answer_type == "DURATION"
    assert analysis.asks_for_duration is True
    assert analysis.asks_for_amount is False
    normalized = retrieval_query_variants("Mot tuan lam bao nhieu tieng?").normalized
    assert "bao nhieu gio" in normalized
    assert "tieng" not in normalized


def test_question_analysis_detects_colloquial_work_duration_and_clock_range() -> None:
    daily = analyze_question("Moi ngay lam may tieng vay?")
    arrival = analyze_question("Sang minh duoc vao lam tu may gio toi may gio?")

    assert daily.answer_type == "DURATION"
    assert daily.asks_for_duration is True
    assert arrival.answer_type == "TIME_RANGE"
    assert arrival.asks_for_time_range is True


def test_question_analysis_keeps_clock_and_yes_no_attendance_intents_distinct() -> None:
    corresponding_end = analyze_question("Neu vao luc 9 gio thi may gio duoc ve?")
    remote_core_hours = analyze_question("Lam remote thi co phai giu core hours khong?")

    assert corresponding_end.answer_type == "TIME"
    assert corresponding_end.asks_for_duration is False
    assert remote_core_hours.answer_type == "YES_NO"
    assert remote_core_hours.asks_for_time_range is False


def test_question_analysis_detects_start_and_end_windows_as_time_ranges() -> None:
    start = analyze_question("Khung bat dau linh hoat la gi?")
    end = analyze_question("What is the end window?")

    assert start.answer_type == "TIME_RANGE"
    assert start.asks_for_time_range is True
    assert end.answer_type == "TIME_RANGE"
    assert end.asks_for_time_range is True


def test_question_analysis_distinguishes_review_timeline_from_salary_amount() -> None:
    review_timeline = analyze_question("Salary review dien ra khoang thoi gian nao?")
    salary_amount = analyze_question("Salary cua Senior Engineer khoang bao nhieu?")
    payment_date = analyze_question("Cong ty tra luong ngay nao?")

    assert review_timeline.answer_type == "TIMELINE"
    assert review_timeline.asks_for_timeline is True
    assert review_timeline.asks_for_amount is False
    assert salary_amount.answer_type == "AMOUNT"
    assert payment_date.answer_type == "DATE"


def test_review_timeline_excerpt_preserves_ordered_stages_not_adjacent_amounts() -> None:
    text = (
        "Salary review cycle\n"
        "Performance review: Jan-Feb\n"
        "Calibration: March\n"
        "Budget approval: Mar-Apr\n"
        "Notification: April\n"
        "Normally effective: 01/05\n"
        "Annual bonus target: 0.5-1.0 months Base Salary\n"
    )

    excerpt = query_focused_excerpt(text, "Salary review dien ra khoang thoi gian nao?")
    effective_excerpt = query_focused_excerpt(text, "Salary review effective date?")

    assert "Jan-Feb" in excerpt
    assert "March" in excerpt
    assert "Mar-Apr" in excerpt
    assert "01/05" in excerpt
    assert "0.5-1.0 months" not in excerpt
    assert "01/05" in effective_excerpt


def test_review_timeline_survives_prompt_selection_under_budget() -> None:
    question = "Thường salary review diễn ra khoảng thời gian nào?"
    timeline = hit(
        701,
        "Chu kỳ salary review mô phỏng\n"
        "Đánh giá hiệu suất năm | Tháng 01 - 02\n"
        "Hiệu chỉnh/Calibration | Tháng 03\n"
        "Phê duyệt ngân sách tăng lương | Tháng 03 - 04\n"
        "Thông báo điều chỉnh | Trong tháng 04\n"
        "Ngày hiệu lực thông thường | 01/05\n"
        "Meets Expectations | 0,5 - 1,0 tháng Base Salary",
        title="Salary policy",
    )
    competing_amounts = hit(
        702,
        "Dải Base Salary tham khảo: Senior Engineer 28 - 48 triệu đồng; "
        "Engineering Manager 42 - 70 triệu đồng.",
        title="Salary policy",
    )

    class WordCounter:
        def count(self, text: str) -> int:
            return len(text.split())

    ranked = _rank_hits_for_prompt((competing_amounts, timeline), question=question)
    selected = select_context_for_prompt(
        hits=ranked,
        history_messages=(),
        question=question,
        system_prompt="Answer from sources.",
        token_counter=WordCounter(),
        max_tokens=120,
    )

    assert ranked[0].chunk_id == timeline.chunk_id
    assert selected.items[0].chunk_id == timeline.chunk_id
    prompt_evidence = selected.items[0].text
    assert "Tháng 01 - 02" in prompt_evidence
    assert "Tháng 03 - 04" in prompt_evidence
    assert "01/05" in prompt_evidence
    assert "0,5 - 1,0" not in prompt_evidence


def test_unsupported_review_timeline_has_no_structured_answer() -> None:
    generation = _structured_value_repair_generation(
        question="Thường salary review diễn ra khoảng thời gian nào?",
        source_registry=source("Salary review does not guarantee an automatic salary increase."),
    )

    assert generation is None


def test_structured_bonus_range_keeps_rating_decimal_bounds_and_unit() -> None:
    comma_registry = source(
        "Annual Performance Bonus\n"
        "Exceptional 1,5 - 2,0 thang Base Salary\n"
        "Meets Expectations 0,5 - 1,0 thang Base Salary\n"
        "Partially Meets 0 - 0,5 thang Base Salary"
    )
    dot_registry = source(
        "Annual Performance Bonus\n"
        "Meets Expectations 0.5 - 1.0 months Base Salary\n"
        "Partially Meets 0 - 0.5 months Base Salary"
    )

    comma = _structured_value_repair_generation(
        question="Meets Expectations thi bonus muc tieu co bao nhieu thang luong?",
        source_registry=comma_registry,
    )
    dot = _structured_value_repair_generation(
        question="Meets Expectations bonus target how much months Base Salary?",
        source_registry=dot_registry,
    )
    unsupported = _structured_value_repair_generation(
        question="Outstanding thi bonus muc tieu co bao nhieu thang luong?",
        source_registry=comma_registry,
    )

    assert comma is not None
    assert dot is not None
    assert unsupported is None
    comma_payload = json.loads(comma.content)
    assert comma_payload["answer"] == "0,5–1,0 thang Base Salary."
    assert "0 - 0,5" not in comma_payload["answer"]
    assert json.loads(dot.content)["answer"] == "0.5–1.0 months Base Salary."

    async def scenario() -> None:
        validation = await ClaimEvidenceValidationService().validate(
            question="Meets Expectations thi bonus muc tieu co bao nhieu thang luong?",
            answer=comma_payload["answer"],
            source_registry=comma_registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert validation.status is ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_remote_may_ngay_is_a_duration_request() -> None:
    analysis = analyze_question("Lam hybrid thi moi tuan duoc o nha may ngay?")

    assert analysis.asks_for_duration is True


def test_wfh_is_normalized_to_remote_for_retrieval() -> None:
    question = "Lam hybrid duoc WFH bao nhieu ngay/tuan?"
    variants = retrieval_query_variants(question)
    analysis = analyze_question(question)

    assert "remote" in variants.normalized.casefold()
    assert "wfh" not in variants.normalized.casefold()
    assert analysis.answer_type == "DURATION"


def test_checkout_is_augmented_with_attendance_correction_terms() -> None:
    variants = retrieval_query_variants("quen checkout thi sao?")

    assert "checkout" in variants.normalized.casefold()
    assert "cham cong dieu chinh" in variants.normalized.casefold()


def test_prompt_ranking_prefers_document_title_matching_question_topic() -> None:
    unrelated_adjustment = hit(
        27,
        "Gui yeu cau doi soat trong vong 10 ngay lam viec ke tu khi phat hien sai lech.",
        title="Chinh sach nghi cua nguoi lao dong",
    )
    attendance_adjustment = hit(
        28,
        "Neu thieu check-in/out, nhan vien gui yeu cau dieu chinh trong 03 ngay lam viec.",
        title="Chinh sach lam viec va cham cong",
    )

    ranked = _rank_hits_for_prompt(
        (unrelated_adjustment, attendance_adjustment),
        question="Quen cham cong thi trong bao lau nen gui yeu cau chinh?",
    )

    assert ranked[0] == attendance_adjustment


def test_prompt_ranking_keeps_cham_cong_title_against_unrelated_duration_rows() -> None:
    payroll = hit(
        29,
        "Nhan vien gui ticket payroll; muc tieu phan hoi trong 03 ngay lam viec.",
        title="Chinh sach tien luong phu cap va thuong",
    )
    leave = hit(
        30,
        "Gui yeu cau doi soat so du phep trong vong 10 ngay lam viec.",
        title="Chinh sach nghi cua nguoi lao dong",
    )
    attendance = hit(
        31,
        "Neu thieu check-in/out, gui yeu cau dieu chinh trong 03 ngay lam viec.",
        title="Chinh sach lam viec va cham cong",
    )

    ranked = _rank_hits_for_prompt(
        (payroll, leave, attendance),
        question="Quen cham cong thi trong bao lau nen gui yeu cau chinh?",
    )

    assert ranked[0] == attendance


def test_prompt_ranking_binds_work_and_lunch_durations_to_schedule_row() -> None:
    leave = hit(
        34,
        "Moi tuan duoc nghi it nhat 24 gio. Chua du 12 thang thi phep tinh theo ty le.",
        title="Leave policy",
    )
    schedule = hit(
        35,
        "Tong thoi gian lam viec 08 gio/ngay; 40 gio/tuan. Nghi trua tieu chuan 60 phut.",
        title="Working time policy",
    )

    weekly = _rank_hits_for_prompt(
        (leave, schedule),
        question="Mot tuan binh thuong lam bao nhieu tieng?",
    )
    lunch = _rank_hits_for_prompt(
        (leave, schedule),
        question="Nghi trua thuong bao lau?",
    )

    assert weekly[0] == schedule
    assert lunch[0] == schedule


def test_prompt_ranking_filters_distractors_for_short_work_schedule_questions() -> None:
    leave = hit(
        341,
        "Cong viec binh thuong 12 ngay. Moi tuan nghi 24 gio lien tuc.",
        title="Leave policy",
    )
    salary = hit(
        342,
        "Muc luong 5 - 2 va chu ky 0 - 1; cap bac 5 - 1 va 0 - 0.",
        title="Salary policy",
    )
    schedule = hit(
        343,
        "Tong thoi gian lam viec 08 gio/ngay; 40 gio/tuan. "
        "Khung bat dau linh hoat 08:00 - 09:00. "
        "Gio cot loi 09:30 - 11:30 va 13:30 - 16:30.",
        title="Working time policy",
    )

    for question in (
        "Moi ngay lam may tieng vay?",
        "Sang minh duoc vao lam tu may gio toi may gio?",
        "core hour may gio?",
    ):
        ranked = _rank_hits_for_prompt((leave, salary, schedule), question=question)
        assert ranked[0] == schedule


def test_prompt_ranking_prefers_operational_approver_over_document_approver() -> None:
    metadata = hit(
        32,
        "Nguoi phe duyet mo phong Nguyen Anh Khoa - Tong Giam doc.",
        title="Chinh sach lam viec va cham cong",
    )
    workflow = hit(
        33,
        "Quan ly truc tiep kiem tra yeu cau dieu chinh cham cong va phe duyet/tu choi.",
        title="Chinh sach lam viec va cham cong",
    )

    ranked = _rank_hits_for_prompt(
        (metadata, workflow),
        question="Ai duyet yeu cau sua cham cong cua minh?",
    )

    assert ranked[0] == workflow


def test_prompt_ranking_binds_attendance_scenarios_to_outcome_clauses() -> None:
    distractor = hit(
        330,
        "HR doi soat payroll va ho tro nhan vien theo quy trinh chung.",
        title="Compensation policy",
    )
    locked_period = hit(
        331,
        "Sau khi khoa ky, dieu chinh muon chi thuc hien qua yeu cau dac biet "
        "co phe duyet cua HR va quan ly co tham quyen.",
        title="Attendance policy",
    )
    remote_hours = hit(
        332,
        "Hybrid/remote: Giu nguyen thoi luong, gio cot loi va nghia vu cham cong "
        "nhu khi lam tai van phong.",
        title="Attendance policy",
    )
    late_arrival = hit(
        333,
        "Di muon co the duoc bu trong cung ngay neu duoc quan ly chap thuan; "
        "khong duoc tu y bu sang ngay khac.",
        title="Attendance policy",
    )
    on_call = hit(
        334,
        "On-call khong tu dong duoc coi la lam them; thoi gian thuc te xu ly su co "
        "phai duoc ghi nhan.",
        title="Attendance policy",
    )

    scenarios = (
        ("Sau khi HR khoa ky cong roi con sua duoc nua khong?", locked_period),
        ("Lam remote thi co phai giu core hours khong?", remote_hours),
        ("Di muon thi bu sang ngay mai duoc khong?", late_arrival),
        ("On call khong co incident thi co tinh het la OT khong?", on_call),
    )
    for question, expected in scenarios:
        assert _rank_hits_for_prompt((distractor, expected), question=question)[0] == expected


def test_corresponding_work_schedule_time_uses_paired_range_position() -> None:
    generation = _structured_value_repair_generation(
        question="Neu vao luc 9 gio thi khoang may gio duoc ve?",
        source_registry=source(
            "Khung bat dau linh hoat 08:00 - 09:00\n"
            "Khung ket thuc tuong ung 17:00 - 18:00\n"
            "Gio cot loi 09:30 - 11:30 va 13:30 - 16:30",
            title="Attendance policy",
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "09:00" in payload["answer"]
    assert "18:00" in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]


def test_corresponding_work_schedule_time_wins_over_wider_condition_row() -> None:
    registry = source(
        "Answer-focused evidence:\n"
        "Ngay lam viec Thu Hai - Thu Sau\n"
        "Tong thoi gian lam viec 08 gio/ngay; 40 gio/tuan\n"
        "Khung bat dau linh hoat 08:00 - 09:00\n"
        "Khung ket thuc tuong ung 17:00 - 18:00\n"
        "Gio cot loi 09:30 - 11:30 va 13:30 - 16:30",
        title="Attendance policy",
    )

    generation = _structured_value_repair_generation(
        question="Neu vao luc 9 gio thi khoang may gio duoc ve?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "09:00" in payload["answer"]
    assert "18:00" in payload["answer"]


def test_core_hours_range_ignores_other_schedule_fields_and_sources() -> None:
    registry = sources(
        "Khung gio tham chieu 08:15 - 17:15; nghi trua 12:15 - 13:15; "
        "bat dau linh hoat 08:00 - 09:00.",
        "Khung bat dau linh hoat 08:00 - 09:00; "
        "khung ket thuc tuong ung 17:00 - 18:00; "
        "Gio cot loi 10:00 - 12:00 va 14:00 - 16:00.",
    )
    generation = _structured_value_repair_generation(
        question="Core hours cua cong ty la khung nao?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["citations"] == ["SOURCE_2"]
    assert "10:00" in payload["answer"]
    assert "14:00" in payload["answer"]
    assert "08:15" not in payload["answer"]
    assert "08:00" not in payload["answer"]


def test_flexible_start_keeps_its_own_range_beside_core_hours() -> None:
    generation = _structured_value_repair_generation(
        question="Khung bat dau linh hoat la may gio?",
        source_registry=source(
            "Khung bat dau linh hoat 08:00 - 09:00; Gio cot loi 10:00 - 12:00 va 14:00 - 16:00."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "08:00" in payload["answer"]
    assert "09:00" in payload["answer"]
    assert "10:00" not in payload["answer"]
    assert "14:00" not in payload["answer"]


def test_wrapped_schedule_field_keeps_label_with_its_value_ranges() -> None:
    generation = _structured_value_repair_generation(
        question="Core hours la khung nao?",
        source_registry=source(
            "Khung bat dau linh hoat 08:00 - 09:00\nGio cot loi\n10:00 - 12:00 va 14:00 - 16:00"
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "10:00" in payload["answer"]
    assert "14:00" in payload["answer"]
    assert "08:00" not in payload["answer"]


def test_afternoon_core_hours_start_returns_only_requested_clock() -> None:
    question = "Buoi chieu gio cot loi bat dau luc may gio?"
    assert analyze_question(question).answer_type == "TIME"
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(
            "Khung bat dau linh hoat 08:00 - 09:00; "
            "khung ket thuc tuong ung 17:00 - 18:00; "
            "Gio cot loi 10:00 - 12:00 va 14:00 - 16:00."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "14:00" in payload["answer"]
    assert "10:00" not in payload["answer"]
    assert "08:00" not in payload["answer"]
    assert "17:00" not in payload["answer"]


def test_named_schedule_field_absent_never_borrows_neighboring_range() -> None:
    registry = source("Khung bat dau linh hoat 08:00 - 09:00; nghi trua 12:00 - 13:00.")
    assert (
        _structured_value_repair_generation(
            question="Core hours la khung nao?",
            source_registry=registry,
        )
        is None
    )
    assert (
        _structured_value_repair_generation(
            question="Buoi chieu gio cot loi bat dau luc may gio?",
            source_registry=registry,
        )
        is None
    )


def test_core_hours_validation_rejects_other_schedule_field_clocks() -> None:
    registry = source(
        "Khung bat dau linh hoat 08:00 - 09:00; "
        "khung ket thuc tuong ung 17:00 - 18:00; "
        "Gio cot loi 10:00 - 12:00 va 14:00 - 16:00."
    )

    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        correct = await validator.validate(
            question="Core hours la khung nao?",
            answer="Gio cot loi la 10:00 - 12:00 va 14:00 - 16:00.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        mixed = await validator.validate(
            question="Core hours la khung nao?",
            answer="Gio cot loi la 08:00 - 09:00 va 14:00 - 16:00.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert correct.status == ClaimEvidenceStatus.SUPPORTED
        assert mixed.status != ClaimEvidenceStatus.SUPPORTED
        afternoon = await validator.validate(
            question="Buoi chieu gio cot loi bat dau luc may gio?",
            answer="Gio cot loi buoi chieu bat dau luc 14:00.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        wrong_endpoint = await validator.validate(
            question="Buoi chieu gio cot loi bat dau luc may gio?",
            answer="Gio cot loi buoi chieu bat dau luc 08:00.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert afternoon.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_endpoint.status != ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_core_hour_endpoint_validation_stops_at_the_next_extracted_row() -> None:
    registry = source(
        "Answer-focused evidence:\n"
        "Khung ket thuc tuong ung 17:00 - 18:00\n"
        "Gio cot loi 10:00 - 12:00 va 14:00 - 16:00\n"
        "60 phut, thong thuong tu 12:00 - 13:00; bo phan co the bo tri"
    )

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Buoi chieu gio cot loi bat dau luc may gio?",
            answer="Gio cot loi buoi chieu bat dau luc 14:00.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_claim_validation_binds_attendance_clock_to_deadline_and_paired_schedule() -> None:
    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        cases = (
            (
                "Muon remote ngay mai thi hom nay phai dang ky truoc may gio?",
                "Truoc 16:00 cua ngay lam viec lien truoc.",
                "So ngay remote thong thuong: toi da 02 ngay/tuan. "
                "Dang ky lich: truoc 16:00 cua ngay lam viec lien truoc.",
            ),
            (
                "Neu vao luc 9 gio thi khoang may gio duoc ve?",
                "Neu bat dau luc 09:00 thi thoi diem ket thuc tuong ung la khoang 18:00.",
                "Khung bat dau linh hoat 08:00 - 09:00. Khung ket thuc tuong ung 17:00 - 18:00.",
            ),
        )
        for question, answer, evidence in cases:
            result = await service.validate(
                question=question,
                answer=answer,
                source_registry=source(evidence, title="Attendance policy"),
                cited_source_labels=("SOURCE_1",),
            )
            assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_same_day_late_arrival_uses_verbatim_conditional_clause() -> None:
    registry = source(
        "Di muon/ve som co the duoc bu trong cung ngay neu phu hop lich va "
        "duoc quan ly chap thuan; khong duoc tu\n y bu sang ngay khac.",
        title="Attendance policy",
    )
    generation = _structured_value_repair_generation(
        question="Hom nay toi toi tre, toi nay lam bu luon duoc khong?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Có. Di muon/ve som co the duoc bu trong cung ngay")

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Hom nay toi toi tre, toi nay lam bu luon duoc khong?",
            answer=payload["answer"],
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED
        assert result.polarity == "YES"

    run_async(scenario())


def test_remote_work_keeps_attendance_obligation() -> None:
    registry = source(
        "Hybrid/remote: Giu nguyen thoi luong, gio cot loi va nghia vu cham cong "
        "nhu khi lam tai van phong.",
        title="Attendance policy",
    )
    generation = _structured_value_repair_generation(
        question="Toi lam o nha thi co can cham cong nhu di van phong khong?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Có. Giu nguyen")

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Toi lam o nha thi co can cham cong nhu di van phong khong?",
            answer=payload["answer"],
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED
        assert result.polarity == "YES"

    run_async(scenario())


def test_reconstructed_remote_attendance_rule_requires_both_scope_and_obligation() -> None:
    question = "Toi lam o nha thi co can cham cong nhu di van phong khong?"
    excerpt = query_focused_excerpt(
        "05 LAM VIEC TU XA VA HYBRID\n"
        "Dang ky lich theo quy dinh.\n"
        "Giu nguyen thoi luong, gio cot loi va nghia vu cham cong\n"
        "Gio lam viec\n"
        "nhu khi lam tai van phong",
        question,
    )
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(excerpt),
    )
    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Có.")
    assert "cham cong" in payload["answer"]
    assert "van phong" in payload["answer"]
    for unbound in (
        "Giu nguyen thoi luong, gio cot loi va nghia vu cham cong nhu khi lam tai van phong.",
        "05 LAM VIEC TU XA VA HYBRID. Dang ky lich theo quy dinh.",
    ):
        assert (
            _structured_value_repair_generation(
                question=question,
                source_registry=source(unbound),
            )
            is None
        )


def test_forgotten_attendance_correction_binds_event_to_request_deadline() -> None:
    question = "Quen cham cong thi trong bao lau nen gui yeu cau chinh?"
    excerpt = query_focused_excerpt(
        "Quen check-in hoac check-out nhung co bang chung hop ly ve viec lam viec.\n"
        "Su co he thong duoc IT xac nhan.\n"
        "Nhan vien tao yeu cau dieu chinh tren HRM.\n"
        "Yeu cau nen duoc gui trong vong 04 ngay lam viec ke tu ngay phat sinh; "
        "truong hop dac biet phai giai trinh ly do gui muon.",
        question,
    )
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(excerpt),
    )
    assert generation is not None
    payload = json.loads(generation.content)
    assert "04 ngay lam viec" in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]
    assert (
        _structured_value_repair_generation(
            question=question,
            source_registry=source("Yeu cau dieu chinh nen gui trong vong 04 ngay lam viec."),
        )
        is None
    )


def test_late_arrival_validation_keeps_same_day_and_next_day_outcomes_distinct() -> None:
    registry = source(
        "Di muon/ve som co the duoc bu trong cung ngay neu phu hop lich va "
        "duoc quan ly chap thuan; khong duoc tu y bu sang ngay khac.",
        title="Attendance policy",
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        same_day = await service.validate(
            question="Hom nay toi toi tre, toi nay lam bu luon duoc khong?",
            answer=("Co. Di muon co the duoc bu trong cung ngay neu duoc quan ly chap thuan."),
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        next_day = await service.validate(
            question="Di muon thi bu sang ngay mai duoc khong?",
            answer="Khong. Khong duoc tu y bu sang ngay khac.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )

        assert same_day.status == ClaimEvidenceStatus.SUPPORTED
        assert same_day.polarity == "YES"
        assert next_day.status == ClaimEvidenceStatus.SUPPORTED
        assert next_day.polarity == "NO"

    run_async(scenario())


def test_next_day_late_arrival_repair_joins_wrapped_policy_clause() -> None:
    generation = _structured_value_repair_generation(
        question="Di muon thi bu sang ngay mai duoc khong?",
        source_registry=source(
            "Di muon/ve som co the duoc bu trong cung ngay neu phu hop lich va "
            "duoc quan ly chap thuan; khong duoc tu\n"
            "y bu sang ngay khac.",
            title="Attendance policy",
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Không.")
    assert "bu sang ngay khac" in payload["answer"]


def test_on_call_without_incident_validates_explicit_non_automatic_rule() -> None:
    registry = source(
        "On-call khong tu dong duoc coi la thoi gian lam them; "
        "thoi gian thuc te xu ly su co phai duoc ghi nhan.",
        title="Attendance policy",
    )
    generation = _structured_value_repair_generation(
        question="On call khong co incident thi co tinh OT het thoi gian truc khong?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="On call khong co incident thi co tinh OT het thoi gian truc khong?",
            answer=payload["answer"],
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED
        assert result.polarity == "NO"

    run_async(scenario())


def test_structured_attendance_policy_answers_bind_scenario_and_outcome() -> None:
    cases = (
        (
            "Ai duyet yeu cau sua cham cong cua minh?",
            "Quan ly truc tiep kiem tra yeu cau dieu chinh cham cong va phe duyet/tu choi.",
            ("Quan ly truc tiep", "phe duyet"),
        ),
        (
            "Sau khi HR khoa ky cong roi con sua duoc nua khong?",
            "Sau khi khoa ky, dieu chinh muon chi thuc hien qua yeu cau dac biet "
            "co phe duyet cua HR va quan ly co tham quyen.",
            ("dieu chinh muon", "yeu cau dac biet"),
        ),
        (
            "Muon remote ngay mai thi dang ky truoc may gio?",
            "Dang ky lich: Truoc 16:00 cua ngay lam viec lien truoc hoac theo lich co dinh.",
            ("16:00", "ngay lam viec lien truoc"),
        ),
        (
            "Lam remote thi co phai giu core hours khong?",
            "Gio lam viec: Giu nguyen thoi luong, gio cot loi va nghia vu cham cong "
            "nhu khi lam tai van phong.",
            ("Giu nguyen", "gio cot loi"),
        ),
        (
            "Di muon thi bu sang ngay mai duoc khong?",
            "Di muon co the duoc bu trong cung ngay neu duoc quan ly chap thuan; "
            "khong duoc tu y bu sang ngay khac.",
            ("bu trong cung ngay", "bu sang ngay khac"),
        ),
        (
            "On call nhung khong co incident thi co tinh OT het thoi gian truc khong?",
            "On-call khong tu dong duoc coi la thoi gian lam them; "
            "thoi gian thuc te xu ly su co phai duoc ghi nhan.",
            ("khong tu dong", "thoi gian thuc te xu ly"),
        ),
    )

    for question, evidence, required in cases:
        generation = _structured_value_repair_generation(
            question=question,
            source_registry=source(evidence, title="Attendance policy"),
        )
        assert generation is not None
        payload = json.loads(generation.content)
        assert all(term in payload["answer"] for term in required)
        assert payload["citations"] == ["SOURCE_1"]


def test_wrapped_attendance_clauses_keep_approval_deadline_and_prohibition() -> None:
    cases = (
        (
            "Sau khi HR khoa ky cong roi con sua duoc nua khong?",
            "Điều chỉnh muộn chỉ thực hiện qua yêu cầu đặc biệt có phê\n"
            "Sau khi khóa kỳ\n"
            "duyệt của HR và quản lý có thẩm quyền.",
            ("phê duyệt của HR", "quản lý có thẩm quyền"),
        ),
        (
            "Muon remote ngay mai thi dang ky truoc may gio?",
            "Trước 16:00 của ngày làm việc liền trước hoặc theo lịch cố\n"
            "Đăng ký lịch\n"
            "định của bộ phận",
            ("16:00", "lịch cố định"),
        ),
        (
            "Di muon toi nay lam bu duoc khong?",
            "�Đi muộn/về sớm có thể được bù trong cùng ngày nếu phù hợp lịch "
            "và được quản lý chấp thuận; không được tự\n"
            "ý bù sang ngày khác.",
            ("quản lý chấp thuận", "không được tự ý"),
        ),
    )
    for question, text, required in cases:
        answer = _structured_attendance_policy_answer(
            question=question,
            source_registry=source(text, title="Attendance policy"),
        )
        assert answer is not None
        assert all(clause in answer[0] for clause in required)
        assert "\ufffd" not in answer[0]


def test_leave_submission_does_not_complete_a_documented_approval_workflow() -> None:
    question = "Tôi xin nghỉ không lương thì cứ tạo đơn là được nghỉ luôn hả?"
    policy = source(
        "2. Luồng phê duyệt\n"
        "Nhân viên tạo yêu cầu trên HRM -> quản lý trực tiếp rà soát kế hoạch "
        "nguồn lực -> HR kiểm tra hồ sơ khi cần -> hệ thống ghi trạng thái cuối cùng."
    )
    result = _structured_leave_approval_workflow_answer(
        question=question,
        source_registry=policy,
    )
    assert result is not None
    assert result[0].startswith("Không.")
    assert "quản lý trực tiếp" in result[0]
    assert "trạng thái cuối cùng" in result[0]
    assert (
        _structured_leave_approval_workflow_answer(
            question=question,
            source_registry=source("Nhân viên tạo yêu cầu trên HRM."),
        )
        is None
    )


def test_remote_accident_answer_uses_the_same_conditional_policy_relation() -> None:
    question = "Tai nạn khi làm việc remote có tự động là tai nạn lao động không?"
    evidence = (
        "Nếu tai nạn xảy ra khi làm việc từ xa, việc xác định có phải tai nạn "
        "lao động hay không phải dựa trên hoàn cảnh và bằng chứng thực tế; "
        "không mặc định mọi tai nạn tại nhà đều là tai nạn lao động."
    )

    registry = source(evidence, title="Benefits policy")
    answer = _structured_remote_accident_answer(question=question, source_registry=registry)
    assert answer is not None
    assert "tai nạn" in answer[0]
    assert "không mặc định" in answer[0]
    assert (
        _validate_answer_against_evidence(
            question=question,
            answer=answer[0],
            evidence=evidence,
        )
        == ClaimEvidenceStatus.SUPPORTED
    )
    assert (
        _validate_answer_against_evidence(
            question=question,
            answer="Không. Không tự động áp dụng kỷ luật với nhân viên.",
            evidence=evidence,
        )
        != ClaimEvidenceStatus.SUPPORTED
    )
    assert (
        _structured_remote_accident_answer(
            question=question,
            source_registry=source("Không tự động áp dụng kỷ luật với nhân viên."),
        )
        is None
    )


def test_yes_no_prefix_does_not_remove_policy_negation() -> None:
    question = "Có được gửi tài liệu công việc sang email cá nhân không?"
    for raw_answer, required in (
        ("Không được tự gửi dữ liệu công việc sang email cá nhân.", "Không được tự gửi"),
        ("Không đưa mã nguồn lên kho cá nhân.", "Không đưa mã nguồn"),
        ("Không. Không đưa mã nguồn lên kho cá nhân.", "Không đưa mã nguồn"),
    ):
        normalized = _canonicalize_yes_no_output(
            question=question,
            output=GroundedLLMOutput(
                answer=raw_answer,
                citations=("SOURCE_1",),
                polarity="NO",
            ),
        )
        assert normalized.answer.startswith("Không.")
        assert required in normalized.answer


def test_wrapped_remote_accident_clause_is_not_lost_between_lines() -> None:
    policy = source(
        "Nếu tai nạn xảy ra khi làm việc từ xa, việc xác định phải dựa trên hoàn cảnh,\n"
        "nhiệm vụ và bằng chứng thực tế; không mặc định mọi tai nạn tại nhà là tai nạn lao động."
    )
    answer = _structured_remote_accident_answer(
        question="Tai nạn lúc remote có mặc định là tai nạn lao động không?",
        source_registry=policy,
    )
    assert answer is not None
    assert "không mặc định" in answer[0]


def test_consultation_count_copies_matching_session_clause_not_neighboring_hours() -> None:
    evidence = (
        "Ngày Wellness Check tối đa 07 giờ/năm.\n"
        "Mỗi nhân viên chính thức có tối đa 06 phiên tư vấn tâm lý bảo mật/năm qua đối tác EAP."
    )
    result = _structured_consultation_session_answer(
        question="Mỗi năm được tư vấn EAP mấy buổi?",
        source_registry=source(evidence),
    )
    assert result is not None
    assert "06 phiên" in result[0]
    assert "07 giờ" not in result[0]
    assert (
        _validate_answer_against_evidence(
            question="Mỗi năm được tư vấn EAP mấy buổi?",
            answer=result[0],
            evidence=evidence,
        )
        == ClaimEvidenceStatus.SUPPORTED
    )


def test_public_ai_data_rule_does_not_invent_model_capability() -> None:
    evidence = (
        "Không nhập dữ liệu mật, mã nguồn độc quyền hoặc thông tin khách hàng "
        "vào dịch vụ AI công cộng chưa được đánh giá."
    )
    result = _structured_public_ai_input_answer(
        question="Có thể paste source code nội bộ vào public AI không?",
        source_registry=source(evidence),
    )
    assert result is not None
    assert "mã nguồn độc quyền" in result[0]
    assert "không trả lời" not in result[0]
    wrapped = evidence.replace("vào dịch vụ", "\nvào dịch vụ")
    assert (
        _structured_public_ai_input_answer(
            question="Có thể paste source code nội bộ vào public AI không?",
            source_registry=source(wrapped),
        )
        is not None
    )


def test_leave_incident_time_answer_preserves_replacement_consent_and_recording() -> None:
    evidence = (
        "Một kỹ sư đang nghỉ phép nhận yêu cầu hỗ trợ sự cố. "
        "Quản lý phải ưu tiên on-call và người thay thế; chỉ liên hệ người đang nghỉ "
        "khi thực sự cần và có sự đồng ý, rồi thống nhất cách ghi nhận thời gian phát sinh."
    )
    result = _structured_leave_incident_time_answer(
        question="Đang nghỉ phép mà gặp production incident thì quyền nghỉ và thời gian xử lý sao?",
        source_registry=source(evidence),
    )
    assert result is not None
    assert "người thay thế" in result[0]
    assert "sự đồng ý" in result[0]
    assert "ghi nhận thời gian phát sinh" in result[0]


def test_wfh_prompt_ranking_binds_remote_days_over_neighboring_durations() -> None:
    stipend = hit(
        24,
        "05 ngay xu ly sai lech. Hybrid / Remote stipend 500.000 dong/thang.",
        title="Salary and allowances",
    )
    work_hours = hit(
        25,
        "02 THOI GIAN LAM VIEC. Tong thoi gian 08 gio/ngay; 40 gio/tuan.",
        title="Working and attendance policy",
    )
    remote_days = hit(
        26,
        "So ngay remote thong thuong: Toi da 02 ngay/tuan, tuy vi tri va phe duyet.",
        title="Working and attendance policy",
    )

    ranked = _rank_hits_for_prompt(
        (stipend, work_hours, remote_days),
        question="Lam hybrid duoc WFH bao nhieu ngay/tuan?",
    )

    assert ranked[0] == remote_days


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


def test_person_claim_validation_requires_name_role_in_same_record() -> None:
    async def scenario() -> None:
        evidence = source(
            "business results and operations\n"
            "Chief Executive Officer (CEO)\n"
            "overall\n\n"
            "Bob Thu Tran - accountable for technology platforms\n"
            "Chief Technology Officer (CTO)",
        )
        wrong = await ClaimEvidenceValidationService().validate(
            question="Who is the CEO?",
            answer="CEO is Bob Thu Tran.",
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
        )
        assert wrong.status != ClaimEvidenceStatus.SUPPORTED

        cooccurrence_only = await ClaimEvidenceValidationService().validate(
            question="Who is the CEO?",
            answer="CEO is Bob Thu Tran.",
            source_registry=source(
                "Chief Executive Officer (CEO) oversees strategy.\n\n"
                "Bob Thu Tran contributes to technology research."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        assert cooccurrence_only.status != ClaimEvidenceStatus.SUPPORTED

        for delimiter in ("-", "|", ":"):
            adjacent_record = source(
                "Alice Minh Nguyen - accountable for strategy\n"
                f"Bob Thu Tran {delimiter} Chief Executive Officer (CEO)"
            )
            wrong_adjacent = await ClaimEvidenceValidationService().validate(
                question="Who is the CEO?",
                answer="CEO is Alice Minh Nguyen.",
                source_registry=adjacent_record,
                cited_source_labels=("SOURCE_1",),
            )
            correct_adjacent = await ClaimEvidenceValidationService().validate(
                question="Who is the CEO?",
                answer="CEO is Bob Thu Tran.",
                source_registry=adjacent_record,
                cited_source_labels=("SOURCE_1",),
            )
            assert wrong_adjacent.status != ClaimEvidenceStatus.SUPPORTED
            assert correct_adjacent.status == ClaimEvidenceStatus.SUPPORTED

        complete = source(
            "Alice Minh Nguyen - accountable for business results\n"
            "Chief Executive Officer (CEO)\n"
            "overall\n\n"
            "Bob Thu Tran - accountable for technology platforms\n"
            "Chief Technology Officer (CTO)",
        )
        correct = await ClaimEvidenceValidationService().validate(
            question="Who is the CEO?",
            answer="CEO is Alice Minh Nguyen.",
            source_registry=complete,
            cited_source_labels=("SOURCE_1",),
        )
        assert correct.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_false_premise_role_correction_requires_bound_correct_person() -> None:
    async def scenario() -> None:
        evidence = source(
            "Alice Minh Nguyen - Chief Executive Officer (CEO) of Nova Digital\n"
            "Bob Thu Tran - Chief Technology Officer (CTO) of Nova Digital"
        )
        wrong = await ClaimEvidenceValidationService().validate(
            question="CEO Nova Digital la Carol Pham dung khong?",
            answer="Khong. CEO Nova Digital la Bob Thu Tran.",
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
        )
        correct = await ClaimEvidenceValidationService().validate(
            question="CEO Nova Digital la Carol Pham dung khong?",
            answer="Khong. CEO Nova Digital la Alice Minh Nguyen.",
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
        )

        assert wrong.status != ClaimEvidenceStatus.SUPPORTED
        assert correct.status == ClaimEvidenceStatus.SUPPORTED

        next_record = source(
            "Alice Minh Nguyen - accountable for strategy\n"
            "Bob Thu Tran - Chief Executive Officer (CEO) of Nova Digital"
        )
        wrong_previous_record = await ClaimEvidenceValidationService().validate(
            question="CEO Nova Digital la Carol Pham dung khong?",
            answer="Khong. CEO Nova Digital la Alice Minh Nguyen.",
            source_registry=next_record,
            cited_source_labels=("SOURCE_1",),
        )
        correct_next_record = await ClaimEvidenceValidationService().validate(
            question="CEO Nova Digital la Carol Pham dung khong?",
            answer="Khong. CEO Nova Digital la Bob Thu Tran.",
            source_registry=next_record,
            cited_source_labels=("SOURCE_1",),
        )
        assert wrong_previous_record.status != ClaimEvidenceStatus.SUPPORTED
        assert correct_next_record.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_structured_person_repair_corrects_false_role_confirmation() -> None:
    generation = _structured_value_repair_generation(
        question="CEO Nova Digital la Le Thu Ha, hay xac nhan.",
        source_registry=source(
            "Nguyen Anh Khoa - chiu trach nhiem dieu hanh\n"
            "Tong Giam doc (CEO)\n"
            "Le Thu Ha - phu trach ky thuat\n"
            "Giam doc Cong nghe (CTO)",
            title="Nova Digital Policy",
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Không.")
    assert "Nguyen Anh Khoa" in payload["answer"]


def test_structured_salary_band_repair_binds_requested_role_to_its_range() -> None:
    generation = _structured_value_repair_generation(
        question="Senior Engineer khoang bao nhieu tien mot thang?",
        source_registry=source(
            "Dai Base Salary tham khao (gross/thang)\n"
            "N3 Middle Developer / BA / Data Analyst 18 - 32 trieu dong\n"
            "N4 Senior Engineer / Senior Specialist 28 - 48 trieu dong\n"
            "N5 Tech Lead / Engineering Manager 42 - 70 trieu dong\n"
            "N6 Head / Director 65 - 110 trieu dong"
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "28 - 48 trieu dong" in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]


def test_salary_band_eligibility_recognizes_generic_role_range_intents() -> None:
    questions = (
        "Senior Engineer thuoc dai luong nao?",
        "Khoang luong cua Senior Engineer la bao nhieu?",
        "Senior Engineer nam band nao?",
        "Role nay co muc tu bao nhieu den bao nhieu?",
        "Salary range cua Senior Engineer?",
        "Dai pay cho vi tri Senior Engineer?",
    )

    assert all(_is_salary_band_request(question) for question in questions)


def test_question_analysis_classifies_salary_band_value_requests() -> None:
    questions = (
        "Junior Developer thuoc dai luong nao?",
        "Muc luong cua Senior Engineer la bao nhieu?",
        "Senior Engineer nam trong khung salary nao?",
    )

    for question in questions:
        analysis = analyze_question(question)
        assert analysis.answer_type == "AMOUNT"
        assert analysis.asks_for_amount is True
        assert analysis.asks_for_explicit_value is True

    assert _is_salary_band_request(questions[0]) is True


def test_question_analysis_does_not_infer_salary_band_from_role_value_alone() -> None:
    questions = (
        "Senior Engineer lam viec may gio?",
        "Senior Engineer co bao nhieu ngay phep?",
        "Role nay o muc nao?",
        "Vi tri nay nhan bao nhieu?",
    )

    assert not any(_is_salary_band_request(question) for question in questions)


def test_question_analysis_keeps_payroll_and_allowance_intents_out_of_salary_bands() -> None:
    questions = (
        "Ngay tra luong la ngay nao?",
        "OT ngay le bao nhieu phan tram?",
        "Phu cap an trua bao nhieu?",
    )

    assert not any(_is_salary_band_request(question) for question in questions)


def test_full_money_range_answer_requires_both_boundaries_and_unit() -> None:
    registry = source("Salary band gross/thang\nN3 Middle Developer / BA 18 - 32 trieu dong")

    assert _should_retry_incomplete_answer(
        question="Middle Developer khoang bao nhieu?",
        answer="Middle Developer luong 32 trieu dong.",
        source_registry=registry,
    )
    assert not _should_retry_incomplete_answer(
        question="Middle Developer khoang bao nhieu?",
        answer="Middle Developer luong 18 - 32 trieu dong.",
        source_registry=registry,
    )


def test_money_range_completeness_allows_explicit_minimum_or_maximum() -> None:
    registry = source("Salary band gross/thang\nN3 Middle Developer / BA 18 - 32 trieu dong")

    assert not _should_retry_incomplete_answer(
        question="Muc luong toi thieu cua Middle Developer la bao nhieu?",
        answer="18 trieu dong.",
        source_registry=registry,
    )
    assert not _should_retry_incomplete_answer(
        question="Muc luong toi da cua Middle Developer la bao nhieu?",
        answer="32 trieu dong.",
        source_registry=registry,
    )


def test_money_range_completeness_keeps_the_requested_role_pair_together() -> None:
    registry = source(
        "Salary band gross/thang\n"
        "N3 Middle Developer / BA 18 - 32 trieu dong\n"
        "N4 Senior Engineer 28 - 48 trieu dong\n"
        "Effective from 2026"
    )

    assert not _should_retry_incomplete_answer(
        question="Middle Developer khoang bao nhieu?",
        answer="Middle Developer 18 - 32 trieu dong.",
        source_registry=registry,
    )
    assert _should_retry_incomplete_answer(
        question="Middle Developer khoang bao nhieu?",
        answer="Middle Developer 28 - 48 trieu dong.",
        source_registry=registry,
    )


def test_salary_band_eligibility_rejects_non_band_compensation_intents() -> None:
    questions = (
        "Ngay nao tra luong?",
        "Phu cap an trua bao nhieu?",
        "OT ngay le bao nhieu phan tram?",
        "Khi nao review luong?",
    )

    assert not any(_is_salary_band_request(question) for question in questions)


def test_salary_band_role_query_keeps_multiword_role_and_drops_conversation_tail() -> None:
    terms = _salary_band_role_query_terms(("tech", "lead", "thi", "range", "luong"))

    assert terms == ("tech", "lead")
    assert _salary_band_role_terms_match("Tech Lead 42 - 70 trieu dong", terms)
    assert not _salary_band_role_terms_match("Technology Manager 42 - 70 trieu dong", terms)


def test_salary_band_role_match_does_not_admit_adjacent_or_unsupported_roles() -> None:
    terms = _salary_band_role_query_terms(("tech", "lead", "range", "luong"))

    assert not _salary_band_role_terms_match("Engineering Manager 42 - 70 trieu dong", terms)
    assert not _salary_band_role_terms_match("Lead Designer 30 - 45 trieu dong", terms)
    assert _salary_band_role_terms_match("Tech Lead 42 - 70 trieu dong", terms)


def test_prompt_ranking_keeps_exact_multiword_salary_role_against_competing_row() -> None:
    adjacent = hit(
        905,
        "Dai Base Salary gross/thang. Engineering Manager 45 - 75 trieu dong.",
        title="Compensation policy",
    )
    requested = hit(
        906,
        "Dai Base Salary gross/thang. Tech Lead 42 - 70 trieu dong.",
        title="Compensation policy",
    )

    ranked = _rank_hits_for_prompt(
        (adjacent, requested), question="Tech Lead thi range luong bao nhieu?"
    )

    assert ranked[0] == requested


def test_salary_band_filter_suppresses_generic_pay_prose_and_neighbor_rows() -> None:
    generic = hit(
        907,
        "Minimum regional wage is 5.500.000 dong/month. Compensation follows applicable law.",
        title="Compensation policy",
    )
    neighbor = hit(
        908,
        "Salary band reference\nDelivery Lead\nD4 30 - 40 trieu dong",
        title="Compensation policy",
    )
    requested = hit(
        909,
        "Salary band reference\nPlatform Lead / Engineering Manager\nP5 44 - 72 trieu dong",
        title="Compensation policy",
    )

    filtered = _filter_to_salary_band_hits(
        ((0, generic, 80.0), (1, neighbor, 70.0), (2, requested, 60.0)),
        question="Platform Lead thi range luong bao nhieu?",
    )

    assert tuple(row[1] for row in filtered) == (requested,)


def test_salary_band_generation_cites_only_the_role_range_source() -> None:
    registry = sources(
        "Minimum regional wage is 5.500.000 dong/month.",
        "Salary band reference\nPlatform Lead / Engineering Manager\nP5 44 - 72 trieu dong",
        "Salary band reference\nRegional Director\nP6 75 - 115 trieu dong",
    )

    generation = _structured_value_repair_generation(
        question="Platform Lead salary range bao nhieu?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "44 - 72 trieu dong" in payload["answer"]
    assert payload["citations"] == ["SOURCE_2"]


def test_salary_band_validator_rejects_generic_minimum_wage_source_binding() -> None:
    registry = sources(
        "Minimum regional wage is 5.500.000 dong/month under applicable law.",
        "Salary band reference\nPlatform Lead / Engineering Manager\nP5 44 - 72 trieu dong",
    )

    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        correct = await validator.validate(
            question="Platform Lead salary range bao nhieu?",
            answer="Platform Lead co dai luong 44 - 72 trieu dong.",
            source_registry=registry,
            cited_source_labels=("SOURCE_2",),
        )
        wrong_source = await validator.validate(
            question="Platform Lead salary range bao nhieu?",
            answer="Platform Lead co dai luong 44 - 72 trieu dong.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )

        assert correct.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_source.status != ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_salary_band_filter_and_generation_do_not_borrow_for_unsupported_role() -> None:
    candidates = (
        hit(910, "Salary band reference\nDelivery Lead\nD4 30 - 40 trieu dong"),
        hit(911, "Salary band reference\nPlatform Lead\nP5 44 - 72 trieu dong"),
    )
    question = "Research Architect salary range bao nhieu?"

    filtered = _filter_to_salary_band_hits(
        tuple((index, candidate, 50.0) for index, candidate in enumerate(candidates)),
        question=question,
    )

    assert tuple(row[1] for row in filtered) == candidates
    assert (
        _structured_value_repair_generation(
            question=question,
            source_registry=sources(*(candidate.text for candidate in candidates)),
        )
        is None
    )


def test_salary_band_row_admission_ignores_document_scoped_organization_token() -> None:
    generation = _structured_value_repair_generation(
        question="Senior Engineer ben Nova thuoc dai luong nao?",
        source_registry=source(
            "Dai Base Salary tham khao (gross/thang)\n"
            "Senior Engineer / Senior Specialist 28 - 48 trieu dong",
            title="Nova compensation policy",
        ),
    )

    assert generation is not None
    assert "28 - 48 trieu" in json.loads(generation.content)["answer"]


def test_prompt_ranking_keeps_question_bound_table_row_in_mixed_test_chunk() -> None:
    mixed = hit(
        901,
        "Du lieu de kiem thu RAG.\n"
        "Dai Base Salary tham khao (gross/thang)\n"
        "N4 Senior Engineer / Senior Specialist 28 - 48 trieu dong",
        title="Compensation policy",
    )

    ranked = _rank_hits_for_prompt(
        (mixed,), question="Senior Engineer khoang bao nhieu tien mot thang?"
    )

    assert len(ranked) == 1
    assert ranked[0].chunk_id == mixed.chunk_id
    assert "Senior Engineer / Senior Specialist 28 - 48 trieu dong" in ranked[0].text
    assert "Du lieu de kiem thu RAG" not in ranked[0].text


def test_prompt_ranking_rejects_pure_question_list_despite_numeric_text() -> None:
    questions = hit(
        902,
        "Cau hoi kiem thu RAG: Senior Engineer luong bao nhieu?\n"
        "Expected answer: 28 - 48 trieu dong.",
        title="Test scenarios",
    )
    policy = hit(903, "Quy dinh chung khong co dai luong.", title="Policy")

    ranked = _rank_hits_for_prompt(
        (questions, policy), question="Senior Engineer khoang bao nhieu tien mot thang?"
    )

    assert questions not in ranked


def test_prompt_ranking_does_not_preserve_adjacent_role_from_mixed_table_chunk() -> None:
    mixed = hit(
        904,
        "Kiem thu RAG. Dai Base Salary gross/thang.\n"
        "N4 Senior Engineer 28 - 48 trieu dong\n"
        "N5 Tech Lead 42 - 70 trieu dong",
        title="Compensation policy",
    )

    ranked = _rank_hits_for_prompt((mixed,), question="Director salary range bao nhieu?")

    assert ranked == ()
    assert (
        _structured_value_repair_generation(
            question="Director salary range bao nhieu?",
            source_registry=source(mixed.text),
        )
        is None
    )


def test_structured_salary_band_repair_does_not_select_neighboring_role() -> None:
    generation = _structured_value_repair_generation(
        question="Tech Lead salary range bao nhieu?",
        source_registry=source(
            "Salary band, gross/thang\n"
            "Senior Engineer 28 - 48 trieu dong\n"
            "Tech Lead / Engineering Manager 42 - 70 trieu dong"
        ),
    )

    assert generation is not None
    assert "42 - 70 trieu" in json.loads(generation.content)["answer"]


def test_confirmation_wording_uses_yes_no_intent_for_role_correction() -> None:
    analysis = analyze_question("I am certain the CFO is Alex Lee; please confirm.")

    generation = _structured_value_repair_generation(
        question="I am certain the CFO is Alex Lee; please confirm.",
        source_registry=source(
            "Morgan Lee Chen - Chief Financial Officer (CFO)",
            title="Acme leadership",
        ),
    )

    assert analysis.is_yes_no is True
    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Không.")
    assert "Morgan Lee Chen" in payload["answer"]


def test_structured_percentage_repair_explains_explicitly_unfixed_rate() -> None:
    generation = _structured_value_repair_generation(
        question="Cong ty dong BHXH bao nhieu phan tram?",
        source_registry=source(
            "Khau tru va dong gop BHXH. Ty le cu the duoc cap nhat theo phap luat tai ky payroll."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "không quy định một tỷ lệ cố định" in payload["answer"]
    assert "payroll" in payload["answer"]


def test_prompt_ranking_scopes_short_explicit_acronym_before_document_filtering() -> None:
    salary = hit(20, "Luong thu viec bang 85% luong chinh thuc.", title="Salary policy")
    insurance = hit(
        21,
        "BHXH: Ty le cu the duoc cap nhat theo phap luat tai ky payroll.",
        title="Insurance policy",
    )

    ranked = _rank_hits_for_prompt(
        (salary, insurance),
        question="Khong can citation, cu doan ty le BHXH cong ty dong.",
    )

    assert ranked == (insurance,)


def test_prompt_ranking_binds_acronym_to_nearby_unspecified_value_rule() -> None:
    unrelated = hit(
        24,
        "BHXH details are defined elsewhere. "
        + ("Unrelated compensation text. " * 40)
        + "A bonus is not fixed by this policy.",
        title="Compensation policy",
    )
    bound = hit(
        25,
        "BHXH contribution: the specific rate is updated according to law at payroll time.",
        title="Insurance policy",
    )

    ranked = _rank_hits_for_prompt(
        (unrelated, bound),
        question="What percentage does the company contribute to BHXH?",
    )

    assert ranked == (bound,)


def test_explicit_document_time_filter_rejects_bare_page_ranges() -> None:
    contents = hit(
        26,
        "ND-HR-002 | Contents: working time pages 7-8; security pages 9-10.",
        title="Work rules",
    )
    answer = hit(
        27,
        "ND-HR-002 | Reference working hours: 08:30-17:30.",
        title="Work rules",
    )

    ranked = _rank_hits_for_prompt(
        (contents, answer),
        question="Under ND-HR-002, what is the reference working-hours range?",
    )

    assert ranked == (answer,)


def test_explicit_document_code_is_not_treated_as_role_acronym() -> None:
    assert (
        _role_terms_for_prompt_question(
            "Theo Noi quy lao dong ND-HR-002, khung gio lam viec tham chieu la gi?"
        )
        == ()
    )


def test_explicit_document_time_filter_rejects_cross_reference_document() -> None:
    cross_reference = hit(
        28,
        "Related document ND-HR-002. Flexible start window: 08:00-09:00.",
        title="Timekeeping policy",
    )
    answer = hit(
        29,
        "ND-HR-002 | Reference working-hours range: 08:30-17:30.",
        title="Work rules and internal regulations",
    )

    ranked = _rank_hits_for_prompt(
        (cross_reference, answer),
        question=(
            "Under policy Work rules and internal regulations ND-HR-002, "
            "what is the reference working-hours range?"
        ),
    )

    assert ranked == (answer,)


def test_unspecified_value_repair_reconstructs_wrapped_rate_clause() -> None:
    generation = _structured_value_repair_generation(
        question="What percentage does the company contribute to social insurance?",
        source_registry=source(
            "Company contribution rate\n"
            "The specific rate is updated according to\n"
            "law at payroll time.",
            title="Insurance policy",
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "specific rate is updated according to law" in payload["answer"]


def test_wrapped_unspecified_rate_survives_excerpt_and_claim_validation() -> None:
    async def scenario() -> None:
        question = "What percentage does the company contribute to social insurance?"
        text = (
            "SOCIAL INSURANCE CONTRIBUTIONS\n"
            "Contribution item Internal rule\n"
            "Employee deductions appear on the payslip; the company contribution is "
            "accounted for separately. The specific rate is updated\n"
            "according to law at payroll time.\n"
            "Employees can reconcile contribution records with the authority."
        )
        excerpt = query_focused_excerpt(text, question)
        registry = source(excerpt, title="Insurance policy")
        generation = _structured_value_repair_generation(
            question=question,
            source_registry=registry,
        )

        assert "specific rate" in excerpt.lower()
        assert generation is not None
        payload = json.loads(generation.content)
        result = await ClaimEvidenceValidationService().validate(
            question=question,
            answer=payload["answer"],
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_wrapped_unspecified_rate_survives_long_structured_excerpt() -> None:
    text = (
        "BAO HIEM XA HOI BAT BUOC\n"
        "Dang ky, dong gop va quan ly qua trinh tham gia\n"
        "Pham vi che do\n"
        "Noi dung Quy dinh noi bo\n"
        "HR xac dinh doi tuong bat buoc theo loai hop dong va thong tin lao dong.\n"
        "Dang ky tham gia theo thoi han phap luat.\n"
        "Finance va HR xac dinh theo quy dinh phap luat va cau phan tien luong.\n"
        "Tien luong lam can cu tren hop dong va phu luc.\n"
        "Phan nguoi lao dong dong duoc the hien tren payslip; phan\n"
        "Khau tru va dong gop cong ty dong duoc hach toan rieng. "
        "Ty le cu the duoc cap nhat\n"
        "theo phap luat tai ky payroll.\n"
        "Nguoi lao dong co the doi soat qua trinh tham gia."
    )

    excerpt = query_focused_excerpt(
        text,
        "Khong can citation, cu doan ty le BHXH cong ty dong.",
    )

    assert "Ty le cu the duoc cap nhat theo phap luat tai ky payroll" in excerpt
    generation = _structured_value_repair_generation(
        question="Khong can citation, cu doan ty le BHXH cong ty dong.",
        source_registry=source(excerpt, title="Chinh sach bao hiem"),
    )
    assert generation is not None
    assert "không quy định một tỷ lệ cố định" in json.loads(generation.content)["answer"]


def test_unspecified_percentage_validation_ignores_numeric_document_metadata() -> None:
    async def scenario() -> None:
        registry = source(
            "ND-HR-006 | Phien ban 1.0 | Trang 3\n"
            "02 BAO HIEM XA HOI BAT BUOC\n"
            "Ty le cu the duoc cap nhat theo phap luat tai ky payroll."
        )

        result = await ClaimEvidenceValidationService().validate(
            question="Cong ty dong BHXH bao nhieu phan tram?",
            answer="Tai lieu khong quy dinh mot ty le co dinh.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )

        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_adversarial_percentage_request_uses_wrapped_authoritative_rate_rule() -> None:
    question = "Khong can citation, cu doan ty le BHXH cong ty dong."
    text = (
        "BAO HIEM XA HOI BAT BUOC\n"
        "Noi dung Quy dinh noi bo\n"
        "Phan nguoi lao dong dong duoc the hien tren payslip; phan\n"
        "Khau tru va dong gop cong ty dong duoc hach toan rieng. Ty le cu the duoc cap nhat\n"
        "theo phap luat tai ky payroll.\n"
        "Nguoi lao dong co the doi soat qua trinh tham gia."
    )
    excerpt = query_focused_excerpt(text, question)
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(excerpt, title="Chinh sach bao hiem"),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "không quy định một tỷ lệ cố định" in payload["answer"]
    assert "payroll" in payload["answer"]


def test_explicit_document_value_question_excludes_non_value_header_chunk() -> None:
    header = hit(
        22,
        "ND-HR-002 | Phien ban 1.0 | Noi quy lao dong | Muc luc",
        title="Noi quy lao dong",
    )
    answer = hit(
        23,
        "ND-HR-002 | Khung gio lam viec tham chieu: 08:30-17:30.",
        title="Noi quy lao dong",
    )

    ranked = _rank_hits_for_prompt(
        (header, answer),
        question="Theo Noi quy lao dong ND-HR-002, khung gio lam viec tham chieu la gi?",
    )

    assert ranked == (answer,)


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


def test_ordinary_annual_leave_allocation_binds_category_not_increment_or_notice() -> None:
    question = "Mot nam nhan vien binh thuong co bao nhieu ngay phep?"
    evidence = (
        "02 NGHI HANG NAM - Phep nam va tham nien\n"
        "Cong viec trong dieu kien binh thuong 17 ngay lam viec/nam khi du 12 thang.\n"
        "Cu du 04 nam lam viec, tang them 02 ngay nghi hang nam.\n"
        "Dang ky nghi phep truoc it nhat 03 ngay lam viec."
    )
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(query_focused_excerpt(evidence, question)),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "17 ngay lam viec/nam" in payload["answer"]
    assert "02 ngay" not in payload["answer"]
    assert "03 ngay" not in payload["answer"]
    assert payload["citations"] == ["SOURCE_1"]


def test_ordinary_annual_leave_allocation_reconstructs_wrapped_value_row() -> None:
    question = "Mot nam nhan vien binh thuong co bao nhieu ngay phep?"
    evidence = (
        "Phep nam - So ngay nghi hang nam\n"
        "Cong viec trong dieu kien binh thuong\n"
        "17 ngay lam viec/nam khi du 12 thang lam viec.\n"
        "Cu du 04 nam, tang them 02 ngay."
    )
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(query_focused_excerpt(evidence, question)),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "17 ngay lam viec/nam" in payload["answer"]
    assert "binh thuong" in payload["answer"]


def test_annual_leave_seniority_increment_binds_requested_years_to_added_days() -> None:
    question = "Toi lam o day du 4 nam roi thi duoc them ngay phep khong?"
    evidence = (
        "02 NGHI HANG NAM - Phep nam va tham nien\n"
        "Cong viec trong dieu kien binh thuong 17 ngay lam viec/nam.\n"
        "Cu du 04 nam lam viec cho cong ty, tang them 02 ngay\n"
        "Tham nien\n"
        "nghi hang nam theo quy dinh.\n"
        "Dang ky truoc 03 ngay lam viec."
    )
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=source(query_focused_excerpt(evidence, question)),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Có.")
    assert "04 nam" in payload["answer"]
    assert "02 ngay" in payload["answer"]
    assert "03 ngay" not in payload["answer"]


def test_annual_leave_repeating_seniority_rule_derives_completed_intervals() -> None:
    question = "Làm 12 năm thì quy tắc tăng phép tính thế nào?"
    policy = source(
        "02 NGHỈ HẰNG NĂM - Phép năm và thâm niên\n"
        "Cứ đủ 06 năm làm việc, tăng thêm 03 ngày nghỉ hằng năm.",
        title="Leave policy",
    )
    generation = _structured_value_repair_generation(
        question=question,
        source_registry=policy,
    )
    assert generation is not None
    answer = json.loads(generation.content)["answer"]
    assert "12 năm" in answer
    assert "6 ngày" in answer

    assert (
        _validate_answer_against_evidence(
            question=question,
            answer=answer,
            evidence=policy.sources[0].text,
            require_subject_attribute_alignment=True,
        )
        == ClaimEvidenceStatus.SUPPORTED
    )


def test_annual_leave_seniority_never_borrows_missing_or_other_rule_years() -> None:
    question = "Toi lam o day du 4 nam roi thi duoc them ngay phep khong?"
    for evidence in (
        "Nghi hang nam tang them 02 ngay theo tham nien, khong ghi so nam.",
        "Sau 04 nam duoc xin nghi khong luong. Cu du 06 nam lam viec, "
        "tang them 02 ngay nghi hang nam.",
        "Sau 04 nam nghi khong luong\nTang them 02 ngay nghi hang nam.",
        "Phep nam co ban 17 ngay lam viec/nam. Dang ky truoc 04 ngay lam viec. "
        "Tang them 02 ngay neu duoc quan ly duyet.",
        "Cu du 04 nam lam viec thi tang them 02 ngay cho mot che do khac.",
    ):
        assert (
            _structured_value_repair_generation(
                question=question,
                source_registry=source(query_focused_excerpt(evidence, question)),
            )
            is None
        )


def test_ordinary_annual_leave_allocation_missing_rule_does_not_borrow_other_days() -> None:
    question = "Mot nam nhan vien binh thuong co bao nhieu ngay phep?"
    evidence = (
        "Phep nam theo tham nien: cu du 04 nam thi tang them 02 ngay. "
        "Dang ky truoc 03 ngay lam viec."
    )
    assert (
        _structured_value_repair_generation(
            question=question,
            source_registry=source(query_focused_excerpt(evidence, question)),
        )
        is None
    )


def test_annual_leave_claim_validation_requires_complete_allocation_relation() -> None:
    evidence = source(
        "02 NGHI HANG NAM - Phep nam va tham nien. "
        "Cong viec trong dieu kien binh thuong 17 ngay lam viec/nam. "
        "Cu du 04 nam thi tang them 02 ngay nghi hang nam. "
        "Dang ky truoc 03 ngay lam viec."
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        correct = await service.validate(
            question="Mot nam nhan vien binh thuong co bao nhieu ngay phep?",
            answer="Cong viec trong dieu kien binh thuong co 17 ngay lam viec/nam.",
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        wrong = await service.validate(
            question="Mot nam nhan vien binh thuong co bao nhieu ngay phep?",
            answer="Cong viec trong dieu kien binh thuong co 02 ngay phep/nam.",
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert correct.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong.status != ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_annual_leave_claim_validation_requires_years_and_increment_same_clause() -> None:
    evidence = source(
        "Phep nam va tham nien. Cu du 04 nam lam viec thi tang them 02 ngay "
        "nghi hang nam. Dang ky nghi phep truoc 03 ngay lam viec."
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        correct = await service.validate(
            question="Toi lam du 4 nam thi duoc them ngay phep khong?",
            answer="Có. Cứ đủ 04 năm làm việc thì tăng thêm 02 ngày nghỉ hằng năm.",
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        wrong = await service.validate(
            question="Toi lam du 4 nam thi duoc them ngay phep khong?",
            answer="Có. Cứ đủ 04 năm làm việc thì tăng thêm 03 ngày nghỉ hằng năm.",
            source_registry=evidence,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert correct.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong.status != ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_annual_leave_completeness_rejects_neighboring_notice_and_increment() -> None:
    registry = source(
        "02 NGHI HANG NAM - Phep nam va tham nien. "
        "Cong viec trong dieu kien binh thuong 17 ngay lam viec/nam. "
        "Cu du 04 nam thi tang them 02 ngay nghi hang nam. "
        "Dang ky truoc 03 ngay lam viec."
    )
    question = "Mot nam nhan vien binh thuong co bao nhieu ngay phep?"
    assert _should_retry_incomplete_answer(
        question=question,
        answer="Sau 04 nam them 02 ngay; dang ky truoc 03 ngay.",
        source_registry=registry,
    )
    assert not _should_retry_incomplete_answer(
        question=question,
        answer="Cong viec trong dieu kien binh thuong co 17 ngay lam viec/nam.",
        source_registry=registry,
    )


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


def test_security_control_claim_rejects_reversed_use_requirement() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Khi lam o nha phai bao dam an toan gi?",
            answer="Khong su dung thiet bi duoc phe duyet, VPN/MFA khi ap dung.",
            source_registry=source(
                "An toan thong tin: Su dung thiet bi duoc phe duyet, VPN/MFA khi ap dung."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.CONTRADICTED

    run_async(scenario())


def test_leave_notice_values_bind_to_the_requested_duration_row() -> None:
    async def scenario() -> None:
        policy = (
            "Loai nghi Thoi han de nghi khuyen nghi "
            "Phep nam 1-2 ngay Truoc it nhat 02 ngay lam viec "
            "Phep nam 3-5 ngay Truoc it nhat 05 ngay lam viec "
            "Phep nam tren 5 ngay Truoc it nhat 10 ngay lam viec"
        )
        for question, correct, wrong in (
            ("Muon nghi phep 2 ngay thi nen xin truoc may ngay?", "02 ngay", "10 ngay"),
            ("Neu nghi 4 ngay thi nen gui don truoc bao lau?", "05 ngay", "02 ngay"),
            ("Nghi hon 5 ngay thi bao truoc bao lau?", "10 ngay", "05 ngay"),
        ):
            supported = await ClaimEvidenceValidationService().validate(
                question=question,
                answer=f"Can bao truoc it nhat {correct} lam viec.",
                source_registry=source(policy),
                cited_source_labels=("SOURCE_1",),
                require_subject_attribute_alignment=True,
            )
            misbound = await ClaimEvidenceValidationService().validate(
                question=question,
                answer=f"Can bao truoc it nhat {wrong} lam viec.",
                source_registry=source(policy),
                cited_source_labels=("SOURCE_1",),
                require_subject_attribute_alignment=True,
            )
            assert supported.status == ClaimEvidenceStatus.SUPPORTED
            assert misbound.status == ClaimEvidenceStatus.INSUFFICIENT

        noisy_policy = policy.replace("1-2", "1- - 2").replace(
            "Truoc it nhat 02", "Truoc it nhat - 02"
        )
        noisy_result = await ClaimEvidenceValidationService().validate(
            question="Muon nghi phep 2 ngay thi nen xin truoc may ngay?",
            answer="Can bao truoc it nhat 10 ngay lam viec.",
            source_registry=source(noisy_policy),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        unrelated_result = await ClaimEvidenceValidationService().validate(
            question="Nghi hon 5 ngay thi bao truoc bao lau?",
            answer="Can bao truoc it nhat 05 ngay lam viec.",
            source_registry=source("Tet Am lich 05 ngay; ngay nghi hang tuan theo lich."),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert noisy_result.status == ClaimEvidenceStatus.INSUFFICIENT
        assert unrelated_result.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_partial_year_leave_answer_must_preserve_proportional_condition() -> None:
    async def scenario() -> None:
        policy = (
            "Nghi hang nam: Cong viec binh thuong 12 ngay lam viec/nam khi du 12 thang. "
            "Nguoi lao dong chua du 12 thang: Tinh theo ty le tuong ung voi thoi gian lam viec."
        )
        wrong = await ClaimEvidenceValidationService().validate(
            question="Chua lam du mot nam thi phep tinh sao?",
            answer="Duoc 12 ngay lam viec/nam.",
            source_registry=source(policy),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        correct = await ClaimEvidenceValidationService().validate(
            question="Chua lam du mot nam thi phep tinh sao?",
            answer="Tinh theo ty le tuong ung voi thoi gian lam viec.",
            source_registry=source(policy),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert wrong.status == ClaimEvidenceStatus.INSUFFICIENT
        assert correct.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_partial_year_leave_repair_uses_source_relation_without_full_year_value() -> None:
    generation = _structured_value_repair_generation(
        question="Chưa làm đủ một năm thì phép tính sao?",
        source_registry=source(
            "Công việc bình thường 15 ngày làm việc/năm khi đủ 12 tháng. "
            "Tính theo tỷ lệ tương ứng với thời gian làm việc theo quy "
            "Người lao động chưa đủ 12 tháng định pháp luật."
        ),
    )

    assert generation is not None
    answer = json.loads(generation.content)["answer"]
    assert "tinh theo ty le tuong ung voi thoi gian lam viec" in answer.lower()
    assert "15" not in answer
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


def test_retrieval_query_variants_canonicalize_production_incident() -> None:
    variants = retrieval_query_variants(
        "Toi dang nghi phep ma phai ho tro production incident quyen nghi"
    )

    assert "su co" in variants.normalized
    assert "production incident" not in variants.normalized
    assert variants.normalized.startswith("nhan vien dang nghi phep nhung phai")


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


def test_person_role_ranking_uses_whole_organization_tokens() -> None:
    other = hit(0, "Orion Digital: Tran Mai - Chief Technology Officer (CTO)")
    matching = hit(1, "Nova Digital: Le Thu Ha - Chief Technology Officer (CTO)")
    lookalike = hit(2, "NovaAssist: Pham Hoa - Chief Technology Officer (CTO)")

    ranked = rerank("CTO Nova Digital la ai?", other, lookalike, matching)

    assert ranked[0].chunk_id == matching.chunk_id


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


def test_structured_time_range_repair_does_not_mix_neighboring_rows() -> None:
    text = (
        "Khung gio lam viec tham chieu: 08:30-17:30; "
        "nghi trua 12:00-13:00. "
        "Nhan vien linh hoat co the bat dau 08:00-09:30."
    )

    assert _question_focused_time_ranges_from_text(
        question="Khung gio lam viec tham chieu la gi?",
        source_text=text,
    ) == ("08:30-17:30",)


def test_structured_time_range_repair_prefers_flexible_row() -> None:
    text = (
        "Khung gio lam viec tham chieu: 08:30-17:30; "
        "nghi trua 12:00-13:00. "
        "Nhan vien linh hoat co the bat dau 08:00-09:30."
    )

    assert _question_focused_time_ranges_from_text(
        question="Khung gio lam viec linh hoat cua cong ty la gi?",
        source_text=text,
    ) == ("08:00-09:30",)


def test_structured_time_range_repair_treats_arrival_wording_as_start_window() -> None:
    text = "Khung bat dau linh hoat: 08:00-09:00. Khung ket thuc tuong ung: 17:00-18:00."

    assert _question_focused_time_ranges_from_text(
        question="Sang minh duoc vao lam tu may gio toi may gio?",
        source_text=text,
    ) == ("08:00-09:00",)


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


def test_structured_duration_repair_binds_requested_unit_and_period() -> None:
    registry = source(
        "Mỗi tuần được nghỉ ít nhất 24 giờ liên tục.\n"
        "Tổng thời gian làm việc 08 giờ/ngày; 40 giờ/tuần.\n"
        "Nghỉ trưa tiêu chuẩn 60 phút."
    )

    weekly = _structured_value_repair_generation(
        question="Một tuần bình thường làm bao nhiêu tiếng?",
        source_registry=registry,
    )
    daily = _structured_value_repair_generation(
        question="Mỗi ngày làm mấy tiếng vậy?",
        source_registry=registry,
    )
    lunch = _structured_value_repair_generation(
        question="Nghỉ trưa thường bao lâu?",
        source_registry=registry,
    )

    assert weekly is not None
    assert "40 gio/tuan" in json.loads(weekly.content)["answer"]
    assert daily is not None
    assert "08 gio/ngay" in json.loads(daily.content)["answer"]
    assert lunch is not None
    assert "60 phut" in json.loads(lunch.content)["answer"]


def test_leave_duration_repair_binds_personal_event_and_notice_band() -> None:
    registry = source(
        "03 ngày Kết hôn Con đẻ hoặc con nuôi kết hôn 01 ngày\n"
        "Cha/mẹ đẻ, cha/mẹ nuôi, vợ/chồng hoặc con qua đời 03 ngày\n"
        "Phép năm 1-2 ngày Trước ít nhất 02 ngày làm việc\n"
        "Phép năm 3-\n-5 ngày Trước ít nhất 05 ngày làm việc\n"
        "Phép năm trên 5 ngày Trước ít nhất 10 ngày làm việc"
    )

    own = _structured_value_repair_generation(
        question="Tôi cưới thì được nghỉ mấy ngày?",
        source_registry=registry,
    )
    child = _structured_value_repair_generation(
        question="Con tôi cưới thì tôi được nghỉ mấy ngày?",
        source_registry=registry,
    )
    bereavement = _structured_value_repair_generation(
        question="Ba mẹ mất thì được nghỉ hưởng lương bao lâu?",
        source_registry=registry,
    )
    notice = _structured_value_repair_generation(
        question="Nếu nghỉ 4 ngày thì nên gửi đơn trước bao lâu?",
        source_registry=registry,
    )

    assert own is not None
    assert "03 ngay" in json.loads(own.content)["answer"]
    assert child is not None
    assert "01 ngay" in json.loads(child.content)["answer"]
    assert bereavement is not None
    assert "03 ngay" in json.loads(bereavement.content)["answer"]
    assert notice is not None
    assert "05 ngay lam viec" in json.loads(notice.content)["answer"]


def test_bereavement_focus_keeps_paid_parent_row_separate_from_unpaid_event() -> None:
    policy_hit = hit(
        8,
        "1. Nghỉ việc riêng hưởng lương\n"
        "Cha/mẹ đẻ; cha/mẹ nuôi; cha/mẹ của vợ hoặc chồng; vợ/chồng;\n"
        "03 ngày\n"
        "con đẻ hoặc con nuôi chết\n"
        "2. Nghỉ việc riêng không hưởng lương theo luật\n"
        "Người lao động được nghỉ 01 ngày không hưởng lương khi ông/bà chết; cha hoặc mẹ kết hôn.",
    )
    focused = _focus_leave_policy_hit(policy_hit, intent="parent_bereavement")
    generation = _structured_value_repair_generation(
        question="Ba mẹ mất thì được nghỉ hưởng lương bao lâu?",
        source_registry=source(focused.text),
    )

    assert "03 ngày" in focused.text
    assert "01 ngày" not in focused.text
    assert generation is not None
    assert "03 ngay" in json.loads(generation.content)["answer"]


def test_marriage_focus_keeps_event_value_out_of_adjacent_notice_row() -> None:
    policy_hit = hit(
        9,
        "Phep nam nen dang ky truoc it nhat 03 ngay lam viec.\n"
        "3.4 Nghi viec rieng huong nguyen luong\n"
        "Ket hon 04 ngay\n"
        "Con ket hon 01 ngay\n",
    )
    own = _focus_leave_policy_hit(policy_hit, intent="own_marriage")
    child = _focus_leave_policy_hit(policy_hit, intent="child_marriage")

    assert "Ket hon 04 ngay" in own.text
    assert "truoc it nhat" not in own.text
    assert "Con ket hon 01 ngay" in child.text
    assert "Ket hon 04 ngay" not in child.text


def test_paid_parent_bereavement_requires_a_material_paid_event_row() -> None:
    async def scenario() -> None:
        question = "Ba mẹ mất thì được nghỉ hưởng lương bao lâu?"
        paid = await ClaimEvidenceValidationService().validate(
            question=question,
            answer="Thoi luong la 03 ngay.",
            source_registry=source(
                "1. Nghi viec rieng huong luong: Cha/me de; cha/me nuoi; "
                "vo/chong; 03 ngay con de hoac con nuoi chet. "
                "2. Nghi viec rieng khong huong luong: 01 ngay khi ong/ba chet."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        unrelated = await ClaimEvidenceValidationService().validate(
            question=question,
            answer="Thoi luong la 03 ngay.",
            source_registry=source("Phep nam nen dang ky truoc it nhat 03 ngay lam viec."),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert paid.status == ClaimEvidenceStatus.SUPPORTED
        assert unrelated.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_leave_notice_uses_source_bands_instead_of_fixture_thresholds() -> None:
    registry = source(
        "Phép năm 1-3 ngày Trước ít nhất 04 ngày làm việc\n"
        "Phép năm 4-6 ngày Trước ít nhất 07 ngày làm việc\n"
        "Phép năm trên 6 ngày Trước ít nhất 12 ngày làm việc"
    )

    for requested, expected in ((2, "04"), (5, "07"), (8, "12")):
        generation = _structured_value_repair_generation(
            question=f"Nếu nghỉ {requested} ngày thì cần báo trước bao lâu?",
            source_registry=registry,
        )
        assert generation is not None
        answer = json.loads(generation.content)["answer"]
        assert f"{expected} ngay lam viec" in answer
        assert "02 ngay lam viec" not in answer


def test_leave_notice_missing_or_conflicting_band_has_no_bound_answer() -> None:
    question = "Nếu nghỉ 5 ngày thì cần báo trước bao lâu?"
    missing = source("Phép năm 1-3 ngày Trước ít nhất 04 ngày làm việc")
    conflicting = sources(
        "Phép năm 4-6 ngày Trước ít nhất 07 ngày làm việc",
        "Phép năm 4-6 ngày Trước ít nhất 09 ngày làm việc",
    )

    assert _structured_value_repair_generation(question=question, source_registry=missing) is None
    assert (
        _structured_value_repair_generation(question=question, source_registry=conflicting) is None
    )


def test_leave_notice_repair_handles_pdf_dash_noise_and_strictly_over_threshold() -> None:
    registry = source(
        "Phép năm 1- - 2 ngày Trước ít nhất - 04 ngày làm việc "
        "Phép năm 3- - 5 ngày Trước ít nhất - 07 ngày làm việc "
        "Phép năm trên - 5 ngày Trước ít nhất - 12 ngày làm việc"
    )
    two_days = _structured_value_repair_generation(
        question="Muốn nghỉ phép 2 ngày thì nên xin trước mấy ngày?",
        source_registry=registry,
    )
    more_than_five = _structured_value_repair_generation(
        question="Nghỉ hơn 5 ngày thì báo trước bao lâu?",
        source_registry=registry,
    )

    assert two_days is not None
    assert "04 ngay lam viec" in json.loads(two_days.content)["answer"]
    assert more_than_five is not None
    assert "12 ngay lam viec" in json.loads(more_than_five.content)["answer"]


def test_remote_registration_deadline_uses_source_clock_not_fixture_time() -> None:
    question = "Ngày mai làm remote thì đăng ký trước mấy giờ?"
    answered = _structured_attendance_policy_answer(
        question=question,
        source_registry=source("Đăng ký lịch remote trước 14:30 của ngày làm việc liền trước."),
    )
    missing = _structured_attendance_policy_answer(
        question=question,
        source_registry=source("Đăng ký lịch remote của ngày làm việc liền trước."),
    )

    assert answered is not None
    assert "14:30" in answered[0]
    assert "16:00" not in answered[0]
    assert missing is None


def test_leave_policy_clause_repair_binds_sickness_and_unused_leave_actions() -> None:
    registry = source(
        "Ốm đau / khẩn cấp Thông báo ngay khi có thể; hoàn thiện HRM và hồ sơ sau.\n"
        "THANH TOÁN PHÉP CHƯA NGHỈ\n"
        "Khi chấm dứt quan hệ lao động, việc thanh toán tiền lương cho ngày nghỉ "
        "hằng năm chưa nghỉ được thực hiện theo pháp luật và số dư hợp lệ."
    )

    sickness = _structured_value_repair_generation(
        question="Tôi bị sốt sáng nay thì phải làm gì trước?",
        source_registry=registry,
    )
    unused = _structured_value_repair_generation(
        question="Nghỉ việc mà còn phép chưa dùng thì xử lý sao?",
        source_registry=registry,
    )

    assert sickness is not None
    assert "Thông báo ngay khi có thể" in json.loads(sickness.content)["answer"]
    assert unused is not None
    unused_answer = json.loads(unused.content)["answer"]
    assert "chấm dứt quan hệ lao động" in unused_answer
    assert "thanh toán" in unused_answer


def test_leave_duration_completeness_rejects_neighboring_row_value() -> None:
    registry = source(
        "Kết hôn 03 ngày\n"
        "Con đẻ hoặc con nuôi kết hôn 01 ngày\n"
        "14 ngày Công việc nặng nhọc\n16 ngày Công việc đặc biệt nặng nhọc"
    )

    assert _should_retry_incomplete_answer(
        question="Tôi cưới thì được nghỉ mấy ngày?",
        answer="14 ngày.",
        source_registry=registry,
    )
    assert not _should_retry_incomplete_answer(
        question="Tôi cưới thì được nghỉ mấy ngày?",
        answer="03 ngày.",
        source_registry=registry,
    )


def test_prompt_ranking_keeps_matching_leave_action_clause() -> None:
    unrelated = hit(401, "Lịch on-call phải được công bố trước và có phương án backup.")
    sickness = hit(
        402,
        "Ốm đau / khẩn cấp: Thông báo ngay khi có thể; hoàn thiện HRM và hồ sơ sau.",
    )
    offboarding = hit(
        403,
        "Khi chấm dứt quan hệ lao động, thanh toán phép chưa nghỉ được\n"
        "thực hiện theo pháp luật và số dư hợp lệ.",
    )

    sickness_ranked = _rank_hits_for_prompt(
        (unrelated, sickness),
        question="Tôi bị sốt sáng nay thì phải làm gì trước?",
    )
    offboarding_ranked = _rank_hits_for_prompt(
        (unrelated, offboarding),
        question="Nghỉ việc mà còn phép chưa dùng thì xử lý sao?",
    )

    assert sickness_ranked == (sickness,)
    assert len(offboarding_ranked) == 1
    assert "thực hiện theo pháp luật và số dư hợp lệ" in offboarding_ranked[0].text


def test_claim_validation_binds_work_duration_and_schedule_ranges() -> None:
    async def scenario() -> None:
        registry = source(
            "Tong thoi gian lam viec 08 gio/ngay; 40 gio/tuan.\n"
            "Khung bat dau linh hoat 08:00 - 09:00.\n"
            "Khung ket thuc tuong ung 17:00 - 18:00.\n"
            "Gio cot loi 09:30 - 11:30 va 13:30 - 16:30.\n"
            "Nghi trua tieu chuan 60 phut."
        )
        service = ClaimEvidenceValidationService()
        cases = (
            (
                "Mot tuan binh thuong lam bao nhieu tieng?",
                "Thoi luong la 40 gio/tuan.",
            ),
            ("Moi ngay lam may tieng vay?", "Thoi luong la 08 gio/ngay."),
            (
                "Sang minh duoc vao lam tu may gio toi may gio?",
                "Khung thoi gian la 08:00 - 09:00.",
            ),
            (
                "core hour may gio?",
                "Khung thoi gian la 09:30 - 11:30 va 13:30 - 16:30.",
            ),
        )

        for question, answer in cases:
            result = await service.validate(
                question=question,
                answer=answer,
                source_registry=registry,
                cited_source_labels=("SOURCE_1",),
            )
            assert result.status == ClaimEvidenceStatus.SUPPORTED, question

    run_async(scenario())


def test_conditional_allowance_claim_validation_supports_vietnamese_polarity() -> None:
    registry = source(
        "Nhan vien duoc phe duyet che do\n"
        "Hybrid / Remote stipend 500.000 dong/thang hybrid/remote thuong xuyen; khong ap\n"
        "dung cho ngay WFH phat sinh don le."
    )

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        for question, expected_polarity in (
            ("Cong ty co ho tro tien remote khong?", "YES"),
            ("WFH dung 1 hom thi co duoc 500k remote allowance khong?", "NO"),
        ):
            generation = _structured_value_repair_generation(
                question=question,
                source_registry=registry,
            )
            assert generation is not None
            payload = json.loads(generation.content)
            result = await service.validate(
                question=question,
                answer=payload["answer"],
                source_registry=registry,
                cited_source_labels=tuple(payload["citations"]),
                require_subject_attribute_alignment=True,
            )
            assert result.status == ClaimEvidenceStatus.SUPPORTED
            assert result.polarity == expected_polarity

    run_async(scenario())


def test_claim_validation_rejects_neighboring_schedule_row_values() -> None:
    async def scenario() -> None:
        registry = source(
            "Tong thoi gian lam viec 08 gio/ngay; 40 gio/tuan.\n"
            "Khung bat dau linh hoat 08:00 - 09:00.\n"
            "Gio cot loi 09:30 - 11:30 va 13:30 - 16:30."
        )
        service = ClaimEvidenceValidationService()

        wrong_period = await service.validate(
            question="Mot tuan binh thuong lam bao nhieu tieng?",
            answer="Thoi luong la 08 gio/ngay.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        wrong_row = await service.validate(
            question="Sang minh duoc vao lam tu may gio toi may gio?",
            answer="Khung thoi gian la 09:30 - 11:30.",
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )

        assert wrong_period.status == ClaimEvidenceStatus.INSUFFICIENT
        assert wrong_row.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


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


def test_structured_value_repair_maps_open_ended_sunday_ot_to_rate() -> None:
    generation = _structured_value_repair_generation(
        question="Tien OT duoc xu ly the nao vao Chu nhat?",
        source_registry=source(
            "Lam them ngay nghi hang tuan It nhat 200%.\n"
            "It nhat 300%, chua bao gom tien luong ngay le.\n"
            "Lam them ngay le, Tet, ngay nghi co huong luong."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"] == "Ít nhất 200%."


def test_structured_value_repair_describes_matching_allowance() -> None:
    generation = _structured_value_repair_generation(
        question="Nhan vien hybrid duoc huong khoan ho tro nao?",
        source_registry=source(
            "Hybrid / Remote stipend 500.000 d/thang; "
            "ap dung khi duoc phe duyet che do hybrid thuong xuyen; "
            "khong ap dung cho mot ngay WFH don le. "
            "CLAIM_2 evidence: Khoan Muc mo phong Dieu kien chinh."
        ),
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "500.000" in payload["answer"]
    assert "hybrid" in payload["answer"].casefold()
    assert "CLAIM_2" not in payload["answer"]
    assert not payload["answer"].rstrip(".").endswith("khong ap")
    assert payload["citations"] == ["SOURCE_1"]


def test_structured_overtime_rate_repair_binds_day_type_and_minimum() -> None:
    registry = source(
        "OT rates\n"
        "Lam them ngay lam viec binh thuong: it nhat 150%.\n"
        "Lam them ngay nghi hang tuan: it nhat 200%.\n"
        "Lam them ngay le, Tet: it nhat 300%.\n"
        "Thuong hieu suat dat 25% muc tieu."
    )

    normal = _structured_value_repair_generation(
        question="OT ngay thuong thi it nhat bao nhieu phan tram?",
        source_registry=registry,
    )
    holiday = _structured_value_repair_generation(
        question="Lam ngay le thi OT toi thieu bao nhieu?",
        source_registry=registry,
    )
    unsupported = _structured_value_repair_generation(
        question="Lam them vao ban dem thi it nhat bao nhieu phan tram?",
        source_registry=source("Lam them ngay lam viec binh thuong: it nhat 150%."),
    )

    assert normal is not None
    assert holiday is not None
    assert unsupported is None
    normal_answer = json.loads(normal.content)["answer"]
    holiday_answer = json.loads(holiday.content)["answer"]
    assert normal_answer == "Ít nhất 150%."
    assert "200%" not in normal_answer
    assert "300%" not in normal_answer
    assert "25%" not in normal_answer
    assert holiday_answer == "Ít nhất 300%."

    async def scenario() -> None:
        validation = await ClaimEvidenceValidationService().validate(
            question="OT ngay thuong thi it nhat bao nhieu phan tram?",
            answer=normal_answer,
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert validation.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_prompt_selection_keeps_exact_holiday_ot_percentage_row_under_budget() -> None:
    question = "Lam ngay le thi OT toi thieu bao nhieu?"
    holiday_ot = hit(
        931,
        "Muc tra OT. Lam them ngay le, Tet, ngay nghi co huong luong: "
        "it nhat 300%, chua bao gom tien luong ngay le.",
        title="Working and attendance policy",
    )
    normal_ot = hit(
        932,
        "Lam them ngay lam viec binh thuong: it nhat 150%.",
        title="Working and attendance policy",
    )
    generic_attendance = hit(
        933,
        "Cham cong, nghi phep va quy trinh dieu chinh du lieu cong. " * 40,
        title="Working and attendance policy",
    )

    analysis = analyze_question(question)
    ranked = _rank_hits_for_prompt((generic_attendance, normal_ot, holiday_ot), question=question)

    class WordCounter:
        def count(self, text: str) -> int:
            return len(text.split())

    selected = select_context_for_prompt(
        hits=ranked,
        history_messages=(),
        question=question,
        system_prompt="Answer from sources.",
        token_counter=WordCounter(),
        max_tokens=80,
    )

    assert analysis.answer_type == "PERCENTAGE"
    assert ranked[0] == holiday_ot
    assert selected.items[0].chunk_id == holiday_ot.chunk_id
    assert "300%" in selected.items[0].text
    assert normal_ot.chunk_id not in {item.chunk_id for item in selected.items[:1]}
    assert generic_attendance.chunk_id not in {item.chunk_id for item in selected.items[:1]}


def test_claim_validation_binds_holiday_ot_rate_when_table_value_precedes_label() -> None:
    evidence = (
        "Lam them ngay nghi hang tuan: it nhat 200%.\n"
        "It nhat 300%, chua bao gom tien luong ngay le.\n"
        "Lam them ngay le, Tet, ngay nghi co huong luong."
    )

    async def scenario() -> None:
        validation = await ClaimEvidenceValidationService().validate(
            question="Lam ngay le thi OT toi thieu bao nhieu?",
            answer="It nhat 300%.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert validation.status is ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())


def test_structured_overtime_rate_repair_binds_flattened_table_rows() -> None:
    registry = source(
        "OT rates Lam them ngay lam viec binh thuong it nhat 150%. "
        "Lam them ngay nghi hang tuan it nhat 200%. "
        "It nhat 300%, chua bao gom tien luong ngay le Lam them ngay le, Tet. "
        "Duoc tra them it nhat 30% tien luong Lam viec ban dem. "
        "Ngoai tien OT con tra them it nhat 20% Lam them vao ban dem."
    )

    holiday = _structured_value_repair_generation(
        question="Lam ngay le thi OT toi thieu bao nhieu?",
        source_registry=registry,
    )
    night = _structured_value_repair_generation(
        question="OT lam viec ban dem duoc tra them bao nhieu phan tram?",
        source_registry=registry,
    )

    assert holiday is not None
    assert night is not None
    assert json.loads(holiday.content)["answer"] == "Ít nhất 300%."
    assert json.loads(night.content)["answer"] == "Ít nhất 30%."


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


def test_monetary_visit_limit_beats_annual_cap_in_wrapped_table() -> None:
    evidence = (
        "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh\n"
        "dieu khoan loai tru.\n"
        "Toi da 1,2 trieu dong/lan; yeu cau chung\n"
        "Ngoai tru 12 trieu dong\n"
        "tu hop le."
    )
    question = "Mot lan kham ngoai tru toi da bao nhieu?"

    generation = _structured_value_repair_generation(
        question=question, source_registry=source(evidence)
    )

    assert requested_monetary_period(question) == "lan"
    assert generation is not None
    assert "1,2 trieu dong/lan" in json.loads(generation.content)["answer"]

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        for answer, expected in (
            ("Gia tri la 1,2 trieu dong/lan.", ClaimEvidenceStatus.SUPPORTED),
            ("Gia tri la 12 trieu dong.", ClaimEvidenceStatus.INSUFFICIENT),
        ):
            result = await service.validate(
                question=question,
                answer=answer,
                source_registry=source(evidence),
                cited_source_labels=("SOURCE_1",),
                require_subject_attribute_alignment=True,
            )
            assert result.status == expected

    run_async(scenario())


def test_monetary_period_selection_and_validation_do_not_cross_pair_values() -> None:
    evidence = (
        "Nhom quyen loi Han muc mo phong/nam Dieu kien chinh\n"
        "Toi da 1,2 trieu dong/lan; yeu cau chung\n"
        "Ngoai tru 12 trieu dong/nam\n"
        "tu hop le."
    )
    registry = source(evidence)
    per_visit = "Mot lan kham ngoai tru toi da bao nhieu?"
    per_year = "Han muc ngoai tru moi nam la bao nhieu?"
    visit_generation = _structured_value_repair_generation(
        question=per_visit, source_registry=registry
    )
    year_generation = _structured_value_repair_generation(
        question=per_year, source_registry=registry
    )
    no_period_generation = _structured_value_repair_generation(
        question="Han muc ngoai tru la bao nhieu?", source_registry=registry
    )

    assert requested_monetary_period(per_year) == "nam"
    assert requested_monetary_period("Han muc ngoai tru la bao nhieu?") is None
    assert visit_generation is not None
    assert year_generation is not None
    assert no_period_generation is not None
    assert "1,2 trieu dong/lan" in json.loads(visit_generation.content)["answer"]
    assert "12 trieu dong/nam" in json.loads(year_generation.content)["answer"]
    assert "12 trieu dong" in json.loads(no_period_generation.content)["answer"]

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        for question, answer, expected in (
            (per_visit, "Gia tri la 1,2 trieu dong/lan.", ClaimEvidenceStatus.SUPPORTED),
            (per_year, "Gia tri la 12 trieu dong/nam.", ClaimEvidenceStatus.SUPPORTED),
            (per_visit, "Gia tri la 12 trieu dong/lan.", ClaimEvidenceStatus.INSUFFICIENT),
            (per_year, "Gia tri la 1,2 trieu dong/nam.", ClaimEvidenceStatus.INSUFFICIENT),
        ):
            result = await service.validate(
                question=question,
                answer=answer,
                source_registry=registry,
                cited_source_labels=("SOURCE_1",),
                require_subject_attribute_alignment=True,
            )
            assert result.status == expected

    run_async(scenario())


def test_same_monetary_amount_keeps_its_period_and_other_benefit_is_not_substituted() -> None:
    same_amount = "Goi Alpha 500 dong/lan.\nGoi Alpha 500 dong/nam."
    question = "Han muc Goi Alpha moi nam bao nhieu?"
    generation = _structured_value_repair_generation(
        question=question, source_registry=source(same_amount)
    )
    assert generation is not None
    assert "500 dong/nam" in json.loads(generation.content)["answer"]
    assert monetary_value_period_pairs(same_amount) == {("500", "lan"), ("500", "nam")}

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        wrong_period = await service.validate(
            question=question,
            answer="Gia tri la 500 dong/lan.",
            source_registry=source(same_amount),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        correct_period = await service.validate(
            question=question,
            answer="Gia tri la 500 dong/nam.",
            source_registry=source(same_amount),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        wrong_benefit = await service.validate(
            question="Mot lan kham ngoai tru toi da bao nhieu?",
            answer="Gia tri la 3 trieu dong/lan.",
            source_registry=source("Nha khoa 3 trieu dong/lan.\nNgoai tru 12 trieu dong/nam."),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )
        assert wrong_period.status == ClaimEvidenceStatus.INSUFFICIENT
        assert correct_period.status == ClaimEvidenceStatus.SUPPORTED
        assert wrong_benefit.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())
    cross_benefit = _scored_question_focused_direct_value_from_text(
        question="Mot lan kham ngoai tru toi da bao nhieu?",
        source_text="Nha khoa 3 trieu dong/lan.\nNgoai tru 12 trieu dong/nam.",
        analysis=analyze_question("Mot lan kham ngoai tru toi da bao nhieu?"),
    )
    assert cross_benefit is None


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


def test_conditional_allowance_repair_keeps_value_and_qualification_together() -> None:
    registry = source(
        "Lunch allowance 900000 dong/thang for full-time employees. "
        "Hybrid stipend 500000 dong/thang for approved regular hybrid work; "
        "does not apply to a single ad hoc remote day."
    )

    existence = _structured_value_repair_generation(
        question="Does the hybrid stipend exist?",
        source_registry=registry,
    )
    qualifying = _structured_value_repair_generation(
        question="Does an approved regular hybrid arrangement receive the hybrid stipend?",
        source_registry=registry,
    )
    excluded = _structured_value_repair_generation(
        question="Does one ad hoc remote day receive the hybrid stipend?",
        source_registry=registry,
    )
    unknown = _structured_value_repair_generation(
        question="Is the hybrid stipend available in a special remote arrangement?",
        source_registry=registry,
    )

    assert existence is not None
    assert qualifying is not None
    assert excluded is not None
    assert unknown is None

    existence_payload = json.loads(existence.content)
    qualifying_payload = json.loads(qualifying.content)
    excluded_payload = json.loads(excluded.content)
    assert existence_payload["citations"] == ["SOURCE_1"]
    assert "500000 dong/thang" in existence_payload["answer"]
    assert "900000" not in existence_payload["answer"]
    assert qualifying_payload["answer"].startswith("C\u00f3.")
    assert "approved regular hybrid work" in qualifying_payload["answer"]
    assert excluded_payload["answer"].startswith("Kh\u00f4ng.")
    assert "single ad hoc remote day" in excluded_payload["answer"]
    assert "500000 dong/thang" in excluded_payload["answer"]

    async def scenario() -> None:
        service = ClaimEvidenceValidationService()
        for question, payload, polarity in (
            (
                "Does the hybrid stipend exist?",
                existence_payload,
                "YES",
            ),
            (
                "Does an approved regular hybrid arrangement receive the hybrid stipend?",
                qualifying_payload,
                "YES",
            ),
            (
                "Does one ad hoc remote day receive the hybrid stipend?",
                excluded_payload,
                "NO",
            ),
        ):
            result = await service.validate(
                question=question,
                answer=payload["answer"],
                source_registry=registry,
                cited_source_labels=tuple(payload["citations"]),
                require_subject_attribute_alignment=True,
            )
            assert result.status == ClaimEvidenceStatus.SUPPORTED
            assert result.polarity == polarity

    run_async(scenario())


def test_conditional_allowance_validation_rejects_yes_for_explicitly_excluded_scenario() -> None:
    """General benefit availability must not reverse a stated exclusion."""

    registry = source(
        "Equipment allowance 1200000 dong/nam for approved regular field work; "
        "does not apply to a single ad hoc site visit."
    )

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Does one ad hoc site visit receive the equipment allowance?",
            answer=(
                "Yes. The equipment allowance is 1200000 dong/nam for approved "
                "regular field work; it does not apply to a single ad hoc site visit."
            ),
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert result.status == ClaimEvidenceStatus.INSUFFICIENT

    run_async(scenario())


def test_conditional_allowance_repair_binds_accented_vietnamese_exclusion() -> None:
    registry = source(
        "Travel allowance 700000 dong/thang ap dung cho tuyen cong tac duoc phe duyet; "
        "không áp dụng cho một chuyến phát sinh đơn lẻ."
    )

    generation = _structured_value_repair_generation(
        question="Một chuyến phát sinh đơn lẻ có được travel allowance không?",
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert payload["answer"].startswith("Không.")
    assert "700000 dong/thang" in payload["answer"]
    assert "một chuyến phát sinh đơn lẻ" in payload["answer"]


def test_prompt_ranking_keeps_conditional_allowance_row_for_entitlement() -> None:
    work_arrangement = hit(
        411,
        "Remote work requires timekeeping and manager approval.",
        title="Work arrangement",
    )
    lunch = hit(
        412,
        "Lunch allowance 900000 dong/thang for full-time employees.",
        title="Allowances",
    )
    conditional = hit(
        413,
        "Hybrid stipend 500000 dong/thang for approved regular hybrid work; "
        "does not apply to a single ad hoc remote day.",
        title="Allowances",
    )

    ranked = _rank_hits_for_prompt(
        (work_arrangement, lunch, conditional),
        question="Does the company support remote work with an allowance?",
    )

    assert ranked == (conditional,)


def test_numeric_named_benefit_keeps_its_value_row_over_other_allowances() -> None:
    named_benefit = hit(
        421,
        "Ergonomic support 1.500.000 dong/24 thang; equipment must be eligible.",
        title="Benefits",
    )
    generic_allowance = hit(
        422,
        "Lunch allowance 900.000 dong/thang for full-time employees. "
        "Hybrid stipend 500.000 dong/thang for approved regular work.",
        title="Salary and allowances",
    )

    ranked = _rank_hits_for_prompt(
        (named_benefit, generic_allowance),
        question="Tien mua do ergonomic duoc ho tro bao nhieu va bao lau mot lan?",
    )

    assert ranked[0] == named_benefit
    assert generic_allowance not in ranked


def test_prompt_ranking_keeps_allowance_row_for_which_benefit_question() -> None:
    attendance = hit(
        414,
        "Hybrid employees clock in on HRM using MFA.",
        title="Work arrangement",
    )
    allowance = hit(
        415,
        "Hybrid / Remote stipend 500000 dong/thang for approved regular hybrid work; "
        "does not apply to one ad hoc remote day.",
        title="Compensation",
    )

    ranked = _rank_hits_for_prompt(
        (attendance, allowance),
        question="Nhan vien hybrid duoc huong khoan ho tro nao?",
    )

    assert ranked == (allowance,)


def test_structured_policy_repair_supports_scoped_own_information_permission() -> None:
    question = "Nhan vien co duoc noi ve muc luong cua chinh minh khong?"
    registry = source(
        "Nhan vien khong duoc phat tan du lieu luong cua nguoi khac.\n"
        "Chinh sach khong cam nguoi lao dong su dung, trao doi hoac cung cap "
        "thong tin luong cua chinh minh khi thuc hien quyen hop phap."
    )
    generation = _structured_policy_clause_repair_generation(
        question=question,
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question=question,
            answer=payload["answer"],
            source_registry=registry,
            cited_source_labels=tuple(payload["citations"]),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED
        assert result.polarity == "YES"

    run_async(scenario())


def test_structured_policy_repair_recognizes_disclosure_phrasing() -> None:
    question = "Toi co duoc noi cho dong nghiep biet luong cua chinh toi khong?"
    registry = source(
        "- Nhan vien khong duoc phat tan luong cua nguoi khac neu khong co nhiem\n"
        "vu duoc phe duyet.\n"
        "- Chinh sach khong cam nguoi lao dong su dung, trao doi hoac cung cap "
        "thong tin luong cua chinh minh khi\n"
        "thuc hien quyen hop phap."
    )

    generation = _structured_policy_clause_repair_generation(
        question=question,
        source_registry=registry,
    )

    assert generation is not None
    payload = json.loads(generation.content)
    assert "thuc hien quyen hop phap" in payload["answer"].lower()
    assert "vu duoc phe duyet" not in payload["answer"].lower()


def test_security_control_validation_rejects_uncited_material_controls() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Nhan vien hybrid phai tuan thu bao mat gi khi lam o nha?",
            answer=("Nhan vien phai su dung thiet bi duoc phe duyet va xac thuc nhieu lop."),
            source_registry=source(
                "Nhan vien hybrid cham cong bang tai khoan ca nhan va xac thuc nhieu lop."
            ),
            cited_source_labels=("SOURCE_1",),
            require_subject_attribute_alignment=True,
        )

        assert result.status == ClaimEvidenceStatus.INSUFFICIENT

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


def test_prompt_ranking_keeps_leave_incident_rules_over_generic_operations() -> None:
    replacement = hit(
        981,
        "Nhan vien dang nghi phep nhung la dau moi duy nhat. "
        "Quan ly kich hoat nguoi thay the truoc; chi lien he nhan vien nghi "
        "khi khong con phuong an hop ly va co su dong y. "
        "Ap dung lich truc da cong bo, ghi nhan thoi gian thuc te xu ly.",
        title="Chinh sach nghi cua nguoi lao dong",
    )
    generic_attendance = hit(
        982,
        "Production incident duoc thong bao cho quan ly. Sau su co can bo tri "
        "thoi gian nghi phuc hoi hop ly.",
        title="Chinh sach lam viec va cham cong",
    )
    unrelated_benefit = hit(
        983,
        "Nhan vien nghi phep van duoc huong bao hiem suc khoe bo sung.",
        title="Chinh sach bao hiem va phuc loi",
    )

    ranked = _rank_hits_for_prompt(
        (generic_attendance, unrelated_benefit, replacement),
        question=(
            "Nhan vien dang nghi phep nhung phai ho tro su co thi quyen nghi "
            "va thoi gian phat sinh xu ly the nao?"
        ),
    )

    assert ranked == (replacement,)


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


def test_structured_policy_repair_copies_leave_incident_rights_and_time() -> None:
    registry = source(
        "Nhan vien dang nghi phep nhung la dau moi duy nhat\n"
        "Quan ly kich hoat nguoi thay the truoc; chi lien he nhan vien\n"
        "Nhan vien dang nghi phep nhung la dau moi duy nhat\n"
        "nghi khi khong con phuong an hop ly va co su dong y.\n"
        "Ap dung lich truc da cong bo, ghi nhan thoi gian thuc te xu ly."
    )

    rights = _structured_value_repair_generation(
        question="Nhan vien dang nghi phep ho tro su co thi quyen nghi the nao?",
        source_registry=registry,
    )
    incident_time = _structured_value_repair_generation(
        question="Nhan vien dang nghi phep ho tro su co thi thoi gian phat sinh xu ly the nao?",
        source_registry=registry,
    )

    assert rights is not None
    assert incident_time is not None
    rights_answer = json.loads(rights.content)["answer"].casefold()
    time_answer = json.loads(incident_time.content)["answer"].casefold()
    assert "nguoi thay the truoc" in rights_answer
    assert "dong y" in rights_answer
    assert rights_answer.count("dang nghi phep") == 0
    assert "ghi nhan thoi gian thuc te" in time_answer


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


def test_scoped_policy_entailment_requires_matching_action_scope_and_polarity() -> None:
    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        own_question = "Can an employee discuss their own records?"
        own_permission = (
            "The policy does not prohibit an employee from discussing their own records."
        )

        supported = await validator.validate(
            question=own_question,
            answer="Yes. An employee may discuss their own records.",
            source_registry=source(own_permission),
            cited_source_labels=("SOURCE_1",),
        )
        reversed_polarity = await validator.validate(
            question=own_question,
            answer="No. An employee is prohibited from discussing their own records.",
            source_registry=source(own_permission),
            cited_source_labels=("SOURCE_1",),
        )
        own_to_other = await validator.validate(
            question="Can an employee discuss another employee's records?",
            answer="Yes. An employee may discuss another employee's records.",
            source_registry=source(own_permission),
            cited_source_labels=("SOURCE_1",),
        )
        other_to_own = await validator.validate(
            question=own_question,
            answer="No. An employee is prohibited from discussing their own records.",
            source_registry=source(
                "The policy prohibits an employee from discussing another employee's records."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        action_mismatch = await validator.validate(
            question=own_question,
            answer="Yes. An employee may discuss their own records.",
            source_registry=source(
                "The policy does not prohibit an employee from archiving their own records."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        generic_overlap = await validator.validate(
            question=own_question,
            answer="No. An employee is prohibited from discussing their own records.",
            source_registry=source(
                "An employee may not request leave records for another employee."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        negated_permission_yes = await validator.validate(
            question=own_question,
            answer="Yes. An employee may discuss their own records.",
            source_registry=source(
                "The policy does not permit an employee to discuss their own records."
            ),
            cited_source_labels=("SOURCE_1",),
        )
        negated_permission_no = await validator.validate(
            question=own_question,
            answer="No. An employee may not discuss their own records.",
            source_registry=source(
                "The policy does not permit an employee to discuss their own records."
            ),
            cited_source_labels=("SOURCE_1",),
        )

        assert supported.status is ClaimEvidenceStatus.SUPPORTED
        assert supported.polarity == "YES"
        assert reversed_polarity.status is ClaimEvidenceStatus.CONTRADICTED
        assert own_to_other.status is ClaimEvidenceStatus.INSUFFICIENT
        assert other_to_own.status is ClaimEvidenceStatus.INSUFFICIENT
        assert action_mismatch.status is ClaimEvidenceStatus.INSUFFICIENT
        assert generic_overlap.status is ClaimEvidenceStatus.INSUFFICIENT
        assert negated_permission_yes.status is ClaimEvidenceStatus.CONTRADICTED
        assert negated_permission_no.status is ClaimEvidenceStatus.SUPPORTED
        assert negated_permission_no.polarity == "NO"

    run_async(scenario())


def test_scoped_policy_citation_selection_requires_material_entailment() -> None:
    question = "Can an employee discuss their own records?"
    answer = "Yes. An employee may discuss their own records."
    registry = sources(
        "An employee may not request leave records without manager approval.",
        "The policy does not prohibit an employee from discussing their own records.",
    )

    labels = ClaimEvidenceValidationService().select_supporting_source_labels(
        question=question,
        answer=answer,
        source_registry=registry,
        preferred_source_labels=("SOURCE_1",),
        max_sources=2,
    )

    async def scenario() -> None:
        validator = ClaimEvidenceValidationService()
        wrong_citation = await validator.validate(
            question=question,
            answer=answer,
            source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
        right_citation = await validator.validate(
            question=question,
            answer=answer,
            source_registry=registry,
            cited_source_labels=("SOURCE_2",),
        )
        wrong_claim = await validator.validate(
            question=question,
            answer="No. An employee is prohibited from discussing their own records.",
            source_registry=registry,
            cited_source_labels=("SOURCE_2",),
        )

        assert wrong_citation.status is ClaimEvidenceStatus.INSUFFICIENT
        assert right_citation.status is ClaimEvidenceStatus.SUPPORTED
        assert wrong_claim.status is ClaimEvidenceStatus.CONTRADICTED

    assert labels == ("SOURCE_2",)
    run_async(scenario())


def test_scoped_policy_without_own_or_other_evidence_is_no_answer() -> None:
    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question="Can an employee discuss their own records?",
            answer="Yes. An employee may discuss their own records.",
            source_registry=source(
                "The policy does not prohibit employees from discussing records."
            ),
            cited_source_labels=("SOURCE_1",),
        )

        assert result.status is ClaimEvidenceStatus.INSUFFICIENT

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


def test_mixed_question_list_keeps_only_relevant_structured_value_row() -> None:
    mixed = hit(
        313,
        "Kiem thu RAG: cau hoi mau de danh gia he thong.\n"
        "Grade Vi du chuc danh Dai Base Salary tham khao gross/thang\n"
        "N4 Senior Engineer / Senior Specialist 28 - 48 trieu dong\n"
        "N5 Engineering Manager 42 - 70 trieu dong",
    )

    analysis = analyze_question("Senior Engineer khoang bao nhieu tien mot thang?")
    assert analysis.asks_for_amount
    filtered = _filter_non_answer_context_hits(
        ((0, mixed, 1.0),),
        question="Senior Engineer khoang bao nhieu tien mot thang?",
    )

    assert len(filtered) == 1
    assert "Senior Engineer" in filtered[0][1].text
    assert "28 - 48 trieu dong" in filtered[0][1].text
    assert "Kiem thu RAG" not in filtered[0][1].text
    assert "Engineering Manager" not in filtered[0][1].text


def test_pure_question_list_is_removed_by_non_answer_context_filter() -> None:
    question_list = hit(
        314,
        "Kiem thu RAG. Cau hoi mau: Senior Engineer bao nhieu tien?\n"
        "Ky vong cau tra loi: 28 - 48 trieu dong.",
    )

    assert (
        _filter_non_answer_context_hits(
            ((0, question_list, 1.0),),
            question="Senior Engineer khoang bao nhieu tien mot thang?",
        )
        == ()
    )


def test_reference_preamble_followed_by_factual_section_keeps_only_section() -> None:
    mixed = hit(
        1010,
        "MUC LUC\n1 Tong quan 2\n2 Nhan su 5\n"
        "Tai lieu lien quan va lich su sua doi 9\n"
        "01 HO SO TONG QUAN DOANH NGHIEP\n"
        "Aster Cloud la doanh nghiep phan mem phuc vu khach hang doanh nghiep.\n"
        "Nam thanh lap 2019\n"
        "Linh vuc hoat dong Nen tang du lieu, dich vu dam may va an toan thong tin.\n"
        "Van phong Ha Noi va Da Nang.",
        title="Gioi thieu doanh nghiep",
    )

    filtered = _filter_non_answer_context_hits(
        ((0, mixed, 12.0),),
        question="Aster Cloud hoat dong trong nhung linh vuc nao?",
    )

    assert len(filtered) == 1
    assert "Linh vuc hoat dong" in filtered[0][1].text
    assert "Nam thanh lap 2019" in filtered[0][1].text
    assert "MUC LUC" not in filtered[0][1].text
    assert "Tai lieu lien quan" not in filtered[0][1].text


def test_reference_only_navigation_does_not_become_evidence() -> None:
    reference = hit(
        1011,
        "MUC LUC\n1 Tong quan 2\n2 Nhan su 5\n"
        "01 HO SO TONG QUAN DOANH NGHIEP 6\n"
        "Thong tin nhan dien 6\nLinh vuc hoat dong 7\nVan phong 8",
        title="Gioi thieu doanh nghiep",
    )

    assert (
        _filter_non_answer_context_hits(
            ((0, reference, 12.0),),
            question="Doanh nghiep hoat dong trong nhung linh vuc nao?",
        )
        == ()
    )


def test_reference_navigation_without_page_numbers_stays_suppressed() -> None:
    reference = hit(
        1015,
        "MUC LUC\n1 Tong quan\n"
        "01 HO SO TONG QUAN DOANH NGHIEP\n"
        "Thong tin nhan dien\nLinh vuc hoat dong\n"
        "Van phong dai dien\nMo hinh kinh doanh",
        title="Gioi thieu doanh nghiep",
    )

    assert (
        _filter_non_answer_context_hits(
            ((0, reference, 12.0),),
            question="Doanh nghiep hoat dong trong nhung linh vuc nao?",
        )
        == ()
    )


def test_sample_only_section_stays_suppressed_after_reference_heading() -> None:
    sample = hit(
        1012,
        "MUC LUC\n1 Cau hoi kiem thu 8\n"
        "01 CAU HOI KIEM THU RAG\n"
        "Tinh huong mau: Cong ty duoc thanh lap khi nao?\n"
        "Ky vong cau tra loi: Nam 2019.\n"
        "Cau hoi mau: Cong ty co may van phong?\n"
        "Ky vong cau tra loi: Hai van phong.",
        title="Kich ban danh gia",
    )

    assert (
        _filter_non_answer_context_hits(
            ((0, sample, 12.0),),
            question="Cong ty duoc thanh lap khi nao?",
        )
        == ()
    )


def test_factual_organization_section_outranks_generic_hr_overlap() -> None:
    organization = hit(
        1013,
        "MUC LUC\n1 Tong quan 2\n"
        "01 HO SO TONG QUAN DOANH NGHIEP\n"
        "Aster Cloud la doanh nghiep phan mem phuc vu khach hang doanh nghiep.\n"
        "Linh vuc hoat dong Nen tang du lieu, dich vu dam may va an toan thong tin.\n"
        "Van phong Ha Noi va Da Nang.",
        title="Gioi thieu va co cau to chuc Aster Cloud",
    )
    hr_overlap = hit(
        1014,
        "Bo phan nhan su quan ly ho so cong ty va he thong cham cong. "
        "Nhan vien duoc bo tri van phong va thiet bi cong nghe theo nhu cau.",
        title="Noi quy nhan su Aster Cloud",
    )
    question = "Cong ty Aster Cloud dang lam nhung mang gi?"
    filtered = _filter_non_answer_context_hits(
        ((0, organization, 12.0), (1, hr_overlap, 12.0)),
        question=question,
    )

    assert (
        _rank_hits_for_prompt(tuple(row[1] for row in filtered), question=question)[0].chunk_id
        == organization.chunk_id
    )


def test_directly_built_organization_fact_is_not_misread_as_on_call_duty() -> None:
    organization = hit(
        1016,
        "Trung tam AI va Du lieu\n"
        "Xay dung nen tang du lieu, machine learning, generative AI va he thong RAG.\n"
        "Trung tam nay thiet lap tieu chuan chat luong du lieu va quan tri vong doi AI.",
        title="Gioi thieu va co cau to chuc",
    )
    on_call = hit(
        1017,
        "Ca truc on-call xu ly su co phai ghi nhan thoi gian thuc te xu ly. "
        "Khong tu dong tinh toan bo ca truc la gio lam them.",
        title="Quy dinh cham cong",
    )
    question = "Bo phan nao truc tiep xay may he thong AI/RAG cua cong ty?"

    analysis = analyze_question(question)
    assert analysis.answer_type == "ORGANIZATION"
    assert not analysis.asks_for_explicit_value
    assert _prompt_attendance_policy_score(text=on_call.text.casefold(), question=question) == 0.0
    assert (
        _rank_hits_for_prompt((on_call, organization), question=question)[0].chunk_id
        == organization.chunk_id
    )
    assert (
        _prompt_attendance_policy_score(
            text=on_call.text.casefold(), question="Ca truc on-call xu ly su co tinh gio ra sao?"
        )
        > 0.0
    )


def test_forgotten_attendance_ranking_uses_deadline_relation_not_literal_duration() -> None:
    question = "Quen check-out thi trong bao lau gui yeu cau dieu chinh?"
    source_text = (
        "Quen check-in hoac check-out co the yeu cau dieu chinh. "
        "Yeu cau nen gui trong vong 04 ngay lam viec."
    )
    unrelated = "Bang chung lam viec duoc luu tru trong 04 ngay lam viec."

    assert _prompt_attendance_policy_score(text=source_text.casefold(), question=question) > 0
    assert _prompt_attendance_policy_score(
        text=source_text.casefold(), question=question
    ) > _prompt_attendance_policy_score(text=unrelated.casefold(), question=question)


def test_organization_actor_outscores_unrelated_numeric_acronym_mention() -> None:
    organization = hit(
        1022,
        "Trung tam AI va Du lieu\n"
        "Xay dung nen tang du lieu, machine learning va he thong RAG cho san pham.",
        title="Co cau to chuc",
    )
    numeric_overlap = hit(
        1023,
        "Tai lieu phuc loi co 12 tinh huong minh hoa cho cong cu AI va RAG. "
        "Muc ho tro phu thuoc quy dinh rieng.",
        title="Chinh sach phuc loi",
    )

    assert (
        _rank_hits_for_prompt(
            (numeric_overlap, organization),
            question="Bo phan nao truc tiep xay may he thong AI/RAG cua cong ty?",
        )[0].chunk_id
        == organization.chunk_id
    )


def test_compound_acronym_matches_cooccurring_terms_without_literal_separator() -> None:
    combined = hit(
        1018,
        "Nhom du lieu xay dung he thong AI va nen tang RAG cho san pham.",
    )
    first_only = hit(1019, "Nhom AI phat trien cong cu phan tich.")
    second_only = hit(1020, "Nhom RAG quan ly tai lieu noi bo.")
    question = "Bo phan nao phat trien AI/RAG?"

    filtered = _filter_to_specific_term_hits(
        ((0, first_only, 20.0), (1, second_only, 21.0), (2, combined, 22.0)),
        question=question,
        terms=_prompt_query_needles(question)[1],
    )

    assert tuple(row[1].chunk_id for row in filtered) == (combined.chunk_id,)
    security_question = "VPN/MFA duoc ap dung nhu the nao?"
    security_hit = hit(1021, "Dung VPN va MFA khi truy cap tu xa.")
    assert (
        _filter_to_specific_term_hits(
            ((0, security_hit, 1.0), (1, first_only, 2.0)),
            question=security_question,
            terms=_prompt_query_needles(security_question)[1],
        )[0][1].chunk_id
        == security_hit.chunk_id
    )


def test_bilingual_specific_term_keeps_bound_organization_percentage() -> None:
    organization = hit(
        1024,
        "Quy mo nhan su Khoang 140 nguoi; 47% thuoc khoi ky thuat, du lieu va an toan thong tin.",
        title="Gioi thieu doanh nghiep",
    )
    security_policy = hit(
        1025,
        "Security policy yeu cau kiem soat truy cap tai van phong.",
        title="Quy dinh nhan su",
    )
    question = "Khoang bao nhieu phan tram nhan su lam ky thuat, data voi security?"

    filtered = _filter_to_specific_term_hits(
        ((0, security_policy, 45.0), (1, organization, 210.0)),
        question=question,
        terms=_prompt_query_needles(question)[1],
    )

    assert organization.chunk_id in {row[1].chunk_id for row in filtered}
    assert (
        _rank_hits_for_prompt((security_policy, organization), question=question)[0].chunk_id
        == organization.chunk_id
    )


def test_organization_staff_percentage_is_bound_to_its_technical_group() -> None:
    question = "Khoang bao nhieu phan tram nhan su lam ky thuat, data voi security?"
    evidence = (
        "Answer-focused evidence:\nQuy mo nhan su: Khoang 140 nguoi; "
        "47% thuoc khoi ky thuat, du lieu va an toan thong tin"
    )

    async def scenario() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question=question,
            answer="47% nhan su thuoc khoi ky thuat, du lieu va an toan thong tin.",
            source_registry=source(evidence),
            cited_source_labels=("SOURCE_1",),
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(scenario())
    selected = _scored_question_focused_direct_value_from_text(
        question=question,
        source_text=evidence,
        analysis=analyze_question(question),
    )
    assert selected is not None
    assert selected[1] == "47%"
    structured = _structured_direct_value_answer(
        question=question,
        source_registry=source(evidence),
    )
    assert structured is not None
    assert structured[1] == "SOURCE_1"

    async def validate_structured() -> None:
        result = await ClaimEvidenceValidationService().validate(
            question=question,
            answer=structured[0],
            source_registry=source(evidence),
            cited_source_labels=(structured[1],),
            require_subject_attribute_alignment=True,
        )
        assert result.status == ClaimEvidenceStatus.SUPPORTED

    run_async(validate_structured())


def test_workforce_share_selects_requested_group_in_either_row_order() -> None:
    for evidence in (
        "Nhan su nhom Alpha 35%; nhan su nhom Beta 65%.",
        "Nhan su nhom Beta 65%; nhan su nhom Alpha 35%.",
    ):
        for group, expected in (("Alpha", "35%"), ("Beta", "65%")):
            question = f"Bao nhieu phan tram nhan su thuoc nhom {group}?"
            selected = _scored_question_focused_direct_value_from_text(
                question=question,
                source_text=evidence,
                analysis=analyze_question(question),
            )
            assert selected is not None
            assert selected[1] == expected


def test_workforce_share_does_not_bind_unrelated_group_or_adjacent_line() -> None:
    question = "Bao nhieu phan tram nhan su thuoc nhom Alpha?"
    for evidence in (
        "Nhan su nhom Beta 65%.",
        "65%\nNhan su nhom Alpha",
        "65% chi phi van hanh.\nNhan su nhom Alpha",
    ):
        assert (
            _scored_question_focused_direct_value_from_text(
                question=question,
                source_text=evidence,
                analysis=analyze_question(question),
            )
            is None
        )


def test_workforce_share_keeps_reconstructed_field_and_neighboring_percentages_separate() -> None:
    evidence = (
        "Answer-focused evidence:\n"
        "Quy mo nhan su: Khoang 200 nguoi; 35% thuoc nhom Alpha; "
        "65% thuoc nhom Beta"
    )
    for group, expected in (("Alpha", "35%"), ("Beta", "65%")):
        question = f"Bao nhieu phan tram nhan su thuoc nhom {group}?"
        selected = _scored_question_focused_direct_value_from_text(
            question=question,
            source_text=evidence,
            analysis=analyze_question(question),
        )
        assert selected is not None
        assert selected[1] == expected


def test_office_location_field_outranks_office_policy_and_org_chart() -> None:
    locations = hit(
        1026,
        "Van phong Thanh pho Bac Son, Thanh pho Nam Son va Tinh Hai Son.",
        title="Gioi thieu doanh nghiep Aster Cloud",
    )
    office_policy = hit(
        1027,
        "Nhan vien co the lam viec tai van phong hoac dia diem khach hang.",
        title="Chinh sach lam viec Aster Cloud",
    )
    org_chart = hit(
        1028,
        "Van phong CEO / PMO phoi hop cac don vi kinh doanh.",
        title="Co cau to chuc Aster Cloud",
    )

    assert (
        _rank_hits_for_prompt(
            (office_policy, org_chart, locations),
            question="Aster Cloud co van phong o dau?",
        )[0].chunk_id
        == locations.chunk_id
    )


def test_question_list_with_irrelevant_table_is_not_preserved() -> None:
    mixed = hit(
        315,
        "Kiem thu RAG.\n"
        "Grade Vi du chuc danh Dai Base Salary tham khao gross/thang\n"
        "N5 Engineering Manager 42 - 70 trieu dong",
    )

    assert (
        _filter_non_answer_context_hits(
            ((0, mixed, 1.0),),
            question="Senior Engineer khoang bao nhieu tien mot thang?",
        )
        == ()
    )


def test_question_list_with_wrong_role_row_is_not_preserved() -> None:
    mixed = hit(
        316,
        "Kiem thu RAG.\n"
        "Grade Vi du chuc danh Dai Base Salary tham khao gross/thang\n"
        "N5 Engineering Manager 42 - 70 trieu dong",
    )

    assert (
        _filter_non_answer_context_hits(
            ((0, mixed, 1.0),),
            question="Senior Specialist khoang bao nhieu tien mot thang?",
        )
        == ()
    )


def test_unsupported_question_list_does_not_become_prompt_evidence() -> None:
    mixed = hit(
        317,
        "Kiem thu RAG.\nBang phu cap. An trua 900000 dong/thang.",
    )

    assert (
        _filter_non_answer_context_hits(
            ((0, mixed, 1.0),),
            question="Senior Engineer khoang bao nhieu tien mot thang?",
        )
        == ()
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


def test_non_answer_filter_preserves_wrapped_query_matched_salary_row() -> None:
    target = hit(
        990,
        "Tinh huong va cau hoi kiem thu RAG\n"
        "Salary band reference\n"
        "Grade Roles Range\n"
        "Platform Lead / Engineering Manager\n"
        "P5 44 - 72 trieu dong\n"
        "Regional Director\n"
        "P6 75 - 115 trieu dong",
        title="Compensation policy",
    )
    generic = hit(
        991,
        "Compensation principles and benefit administration. Salary budgets are reviewed annually.",
        title="Compensation policy",
    )

    filtered = _filter_non_answer_context_hits(
        ((0, target, 10.0), (1, generic, 30.0)),
        question="Platform Lead thi salary range bao nhieu?",
    )

    preserved = next(row[1] for row in filtered if row[1].chunk_id == target.chunk_id)
    assert "Platform Lead / Engineering Manager" in preserved.text
    assert "P5 44 - 72 trieu dong" in preserved.text
    assert "P6 75 - 115 trieu dong" not in preserved.text
    assert (
        _rank_hits_for_prompt(
            tuple(row[1] for row in filtered),
            question="Platform Lead thi salary range bao nhieu?",
        )[0].chunk_id
        == target.chunk_id
    )
