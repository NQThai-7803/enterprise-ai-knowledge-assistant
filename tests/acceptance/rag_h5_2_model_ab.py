# ruff: noqa: E501
"""Frozen-evidence local generation comparison for RAG-H5.2."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import statistics
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from starlette.requests import Request

from app.api.dependencies import get_grounded_answer_service
from app.chat.context_builder import select_context_for_prompt
from app.chat.models import GroundingStatus
from app.chat.prompt_builder import (
    build_grounded_prompt,
    build_grounding_system_prompt,
    information_need_source_labels,
)
from app.citations.grounded_output import (
    parse_grounded_llm_output,
    parse_structured_grounded_llm_output,
)
from app.citations.registry import build_prompt_source_registry
from app.core.config import get_settings
from app.core.exceptions import CitationValidationFailedApplicationError
from app.db.session import async_session_factory
from app.llm.openai_compatible_provider import OpenAICompatibleLLMProvider
from app.main import app
from app.models import User
from app.retrieval.question_analysis import analyze_question
from app.retrieval.subclaims import information_need_queries
from app.services.claim_evidence_validation_service import ClaimEvidenceStatus
from app.services.grounded_answer_service import (
    _chat_retrieval_candidate_top_k,
    _interleave_retrieval_documents,
    _merge_retrieval_hits,
    _prompt_hit_alignment_score,
    _prompt_query_needles,
    _prompt_source_limit,
)

ARTIFACT = Path(os.getenv("RAG_H52_AB_ARTIFACT", "artifacts/rag-h5-2-model-ab.json"))
MODELS = tuple(
    model.strip()
    for model in os.getenv(
        "RAG_H52_AB_MODELS",
        "qwen2.5:3b,qwen2.5:7b-instruct-8k",
    ).split(",")
    if model.strip()
)


@dataclass(frozen=True, slots=True)
class Case:
    case_id: str
    category: str
    question: str
    expected_groups: tuple[tuple[str, ...], ...] = ()
    unsupported: bool = False


CASES = (
    Case(
        "direct_cto",
        "direct_paraphrase",
        "Người phụ trách công nghệ của Nova Digital tên gì?",
        (("lê thu hà",),),
    ),
    Case("direct_salary_date", "direct_paraphrase", "Lương thường về ngày nào?", (("10",),)),
    Case(
        "direct_remote_short",
        "direct_paraphrase",
        "remote dc may ngay/tuan vay?",
        (("2",), ("ngày", "ngay")),
    ),
    Case("numeric_lunch", "numeric", "phu cap an trua bao nhieu?", (("900",),)),
    Case(
        "numeric_night",
        "numeric",
        "Làm việc ban đêm được cộng thêm bao nhiêu?",
        (("30",), ("%", "phần trăm")),
    ),
    Case("numeric_novacare", "numeric", "NovaCare nội trú tối đa bao nhiêu một năm?", (("150",),)),
    Case(
        "cross_hybrid_security_allowance",
        "cross_document",
        "Nhân viên hybrid có yêu cầu bảo mật gì và có phụ cấp gì?",
        (
            ("vpn", "mfa", "thiết bị", "kết nối an toàn", "thẩm quyền"),
            ("500",),
        ),
    ),
    Case(
        "cross_oncall_sunday",
        "cross_document",
        "Nhân viên on-call xử lý sự cố vào Chủ nhật thì thời gian và mức OT thế nào?",
        (("thời gian thực tế", "ghi nhận"), ("200",)),
    ),
    Case(
        "cross_leave_incident",
        "cross_document",
        "Nhân viên đang nghỉ phép nhưng phải hỗ trợ sự cố thì quyền nghỉ và thời gian phát sinh xử lý thế nào?",
        (("nghỉ",), ("thời gian", "ghi nhận")),
    ),
    Case(
        "cross_schedule_pay",
        "cross_document",
        "Lịch làm việc tham chiếu là gì và làm Chủ nhật được tính OT bao nhiêu phần trăm?",
        (("08", "8 giờ", "giờ"), ("200",)),
    ),
    Case(
        "cross_benefit_eligibility",
        "cross_document",
        "NovaCare có từ ngày đầu không và nội trú được tối đa bao nhiêu mỗi năm?",
        (("không", "khong"), ("sau thử việc", "nhân viên chính thức"), ("150",)),
    ),
    Case(
        "cross_ascii_security_allowance",
        "cross_document",
        "Nhan vien hybrid can tuan thu bao mat nao khi lam o nha va duoc phu cap bao nhieu moi thang?",
        (("ket noi an toan", "vpn", "mfa", "thiet bi", "tham quyen"), ("500",)),
    ),
    Case("unsupported_apple", "unsupported", "CEO Apple là ai?", unsupported=True),
    Case(
        "unsupported_revenue",
        "unsupported",
        "Nova Digital doanh thu năm 2025 bao nhiêu?",
        unsupported=True,
    ),
    Case(
        "unsupported_aws",
        "unsupported",
        "Nova Digital dùng AWS hay Azure cho production?",
        unsupported=True,
    ),
    Case(
        "unsupported_singapore",
        "unsupported",
        "Nova Digital có văn phòng Singapore không?",
        unsupported=True,
    ),
)

# Optional exact-runtime diagnostics. These do not change the authoritative
# 16-case A/B matrix and are selected only through RAG_H52_AB_CASE_IDS.
DIAGNOSTIC_CASES = (
    Case(
        "diag_followup_salary_review",
        "follow_up",
        "salary review được quy định như thế nào?",
        (("salary review",),),
    ),
    Case(
        "diag_followup_leave_under_12_months",
        "follow_up",
        "ngày phép năm của Nhân viên Nova Digital - Nếu chưa đủ 12 tháng?",
        (("tỷ lệ",),),
    ),
    Case(
        "diag_oncall_sunday_ascii",
        "cross_document",
        "Neu on-call phai xu ly su co vao Chu nhat thi thoi gian duoc ghi nhan ra sao va OT bao nhieu?",
        (("ghi nhan", "thoi gian thuc te"), ("200",)),
    ),
    Case(
        "diag_oncall_weekly_rest_ascii",
        "cross_document",
        "Voi ca on-call vao ngay nghi hang tuan, phu cap truc va thoi gian xu ly su co tach ra sao va muc OT la gi?",
        (("on-call",), ("ghi nhan", "thoi gian thuc te"), ("200",)),
    ),
    Case(
        "diag_working_time_payroll_ascii",
        "cross_document",
        "Khung gio lam viec tham chieu la gi va luong hang thang duoc tra ngay nao?",
        (("08:30",), ("17:30",), ("10",)),
    ),
    Case(
        "diag_benefit_eligibility_ascii",
        "cross_document",
        "NovaCare co ngay tu luc nhan viec khong va khi nao duoc tham gia va noi tru toi da bao nhieu moi nam?",
        (("khong",), ("sau thu viec", "nhan vien chinh thuc"), ("150",)),
    ),
    Case(
        "diag_two_document_numeric_ascii",
        "cross_document",
        "Moi thang phu cap an trua bao nhieu va han muc noi tru NovaCare moi nam la bao nhieu?",
        (("900",), ("150",)),
    ),
    Case(
        "diag_three_document_synthesis_ascii",
        "cross_document",
        "Hay tom tat ba moc: so ngay remote moi tuan va phu cap an trua moi thang va han muc noi tru NovaCare moi nam.",
        (("2",), ("900",), ("150",)),
    ),
    Case(
        "diag_followup_compound_ascii",
        "cross_document",
        "Con khoan ho tro hang thang cho che do do la bao nhieu, va neu toi nam vien thi NovaCare toi da bao nhieu mot nam?",
        (("500",), ("150",)),
    ),
)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _request_for_app(application) -> Request:  # noqa: ANN001
    return Request(
        {"type": "http", "method": "GET", "path": "/", "headers": [], "app": application}
    )


def _percentile(values: list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower), 2)


def _summary(results: list[dict[str, object]]) -> dict[str, object]:
    summary: dict[str, object] = {}
    for model in MODELS:
        rows = [row for row in results if row["model"] == model]
        latencies = [int(row["generation_ms"]) for row in rows]
        cross = [row for row in rows if row["category"] == "cross_document"]
        unsupported = [row for row in rows if row["category"] == "unsupported"]
        answered = [row for row in rows if row["status"] == "ANSWER"]
        supported = [row for row in rows if row["category"] != "unsupported"]
        summary[model] = {
            "completed": len(rows),
            "passed": sum(bool(row["passed"]) for row in rows),
            "accuracy": round(sum(bool(row["passed"]) for row in rows) / len(rows), 4)
            if rows
            else 0.0,
            "supported_accuracy": round(
                sum(bool(row["passed"]) for row in supported) / len(supported), 4
            )
            if supported
            else 0.0,
            "numeric_accuracy": _category_accuracy(rows, "numeric"),
            "paraphrase_accuracy": _category_accuracy(rows, "direct_paraphrase"),
            "cross_document": round(sum(bool(row["passed"]) for row in cross) / len(cross), 4)
            if cross
            else 0.0,
            "unsupported_safety": round(
                sum(bool(row["passed"]) for row in unsupported) / len(unsupported), 4
            )
            if unsupported
            else 0.0,
            "claim_completeness": round(
                sum(bool(row["claim_complete"]) for row in cross) / len(cross), 4
            )
            if cross
            else 0.0,
            "claim_support": round(
                sum(bool(row["claim_supported"]) for row in answered) / len(answered), 4
            )
            if answered
            else 0.0,
            "citation_validity": round(
                sum(bool(row["citation_valid"]) for row in answered) / len(answered), 4
            )
            if answered
            else 0.0,
            "false_no_answer_rate": round(
                sum(row["status"] == "NO_ANSWER" for row in supported) / len(supported), 4
            )
            if supported
            else 0.0,
            "average_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p50_ms": round(statistics.median(latencies), 2) if latencies else 0.0,
            "p95_ms": _percentile(latencies, 0.95),
            "max_ms": max(latencies, default=0),
            "timeouts": sum(row["status"] == "TIMEOUT" for row in rows),
        }
    return summary


def _category_accuracy(rows: list[dict[str, object]], category: str) -> float:
    selected = [row for row in rows if row["category"] == category]
    if not selected:
        return 0.0
    return round(sum(bool(row["passed"]) for row in selected) / len(selected), 4)


def _serialize_frozen_case(frozen_case: dict[str, object]) -> dict[str, object]:
    case: Case = frozen_case["case"]
    registry = frozen_case["registry"]
    messages = tuple(frozen_case["messages"])
    rendered_prompt = "\n\n".join(f"{message.role}:\n{message.content}" for message in messages)
    payload = {
        "case_id": case.case_id,
        "category": case.category,
        "resolved_question": case.question,
        "required_claims": list(frozen_case["needs"]),
        "prompt_sha256": hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest(),
        "messages": [{"role": message.role, "content": message.content} for message in messages],
        "selected_sources": [
            {
                "label": source.label,
                "document_id": str(source.document_id) if source.document_id else None,
                "chunk_id": str(source.chunk_id) if source.chunk_id else None,
                "document_title": source.document_title,
                "pages": list(source.page_numbers),
                "packed_evidence": source.text,
            }
            for source in registry.sources
        ],
    }
    if diagnostics := frozen_case.get("retrieval_diagnostics"):
        payload["retrieval_diagnostics"] = diagnostics
    return payload


def _write_checkpoint(
    results: list[dict[str, object]],
    *,
    frozen: list[dict[str, object]],
) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "frozen_case_count": len(frozen),
        "frozen_evidence": [_serialize_frozen_case(case) for case in frozen],
        "results": results,
        "summary": _summary(results),
    }
    ARTIFACT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def main() -> None:
    settings = get_settings()
    service = get_grounded_answer_service(_request_for_app(app))
    async with async_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == "staff.uat@example.test"))
        ).scalar_one()

    selected_case_ids = {
        case_id.strip()
        for case_id in os.getenv("RAG_H52_AB_CASE_IDS", "").split(",")
        if case_id.strip()
    }
    available_cases = CASES + DIAGNOSTIC_CASES if selected_case_ids else CASES
    selected_cases = tuple(
        case
        for case in available_cases
        if not selected_case_ids or case.case_id in selected_case_ids
    )
    end_to_end = os.getenv("RAG_H52_AB_END_TO_END", "1") == "1"
    frozen: list[dict[str, object]] = []
    top_k = _chat_retrieval_candidate_top_k(settings=settings, reranker=service.retrieval_reranker)
    for index, case in enumerate(selected_cases, start=1):
        print(f"[freeze {index}/{len(selected_cases)}] {case.case_id}", flush=True)
        needs = information_need_queries(case.question)
        groups = []
        retrieval_diagnostics = []
        queries = tuple(dict.fromkeys((case.question, *needs)))
        for query in queries:
            result = await service.hybrid_retrieval_service.retrieve(
                query=query, current_user=user, top_k=top_k
            )
            phrases, query_terms, query_numbers = _prompt_query_needles(query)
            query_analysis = analyze_question(query)
            prepared = await service._prepare_prompt_retrieval_hits(
                result.hits, question=query, current_user=user
            )
            groups.append(prepared[:2])
            if os.getenv("RAG_H52_AB_CAPTURE_RETRIEVAL", "0") == "1":
                retrieval_diagnostics.append(
                    {
                        "query": query,
                        "retrieval_hits": [
                            {
                                "rank": rank,
                                "chunk_id": str(hit.chunk_id),
                                "document_title": hit.document_title,
                                "text": hit.text[:500],
                                "alignment_score": _prompt_hit_alignment_score(
                                    hit,
                                    phrases=phrases,
                                    terms=query_terms,
                                    numbers=query_numbers,
                                    question=query,
                                    analysis=query_analysis,
                                    quantity_question="bao nhieu" in _fold(query)
                                    or "how many" in _fold(query),
                                    change_question=False,
                                    role_terms=(),
                                ),
                            }
                            for rank, hit in enumerate(result.hits[:24], start=1)
                        ],
                        "prepared_hits": [
                            {
                                "rank": rank,
                                "chunk_id": str(hit.chunk_id),
                                "document_title": hit.document_title,
                                "text": hit.text[:500],
                            }
                            for rank, hit in enumerate(prepared[:24], start=1)
                        ],
                    }
                )
        merged_hits = _merge_retrieval_hits(*(group[:2] for group in (*groups[1:], groups[0])))
        if len(groups) > 1:
            merged_hits = _interleave_retrieval_documents(merged_hits)
        selected = select_context_for_prompt(
            hits=merged_hits,
            history_messages=(),
            web_results=(),
            conversation_history=None,
            question=case.question,
            information_needs=needs,
            system_prompt=build_grounding_system_prompt(
                no_answer_sentinel=settings.llm_no_answer_sentinel
            ),
            token_counter=service.token_counter,
            max_tokens=settings.chat_context_max_tokens,
        )
        registry = build_prompt_source_registry(
            context_items=selected.items,
            max_sources=_prompt_source_limit(
                settings=settings, reranker=service.retrieval_reranker
            ),
        )
        messages = build_grounded_prompt(
            question=case.question,
            context_items=selected.items,
            history_messages=(),
            no_answer_sentinel=settings.llm_no_answer_sentinel,
            source_registry=registry,
            information_needs=needs,
            structured_claim_output=len(needs) > 1,
        )
        frozen.append(
            {
                "case": case,
                "needs": needs,
                "messages": messages,
                "registry": registry,
                "retrieval_diagnostics": retrieval_diagnostics,
            }
        )

    results: list[dict[str, object]] = []
    _write_checkpoint(results, frozen=frozen)
    if os.getenv("RAG_H52_AB_FREEZE_ONLY", "0") == "1":
        print(json.dumps({"frozen_case_count": len(frozen)}, indent=2), flush=True)
        return
    for model in MODELS:
        provider = OpenAICompatibleLLMProvider(
            base_url="http://127.0.0.1:11434/v1",
            api_key=None,
            model=model,
            timeout_seconds=max(settings.llm_timeout_seconds, 240),
            max_retries=0,
            retry_backoff_seconds=0.0,
            provider_name="ollama",
            reasoning_effort="none",
            app_env="development",
            ollama_num_ctx=settings.llm_ollama_num_ctx,
            ollama_keep_alive=settings.llm_ollama_keep_alive,
        )
        for index, frozen_case in enumerate(frozen, start=1):
            case: Case = frozen_case["case"]
            needs = tuple(frozen_case["needs"])
            registry = frozen_case["registry"]
            print(f"[{model} {index}/{len(frozen)}] {case.case_id}", flush=True)
            started = time.perf_counter()
            status, answer, citations = "INVALID", "", ()
            claim_count = 0
            claim_complete = claim_supported = citation_valid = False
            error_type = None
            generated_outputs: list[str] = []
            generated_requests: list[dict[str, object]] = []
            try:
                if os.getenv("RAG_H52_AB_CAPTURE_OUTPUT", "0") == "1":
                    generated_requests.append(
                        {
                            "kind": "initial",
                            "messages": [
                                {"role": message.role, "content": message.content}
                                for message in tuple(frozen_case["messages"])
                            ],
                        }
                    )
                response = await provider.generate(
                    messages=tuple(frozen_case["messages"]),
                    temperature=settings.llm_temperature,
                    max_output_tokens=settings.llm_max_output_tokens,
                )
                generated_outputs.append(response.content)
                raw = response.content.strip()
                if end_to_end:
                    original_generate = provider.generate

                    async def recording_generate(  # noqa: ANN003, ANN202
                        *,
                        _generate=original_generate,  # noqa: ANN001
                        _outputs=generated_outputs,  # noqa: ANN001
                        _requests=generated_requests,  # noqa: ANN001
                        **kwargs,
                    ):
                        if os.getenv("RAG_H52_AB_CAPTURE_OUTPUT", "0") == "1":
                            _requests.append(
                                {
                                    "kind": "repair",
                                    "messages": [
                                        {"role": message.role, "content": message.content}
                                        for message in kwargs["messages"]
                                    ],
                                }
                            )
                        generated = await _generate(**kwargs)
                        _outputs.append(generated.content)
                        return generated

                    provider.generate = recording_generate
                    try:
                        if len(needs) > 1:
                            draft = await service._compound_draft_with_claim_repair(
                                response,
                                information_needs=needs,
                                source_registry=registry,
                                current_user=user,
                                provider=provider,
                                grounding_question=case.question,
                            )
                        else:
                            draft = await service._draft_from_generation_or_structured_repair(
                                response,
                                source_registry=registry,
                                current_user=user,
                                provider=provider,
                                messages=tuple(frozen_case["messages"]),
                                grounding_question=case.question,
                            )
                    finally:
                        provider.generate = original_generate
                    status = (
                        "ANSWER"
                        if draft.grounding_status == GroundingStatus.ANSWERED
                        else "NO_ANSWER"
                    )
                    answer = draft.content
                    citations = tuple(
                        str(getattr(citation, "document_id", None) or citation.citation_order)
                        for citation in draft.citations
                    )
                    claim_count = len(needs) if len(needs) > 1 else int(status == "ANSWER")
                    claim_complete = claim_supported = status == "ANSWER"
                    citation_valid = status == "ANSWER" and bool(draft.citations)
                elif raw == settings.llm_no_answer_sentinel:
                    status = "NO_ANSWER"
                    claim_complete = claim_supported = citation_valid = case.unsupported
                elif len(needs) > 1 and '"claims"' in raw:
                    structured = parse_structured_grounded_llm_output(
                        raw,
                        expected_claim_ids=tuple(
                            f"CLAIM_{claim_index}" for claim_index in range(1, len(needs) + 1)
                        ),
                        allowed_identifiers={source.label for source in registry.sources},
                    )
                    status = "ANSWER"
                    answer = " ".join(claim.answer for claim in structured.claims)
                    citations = tuple(
                        dict.fromkeys(
                            citation for claim in structured.claims for citation in claim.citations
                        )
                    )
                    claim_count = len(structured.claims)
                    claim_complete = claim_count == len(needs)
                    validations = [
                        await service.claim_validation_service.validate(
                            question=need,
                            answer=claim.answer,
                            source_registry=registry,
                            cited_source_labels=claim.citations,
                            require_subject_attribute_alignment=True,
                        )
                        for claim, need in zip(structured.claims, needs, strict=True)
                    ]
                    claim_supported = all(
                        validation.status == ClaimEvidenceStatus.SUPPORTED
                        for validation in validations
                    )
                    citation_valid = True
                else:
                    parsed = parse_grounded_llm_output(
                        raw, allowed_identifiers={source.label for source in registry.sources}
                    )
                    status, answer, citations = "ANSWER", parsed.answer, parsed.citations
                    claim_count = 1
                    claim_complete = len(needs) <= 1
                    validation = await service.claim_validation_service.validate(
                        question=case.question,
                        answer=answer,
                        source_registry=registry,
                        cited_source_labels=citations,
                    )
                    claim_supported = validation.status == ClaimEvidenceStatus.SUPPORTED
                    citation_valid = True
            except CitationValidationFailedApplicationError:
                status = "NO_ANSWER"
                claim_complete = claim_supported = citation_valid = case.unsupported
            except Exception as exc:  # safe diagnostic type only
                error_type = type(exc).__name__
                status = "TIMEOUT" if "timeout" in error_type.casefold() else "INVALID"

            folded_answer = _fold(answer)
            expected_ok = all(
                any(_fold(term) in folded_answer for term in group)
                for group in case.expected_groups
            )
            passed = (
                status == "NO_ANSWER"
                if case.unsupported
                else status == "ANSWER"
                and expected_ok
                and claim_complete
                and claim_supported
                and citation_valid
            )
            row = {
                "model": model,
                "case_id": case.case_id,
                "category": case.category,
                "status": status,
                "passed": passed,
                "claim_count": claim_count,
                "claim_complete": claim_complete,
                "claim_supported": claim_supported,
                "citation_valid": citation_valid,
                "citations": citations,
                "answer": answer,
                "error_type": error_type,
                "generation_ms": round((time.perf_counter() - started) * 1000),
                "frozen_prompt_sha256": _serialize_frozen_case(frozen_case)["prompt_sha256"],
            }
            if os.getenv("RAG_H52_AB_CAPTURE_OUTPUT", "0") == "1":
                row["generated_outputs"] = generated_outputs
                row["generated_requests"] = generated_requests
                row["source_routes"] = {
                    f"CLAIM_{claim_index}": information_need_source_labels(
                        need,
                        source_registry=registry,
                        max_sources=2,
                    )
                    for claim_index, need in enumerate(needs, start=1)
                }
                row["sources"] = [
                    {
                        "label": source.label,
                        "document_title": source.document_title,
                        "document_id": str(source.document_id),
                        "chunk_id": str(source.chunk_id),
                    }
                    for source in registry.sources
                ]
            results.append(row)
            _write_checkpoint(results, frozen=frozen)
            print(f"  {status} pass={passed} {row['generation_ms']}ms", flush=True)
        await provider.aclose()

    print(json.dumps(_summary(results), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
