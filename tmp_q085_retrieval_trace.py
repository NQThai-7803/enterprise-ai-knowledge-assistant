from __future__ import annotations

import asyncio
import json
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models import User
from app.retrieval.factory import create_hybrid_retrieval_service
from app.retrieval.question_analysis import analyze_question
from app.services import grounded_answer_service as ga
from app.services.grounded_answer_service import _rank_hits_for_prompt


async def main() -> None:
    question = "Tiền mua đồ ergonomic được hỗ trợ bao nhiêu và bao lâu được một lần?"
    target = UUID("ff2c5c5d-26f4-493a-aa17-ae12544f668c")
    async with async_session_factory() as session:
        user = await session.scalar(
            select(User).where(User.id == UUID("397e8ccc-c012-4aad-8d0c-88ad7a12f985"))
        )
    assert user is not None
    retrieval = create_hybrid_retrieval_service(get_settings())
    result = await retrieval.retrieve(query=question, current_user=user, top_k=50)
    keyword = await retrieval.keyword_retrieval_service.retrieve(
        query=question, current_user=user, top_k=100, min_keyword_rank=0.0
    )
    ranked = _rank_hits_for_prompt(result.hits, question=question)
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
        {"stage": "raw", "count": len(rows), "target": any(hit.chunk_id == target for _, hit, _ in rows)}
    ]
    for name, step in stages:
        rows = step(rows)
        filter_trace.append(
            {
                "stage": name,
                "count": len(rows),
                "target": any(hit.chunk_id == target for _, hit, _ in rows),
                "target_score": next((score for _, hit, score in rows if hit.chunk_id == target), None),
            }
        )
    output = {
        "filter_trace": filter_trace,
        "hybrid_target_rank": next(
            (i + 1 for i, hit in enumerate(result.hits) if hit.chunk_id == target), None
        ),
        "keyword_target_rank": next(
            (i + 1 for i, hit in enumerate(keyword.hits) if hit.chunk_id == target), None
        ),
        "prompt_target_rank": next(
            (i + 1 for i, hit in enumerate(ranked) if hit.chunk_id == target), None
        ),
        "hybrid_top": [
            {"id": str(hit.chunk_id), "title": hit.document_title, "ergonomic": "ergonomic" in hit.text.lower()}
            for hit in result.hits[:12]
        ],
        "keyword_top": [
            {"id": str(hit.chunk_id), "title": hit.document_title, "ergonomic": "ergonomic" in hit.text.lower()}
            for hit in keyword.hits[:12]
        ],
        "prompt_top": [
            {"id": str(hit.chunk_id), "title": hit.document_title, "ergonomic": "ergonomic" in hit.text.lower()}
            for hit in ranked[:12]
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


asyncio.run(main())
