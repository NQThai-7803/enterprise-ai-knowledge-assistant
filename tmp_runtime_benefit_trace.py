from __future__ import annotations

import asyncio
import json
import os
from uuid import UUID

import asyncpg

from app.chat.context_builder import _is_person_acronym_question, query_focused_excerpt
from app.chat.prompt_builder import (
    _information_need_source_score,
    _information_need_terms,
    information_need_source_labels,
)
from app.citations.models import PromptSource, PromptSourceRegistry
from app.models import CitationSourceType
from app.retrieval.question_analysis import analyze_question
from app.retrieval.structured import has_explicit_not_specified, selected_structural_line_indexes
from app.retrieval.subclaims import information_need_queries
from app.services.claim_evidence_validation_service import ClaimEvidenceValidationService
from app.services.grounded_answer_service import (
    _structured_policy_clause_repair_generation,
    _structured_value_repair_generation,
)


CASES = {
    "Q075": (
        ("50b9eb0d-60ea-4253-9450-4dacad42609b", "d52936c1-4844-46cd-a492-9e8979754b8a"),
        "Trong policy có ghi cố định tỷ lệ BHXH công ty đóng không?",
    ),
    "Q085": (
        (
            "ff2c5c5d-26f4-493a-aa17-ae12544f668c",
            "219d7320-bc27-47cf-98dc-b572254bf157",
            "382a6c05-54eb-4e78-94ab-81fb9224b141",
            "0c3928a6-88f4-45d6-bc79-c47d2534b099",
            "8b37adba-2402-4c6f-8916-311806cda018",
        ),
        "Tiền mua đồ ergonomic được hỗ trợ bao nhiêu và bao lâu được một lần?",
    ),
    "Q086": (
        ("ff2c5c5d-26f4-493a-aa17-ae12544f668c", "cd524c99-72bf-4aa1-b2d4-8dcdc99cca65"),
        "Nhân viên kết hôn có khoản hỗ trợ riêng của công ty không?",
    ),
    "Q073": (
        ("400d54f2-f10c-4f5f-b68a-f39ae0ec13dd", "8ead7f33-92f8-4106-b875-ffb24fa8deec"),
        "Tôi có được nói cho đồng nghiệp biết lương của chính tôi không?",
    ),
    "Q096": (
        (
            "52d6982f-c375-4426-a946-d424746f49eb",
            "f3677bc8-29b3-4cb7-9f16-b3a7dfb3f038",
            "8b777743-1c80-4a05-9a5b-c0b08e4c3522",
            "a9b972ff-c573-4d0d-9e55-5c83b7a037b3",
        ),
        "Tôi là nhân viên hybrid, vậy vừa phải tuân thủ bảo mật gì khi làm ở nhà vừa được hưởng khoản hỗ trợ nào?",
    ),
}


async def main() -> None:
    connection = await asyncpg.connect(os.environ["TRACE_DATABASE_URL"])
    try:
        output = []
        for case_id, (chunk_ids, question) in CASES.items():
            rows = await connection.fetch(
                "SELECT dc.id, dc.document_id, dc.text, d.title "
                "FROM document_chunks dc JOIN documents d ON d.id = dc.document_id "
                "WHERE dc.id = ANY($1::uuid[])",
                [UUID(chunk_id) for chunk_id in chunk_ids],
            )
            by_id = {str(row["id"]): row for row in rows}
            needs = information_need_queries(question)
            excerpts = [
                query_focused_excerpt(
                    by_id[chunk_id]["text"],
                    question,
                    information_needs=needs,
                )
                for chunk_id in chunk_ids
            ]
            analysis = analyze_question(question)
            registry = PromptSourceRegistry(
                sources=tuple(
                    PromptSource(
                        marker=f"[SOURCE_{index}]",
                        source_type=CitationSourceType.INTERNAL,
                        document_title=by_id[chunk_id]["title"],
                        text=excerpts[index - 1],
                        page_numbers=(1,),
                        start_page=1,
                        end_page=1,
                        hybrid_score=1.0,
                        chunk_id=UUID(chunk_id),
                        document_id=by_id[chunk_id]["document_id"],
                    )
                    for index, chunk_id in enumerate(chunk_ids, start=1)
                )
            )
            generation = _structured_value_repair_generation(
                question=question, source_registry=registry
            )
            if generation is None:
                generation = _structured_policy_clause_repair_generation(
                    question=question, source_registry=registry
                )
            payload = json.loads(generation.content) if generation is not None else None
            validation = None
            if payload is not None:
                validation = await ClaimEvidenceValidationService().validate(
                    question=question,
                    answer=payload["answer"],
                    source_registry=registry,
                    cited_source_labels=tuple(payload["citations"]),
                    require_subject_attribute_alignment=True,
                )
            output.append(
                {
                    "id": case_id,
                    "analysis": {
                        "answer_type": analysis.answer_type,
                        "asks_for_percentage": analysis.asks_for_percentage,
                        "asks_for_person": analysis.asks_for_person,
                        "asks_for_explicit_value": analysis.asks_for_explicit_value,
                        "is_person_acronym_question": _is_person_acronym_question(question),
                    },
                    "source_checks": [
                        {
                            "explicit_not_specified": has_explicit_not_specified(
                                by_id[chunk_id]["text"]
                            ),
                            "selected_indexes": selected_structural_line_indexes(
                                by_id[chunk_id]["text"], question, analysis
                            ),
                        }
                        for chunk_id in chunk_ids
                    ],
                    "source_lines": (
                        [
                            {"index": index, "text": line.strip()}
                            for index, line in enumerate(
                                line
                                for line in by_id[chunk_ids[0]]["text"].splitlines()
                                if line.strip()
                            )
                        ]
                        if case_id == "Q073"
                        else None
                    ),
                    "excerpts": excerpts,
                    "routing": [
                        {
                            "need": need,
                            "labels": information_need_source_labels(
                                need,
                                source_registry=registry,
                                max_sources=4,
                            ),
                            "scores": {
                                source.label: _information_need_source_score(
                                    source,
                                    need=need,
                                    terms=_information_need_terms(need),
                                )
                                for source in registry.sources
                            },
                        }
                        for need in needs
                    ],
                    "payload": payload,
                    "validation": validation.status.value if validation else None,
                }
            )
        print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        await connection.close()


asyncio.run(main())
