"""Offline TASK-035.3E admission contract; invented evidence, no DB fixtures.

Failures intentionally expose current context-selection behavior. The expected
sets describe question-material evidence, not production answer assertions.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest

from app.chat.context_builder import select_context_for_prompt
from app.citations.models import PromptSource, PromptSourceRegistry
from app.models import CitationSourceType
from app.retrieval.models import HybridRetrievalHit
from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    ClaimEvidenceValidationService,
)


class _Counter:
    def count(self, text: str) -> int:
        return len(text.split())


def _hit(
    index: int, text: str, *, channel: str = "semantic", score: float = 1.0
) -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=UUID(int=index),
        document_id=UUID(int=1000 + index),
        document_title=f"Invented source {index}",
        chunk_index=0,
        text=text,
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=len(text.split()),
        hybrid_score=0.017,
        semantic_score=0.7 if channel == "semantic" else None,
        semantic_rank=1 if channel == "semantic" else None,
        keyword_score=0.1 if channel == "keyword" else None,
        keyword_rank=1 if channel == "keyword" else None,
        matched_by=(channel,),
        reranker_score=score,
    )


# Param IDs that still fail on the open S01 safety blocker. Only these are xfail(strict):
# a fix turns them into XPASS failures so the marker must be removed deliberately.
_S01_OPEN = frozenset(
    {
        "C_irrelevant_accessible",
        "D_mixed_accessible",
        "J_wrong_relation",
        "K_unrelated_number",
        "L_reversed_prohibition_final_claim",
        "M_incomplete_final_claim",
    }
)


def _mark_open_s01(request: pytest.FixtureRequest) -> None:
    param_id = request.node.callspec.id
    if param_id in _S01_OPEN:
        request.applymarker(pytest.mark.xfail(strict=True, reason=f"S01 open: {param_id}"))


# The private source in B is deliberately absent from the authorized hit input;
# upstream RBAC is tested separately. Other cases exercise only admission.
_CASES = (
    (
        "A_relevant_accessible",
        "Who signs off archive loans?",
        ("The curator signs off archive loans.",),
        (1,),
    ),
    ("B_private_only", "Who signs off archive loans?", (), ()),
    (
        "C_irrelevant_accessible",
        "Who signs off archive loans?",
        ("After equipment faults, supervisors schedule rest breaks.",),
        (),
    ),
    (
        "D_mixed_accessible",
        "Who signs off archive loans?",
        (
            "The curator signs off archive loans.",
            "After equipment faults, supervisors schedule rest breaks.",
        ),
        (1,),
    ),
    (
        "E_vietnamese_paraphrase",
        "Who authorizes archive loans?",
        ("Việc mượn hiện vật lưu trữ cần người phụ trách bảo tàng chấp thuận.",),
        (1,),
    ),
    (
        "F_english_paraphrase",
        "Who authorizes archive loans?",
        ("The museum curator must approve borrowing archival objects.",),
        (1,),
    ),
    (
        "G_mixed_language",
        "Who approves a field-kit checkout?",
        ("Phiếu checkout bộ dụng cụ dã ngoại cần curator phê duyệt trước khi nhận.",),
        (1,),
    ),
    (
        "H_conditional",
        "When may a researcher take a specimen home?",
        (
            "Only when the lab is closed for maintenance may a researcher take a "
            "specimen home, after written custodian approval.",
        ),
        (1,),
    ),
    (
        "I_multi_document",
        "Who authorizes a specimen transfer and what record is required?",
        (
            "The custodian authorizes specimen transfers.",
            "A specimen transfer requires a signed chain-of-custody form.",
        ),
        (1, 2),
    ),
    (
        "J_wrong_relation",
        "Who approves a field-kit checkout?",
        ("The field-kit custodian records the checkout after it occurs.",),
        (),
    ),
    (
        "K_unrelated_number",
        "How many days may a specimen be retained?",
        ("The visitor badge is valid for 14 days.",),
        (),
    ),
    # Contradictory and partial evidence remain useful context for correcting a
    # premise or refusing a complete answer. Admission is not an entailment verdict.
    (
        "L_reversed_prohibition",
        "May a researcher remove specimens without approval?",
        ("Researchers must never remove specimens without approval.",),
        (1,),
    ),
    (
        "M_incomplete",
        "What approvals are required to transfer a specimen?",
        (
            "A transfer request is reviewed by the custodian; additional "
            "authorization rules are in another procedure.",
        ),
        (1,),
    ),
    ("N_no_authorized_support", "Who authorizes a specimen transfer?", (), ()),
    (
        "O_keyword_fallback",
        "What document records a field-kit checkout?",
        ("The checkout ledger records each field-kit loan.",),
        (1,),
    ),
)


@pytest.mark.parametrize(
    "case_id, question, texts, expected_indexes", _CASES, ids=[case[0] for case in _CASES]
)
def test_only_question_material_authorized_evidence_is_admitted(
    request: pytest.FixtureRequest,
    case_id: str,
    question: str,
    texts: tuple[str, ...],
    expected_indexes: tuple[int, ...],
) -> None:
    _mark_open_s01(request)
    hits = tuple(
        _hit(
            index,
            text,
            channel="keyword" if case_id == "O_keyword_fallback" else "semantic",
            score=0.0 if case_id == "E_vietnamese_paraphrase" else 1.0,
        )
        for index, text in enumerate(texts, start=1)
    )
    selected = select_context_for_prompt(
        hits=hits,
        history_messages=(),
        question=question,
        system_prompt="Answer only from authorized material evidence.",
        token_counter=_Counter(),
        max_tokens=2000,
    )

    assert tuple(item.chunk_id.int for item in selected.items) == expected_indexes


@pytest.mark.parametrize(
    "case_id, question, answer, evidence, expected",
    (
        (
            "L_reversed_prohibition_final_claim",
            "May a researcher remove specimens without approval?",
            "Yes, researchers may remove specimens without approval.",
            "Researchers must never remove specimens without approval.",
            ClaimEvidenceStatus.CONTRADICTED,
        ),
        (
            "M_incomplete_final_claim",
            "What approvals are required to transfer a specimen?",
            "A transfer request is reviewed by the custodian.",
            "A transfer request is reviewed by the custodian; additional "
            "authorization rules are in another procedure.",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
    ),
    ids=("L_reversed_prohibition_final_claim", "M_incomplete_final_claim"),
)
def test_admitted_context_is_not_complete_final_answer_support(
    request: pytest.FixtureRequest,
    case_id: str,
    question: str,
    answer: str,
    evidence: str,
    expected: ClaimEvidenceStatus,
) -> None:
    _mark_open_s01(request)
    source = PromptSource(
        marker="[SOURCE_1]",
        source_type=CitationSourceType.INTERNAL,
        document_title="Invented specimen procedure",
        text=evidence,
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        hybrid_score=0.017,
        chunk_id=UUID(int=1),
        document_id=UUID(int=1001),
    )
    result = asyncio.run(
        ClaimEvidenceValidationService().validate(
            question=question,
            answer=answer,
            source_registry=PromptSourceRegistry(sources=(source,)),
            cited_source_labels=(source.label,),
        )
    )
    assert result.status == expected, case_id
