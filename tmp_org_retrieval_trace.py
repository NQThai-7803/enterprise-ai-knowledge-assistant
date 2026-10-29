from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import select

from app.chat.context_builder import query_focused_excerpt
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models import User
from app.retrieval.factory import create_hybrid_retrieval_service
from app.retrieval.question_analysis import analyze_question
from app.services import grounded_answer_service as ga
from app.services.grounded_answer_service import GroundedAnswerService, _rank_hits_for_prompt


QUESTIONS = {
    "Q011": "Nova Digital có văn phòng ở đâu?",
    "Q012": "Công ty đang làm những mảng gì?",
}
TARGETS = {
    "Q008": UUID("5b3f2520-f988-4cc9-9f53-c886ef510c11"),
    "Q010": UUID("5b3f2520-f988-4cc9-9f53-c886ef510c11"),
    "Q011": UUID("5b3f2520-f988-4cc9-9f53-c886ef510c11"),
    "Q012": UUID("5b3f2520-f988-4cc9-9f53-c886ef510c11"),
    "Q015": UUID("b3e66a26-1bb8-44c6-9ece-36de147301d6"),
}


async def main() -> None:
    async with async_session_factory() as session:
        user = await session.scalar(
            select(User).where(User.id == UUID("397e8ccc-c012-4aad-8d0c-88ad7a12f985"))
        )
    assert user is not None
    retrieval = create_hybrid_retrieval_service(get_settings())
    output = []
    for case_id, question in QUESTIONS.items():
        target = TARGETS[case_id]
        result = await retrieval.retrieve(query=question, current_user=user, top_k=50)
        expanded = await GroundedAnswerService._expand_adjacent_retrieval_hits(
            SimpleNamespace(session_provider=async_session_factory),
            result.hits,
            current_user=user,
        )
        ranked = _rank_hits_for_prompt(expanded, question=question)
        target_hit = next((hit for hit in result.hits if hit.chunk_id == target), None)
        ranked_target_hit = next((hit for hit in ranked if hit.chunk_id == target), None)
        phrases, terms, numbers = ga._prompt_query_needles(question)
        analysis = analyze_question(question)
        quantity_question = ga._asks_for_quantity(question)
        change_question = ga._question_mentions_change(question)
        role_terms = ga._role_terms_for_prompt_question(question)
        rows = tuple(
            (
                index,
                hit,
                ga._prompt_hit_alignment_score(
                    hit,
                    phrases=phrases,
                    terms=terms,
                    numbers=numbers,
                    question=question,
                    analysis=analysis,
                    quantity_question=quantity_question,
                    change_question=change_question,
                    role_terms=role_terms,
                ),
            )
            for index, hit in enumerate(result.hits)
        )
        stages = (
            ("role", lambda value: ga._filter_to_role_person_hits(value, role_terms=role_terms)),
            ("document", lambda value: ga._filter_to_named_document_title_hits(value, question=question)),
            ("answer", lambda value: ga._filter_non_answer_context_hits(value, question=question)),
            ("salary", lambda value: ga._filter_to_salary_band_hits(value, question=question)),
            ("allowance", lambda value: ga._filter_to_conditional_allowance_hits(value, question=question)),
            ("schedule", lambda value: ga._filter_to_work_schedule_hits(value, question=question)),
            ("leave", lambda value: ga._filter_to_leave_policy_hits(value, question=question)),
            ("specific", lambda value: ga._filter_to_specific_term_hits(value, question=question, terms=terms)),
            ("threshold", ga._filter_low_alignment_documents),
        )
        filter_trace = [
            {
                "stage": "raw",
                "count": len(rows),
                "target": any(hit.chunk_id == target for _, hit, _ in rows),
                "target_score": next((score for _, hit, score in rows if hit.chunk_id == target), None),
                "top": [
                    {"id": str(hit.chunk_id), "title": hit.document_title, "score": score}
                    for _, hit, score in sorted(rows, key=lambda row: -row[2])[:3]
                ],
            }
        ]
        for name, step in stages:
            rows = step(rows)
            filter_trace.append(
                {
                    "stage": name,
                    "count": len(rows),
                    "target": any(hit.chunk_id == target for _, hit, _ in rows),
                    "target_score": next(
                        (score for _, hit, score in rows if hit.chunk_id == target), None
                    ),
                    "top": [
                        {"id": str(hit.chunk_id), "title": hit.document_title, "score": score}
                        for _, hit, score in sorted(rows, key=lambda row: -row[2])[:3]
                    ],
                }
            )
        output.append(
            {
                "id": case_id,
                "filter_trace": filter_trace,
                "hybrid_target_rank": next(
                    (i + 1 for i, hit in enumerate(result.hits) if hit.chunk_id == target), None
                ),
                "prompt_target_rank": next(
                    (i + 1 for i, hit in enumerate(ranked) if hit.chunk_id == target), None
                ),
                "hybrid_top_ids": [str(hit.chunk_id) for hit in result.hits[:5]],
                "prompt_top": [
                    {"id": str(hit.chunk_id), "title": hit.document_title}
                    for hit in ranked[:6]
                ],
                "ranked_target_excerpt": (
                    query_focused_excerpt(ranked_target_hit.text, question)
                    if ranked_target_hit is not None
                    else None
                ),
                "target_excerpt": (
                    query_focused_excerpt(target_hit.text, question)[:750]
                    if target_hit is not None
                    else None
                ),
            }
        )
    print(json.dumps(output, ensure_ascii=False))


asyncio.run(main())
