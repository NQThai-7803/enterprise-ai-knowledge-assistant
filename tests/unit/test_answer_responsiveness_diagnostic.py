"""Synthetic 035.3C.1 controls; known relevance gaps remain expected failures.

These tests use pure validation and scoring functions. They do not create a
database session, call a model, or access either Docker project.
"""

import pytest

from app.retrieval.reranker import _normalize_scores
from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    _validate_answer_against_evidence,
)


@pytest.mark.parametrize(
    ("question", "answer"),
    [
        (
            "What approval is needed before shipping a microscope?",
            "After a printer fault, supervisors arrange rest breaks.",
        ),
        (
            "What approval is needed before shipping a microscope?",
            "Sau sự cố máy in, quản lý bố trí thời gian nghỉ hợp lý cho nhân viên.",
        ),
    ],
)
@pytest.mark.xfail(
    strict=True,
    reason="Known defect: verbatim source support does not establish question responsiveness",
)
def test_unrelated_verbatim_clause_must_not_answer_question(question: str, answer: str) -> None:
    assert (
        _validate_answer_against_evidence(question=question, answer=answer, evidence=answer)
        == ClaimEvidenceStatus.INSUFFICIENT
    )


def test_vietnamese_conditional_question_rejects_unrelated_clause() -> None:
    question = "Trước khi giao máy đo, nhân viên cần phê duyệt gì?"
    answer = "Sau sự cố máy in, quản lý bố trí thời gian nghỉ hợp lý cho nhân viên."
    assert (
        _validate_answer_against_evidence(question=question, answer=answer, evidence=answer)
        == ClaimEvidenceStatus.INSUFFICIENT
    )


@pytest.mark.parametrize(
    ("question", "answer"),
    [
        (
            "What approval is needed before shipping a microscope?",
            "Workers need director approval before shipping a microscope.",
        ),
        (
            "What approval is needed before shipping a microscope?",
            "Nhân viên cần trưởng bộ phận phê duyệt trước khi giao máy đo.",
        ),
    ],
)
def test_relevant_verbatim_clause_remains_supported(question: str, answer: str) -> None:
    assert (
        _validate_answer_against_evidence(question=question, answer=answer, evidence=answer)
        == ClaimEvidenceStatus.SUPPORTED
    )


@pytest.mark.xfail(
    strict=True,
    reason="Current validation can reject a responsive Vietnamese conditional clause",
)
def test_relevant_vietnamese_conditional_clause_must_remain_supported() -> None:
    question = "Trước khi giao máy đo, nhân viên cần phê duyệt gì?"
    answer = "Nhân viên cần trưởng bộ phận phê duyệt trước khi giao máy đo."
    assert (
        _validate_answer_against_evidence(question=question, answer=answer, evidence=answer)
        == ClaimEvidenceStatus.SUPPORTED
    )


def test_normalized_reranker_zero_is_a_relative_boundary() -> None:
    assert _normalize_scores((2.0, 9.0)) == (0.0, 100.0)
    assert _normalize_scores((2.0,)) == (50.0,)
    assert _normalize_scores((2.0, 2.0)) == (50.0, 50.0)
