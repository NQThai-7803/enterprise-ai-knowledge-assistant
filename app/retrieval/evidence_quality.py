from __future__ import annotations

import re
from enum import StrEnum

from app.retrieval.question_analysis import fold_text


class EvidenceContextKind(StrEnum):
    ANSWER = "answer"
    QUESTION_LIST = "question_list"
    REFERENCE = "reference"


QUESTION_LIST_CONTEXT_CUES = (
    "cau hoi goi y",
    "cau hoi kiem thu",
    "cau hoi tham khao",
    "cau hoi mau",
    "tinh huong mau",
    "ky vong cau tra loi",
    "cau tra loi ai",
    "sample scenario",
    "example scenario",
    "expected answer",
    "expected ai answer",
    "suggested question",
    "test question",
    "sample question",
    "kiem thu rag",
    "testing rag",
    "no-answer test",
)

_STRONG_QUESTION_LIST_CONTEXT_CUES = (
    "cau hoi kiem thu",
    "ky vong cau tra loi",
    "cau tra loi ai",
    "expected answer",
    "expected ai answer",
    "kiem thu rag",
    "testing rag",
    "no-answer test",
)

REFERENCE_CONTEXT_CUES = (
    "muc luc",
    "danh muc tai lieu",
    "tai lieu lien quan",
    "lich su phien ban",
    "kiem soat tai lieu",
    "table of contents",
    "related documents",
    "version history",
)

_ANSWER_BEARING_CUES = (
    "answer:",
    "tra loi:",
    "dap an:",
    "la ",
    "is ",
    "are ",
    "duoc ",
    "khong duoc ",
    "khong co ",
    "khong quy dinh",
)
_VALUE_EXPRESSION = re.compile(
    r"(?<!\d)\d+(?:[.,]\d+)?\s*(?:%|dong|trieu|ngay|gio|tuan|thang|nam|days?|hours?|weeks?|months?|years?)\b"
)
_STRONG_QUESTION_LIST_CONTEXT_PATTERNS = (
    re.compile(r"\bcau hoi kiem\s+(?:\d+\s+)?thu rag\b"),
    re.compile(r"\bky vong\s+cau tra loi\b"),
)


def classify_evidence_context(text: str) -> EvidenceContextKind:
    folded = fold_text(text)
    if any(cue in folded for cue in _STRONG_QUESTION_LIST_CONTEXT_CUES) or any(
        pattern.search(folded) for pattern in _STRONG_QUESTION_LIST_CONTEXT_PATTERNS
    ):
        return EvidenceContextKind.QUESTION_LIST
    if any(cue in folded for cue in QUESTION_LIST_CONTEXT_CUES) and not _has_answer_bearing_content(
        text, folded
    ):
        return EvidenceContextKind.QUESTION_LIST
    if any(cue in folded for cue in REFERENCE_CONTEXT_CUES):
        return EvidenceContextKind.REFERENCE
    return EvidenceContextKind.ANSWER


def is_non_answer_context(text: str) -> bool:
    return classify_evidence_context(text) != EvidenceContextKind.ANSWER


def _has_answer_bearing_content(text: str, folded: str) -> bool:
    """Allow FAQ/Q&A records while rejecting question-only/sample scaffolding."""
    if _VALUE_EXPRESSION.search(folded):
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    return any(cue in folded for cue in _ANSWER_BEARING_CUES) and any(
        not line.endswith("?") and not line.endswith("?") for line in lines[1:]
    )
