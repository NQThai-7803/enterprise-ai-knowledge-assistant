"""Test-first, synthetic question/evidence/answer responsiveness controls.

This unit contract has no database, Docker, network, model, or benchmark fixture.
Authorization, citation mapping, and final persistence need separate tests.
"""

import asyncio
from uuid import UUID

import pytest

from app.citations.models import PromptSource, PromptSourceRegistry
from app.models import CitationSourceType
from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    ClaimEvidenceValidationService,
)


@pytest.mark.parametrize(
    ("case", "question", "answer", "evidence", "expected"),
    [
        (
            "A_accessible_material_clause",
            "Who must approve shipment of the spectrometer?",
            "The laboratory director must approve shipment of the spectrometer.",
            "The laboratory director must approve shipment of the spectrometer.",
            ClaimEvidenceStatus.SUPPORTED,
        ),
        (
            "B_private_source_excluded_from_registry",
            "Who must approve shipment of the spectrometer?",
            "The laboratory director approves it.",
            "",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
        (
            "C_only_irrelevant_accessible_clause",
            "Who must approve shipment of the spectrometer?",
            "After a printer fault, supervisors arrange rest breaks.",
            "After a printer fault, supervisors arrange rest breaks.",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
        (
            "D_grounded_nonresponsive_vietnamese_claim",
            "Who must approve shipment of the spectrometer?",
            "Sau sự cố máy in, quản lý bố trí giờ nghỉ cho nhân viên.",
            "Sau sự cố máy in, quản lý bố trí giờ nghỉ cho nhân viên.",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
        (
            "E_vietnamese_semantic_paraphrase",
            "Ai phải đồng ý trước khi gửi máy quang phổ?",
            "Trưởng phòng thí nghiệm cần phê duyệt việc chuyển máy quang phổ.",
            "Trước khi vận chuyển máy quang phổ, phải có sự chấp thuận của "
            "trưởng phòng thí nghiệm.",
            ClaimEvidenceStatus.SUPPORTED,
        ),
        (
            "F_english_semantic_paraphrase",
            "Who must authorize dispatch of the spectrometer?",
            "The laboratory director must approve sending the spectrometer.",
            "A spectrometer may be dispatched only after sign-off by the laboratory director.",
            ClaimEvidenceStatus.SUPPORTED,
        ),
        (
            "G_mixed_english_vietnamese_terminology",
            "Who approves sending the spectrometer?",
            "The laboratory director approves sending the spectrometer.",
            "Giám đốc phòng thí nghiệm phê duyệt việc gửi máy quang phổ.",
            ClaimEvidenceStatus.SUPPORTED,
        ),
        (
            "H_two_material_documents",
            "What must happen before dispatching the sealed sample?",
            "The seal must be inspected and the supervisor must sign the dispatch log.",
            "Inspect the seal before dispatching the sample.\n\n"
            "The supervisor must sign the dispatch log before sample dispatch.",
            ClaimEvidenceStatus.SUPPORTED,
        ),
        (
            "I_false_premise",
            "May a courier dispatch the sample without a supervisor signature?",
            "No. The supervisor must sign before the sample is dispatched.",
            "The supervisor must sign before the sample is dispatched.",
            ClaimEvidenceStatus.SUPPORTED,
        ),
        (
            "J_obligation_reversal",
            "Must the supervisor sign before sample dispatch?",
            "The supervisor need not sign before sample dispatch.",
            "The supervisor must sign before sample dispatch.",
            ClaimEvidenceStatus.CONTRADICTED,
        ),
        (
            "K_conditional_requirement_retained",
            "When may the sealed sample be dispatched?",
            "Only after seal inspection may the sample be dispatched.",
            "Only after seal inspection may the sample be dispatched.",
            ClaimEvidenceStatus.SUPPORTED,
        ),
        (
            "L_same_number_unrelated_topic",
            "How many hours of training must a courier complete?",
            "The printer must cool for 4 hours after maintenance.",
            "The printer must cool for 4 hours after maintenance.",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
        (
            "M_repaired_final_claim_must_be_rechecked",
            "Who must sign the sample dispatch log?",
            "The printer technician signs the maintenance record.",
            "The printer technician signs the maintenance record.",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
        (
            "N_missing_material_condition",
            "What must happen before the sealed sample is dispatched?",
            "The supervisor signs the dispatch log.",
            "The seal must be inspected and the supervisor must sign "
            "the dispatch log before sample dispatch.",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
        (
            "O_no_authorized_evidence",
            "Who approves sending the spectrometer?",
            "The laboratory director approves it.",
            "",
            ClaimEvidenceStatus.INSUFFICIENT,
        ),
    ],
    ids=[
        "A_accessible_material_clause",
        "B_private_source_excluded",
        "C_irrelevant_accessible",
        "D_grounded_nonresponsive_vi",
        "E_vietnamese_paraphrase",
        "F_english_paraphrase",
        "G_mixed_language",
        "H_two_documents",
        "I_false_premise",
        "J_obligation_reversal",
        "K_conditional_requirement",
        "L_unrelated_same_number",
        "M_repaired_claim_recheck",
        "N_missing_condition",
        "O_no_authorized_evidence",
    ],
)
def test_synthetic_question_responsiveness_contract(
    case: str,
    question: str,
    answer: str,
    evidence: str,
    expected: ClaimEvidenceStatus,
) -> None:
    paragraphs = tuple(part for part in evidence.split("\n\n") if part)
    sources = tuple(
        PromptSource(
            marker=f"[SOURCE_{index}]",
            source_type=CitationSourceType.INTERNAL,
            document_title=f"Synthetic policy {index}",
            text=part,
            page_numbers=(1,),
            start_page=1,
            end_page=1,
            hybrid_score=1.0,
            chunk_id=UUID(int=index),
            document_id=UUID(int=100 + index),
        )
        for index, part in enumerate(paragraphs, start=1)
    )
    result = asyncio.run(
        ClaimEvidenceValidationService().validate(
            question=question,
            answer=answer,
            source_registry=PromptSourceRegistry(sources=sources),
            cited_source_labels=tuple(source.label for source in sources),
        )
    )
    assert result.status == expected, case
