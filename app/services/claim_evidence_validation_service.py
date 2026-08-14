from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.citations.models import PromptSourceRegistry
from app.retrieval.question_analysis import fold_text
from app.retrieval.structured import has_explicit_not_specified

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_NUMBER_UNIT_RE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:\([^)]{1,80}\)\s*)?([^\W\d_/%]+|%|vnd|\u0111|\u20ab)",
    re.UNICODE,
)

_MUST_CUES = (
    "phai",
    "bat buoc",
    "yeu cau",
    "can gui",
    "can thuc hien",
    "must",
    "required",
    "needs to",
    "has to",
)
_MUST_NOT_CUES = (
    "khong phai",
    "khong can",
    "khong bat buoc",
    "khong yeu cau",
    "does not need",
    "do not need",
    "not need to",
    "need not",
    "not required",
    "must not",
)
_ALLOWED_CUES = ("duoc phep", "co the", "allowed", "may ")
_NOT_ALLOWED_CUES = (
    "khong duoc",
    "khong the",
    "khong co the",
    "not allowed",
    "may not",
    "cannot",
    "can not",
    "prohibited",
    "forbidden",
)
_AUTO_CUES = ("tu dong", "automatic", "automatically")
_NEGATION_CUES = (
    "khong",
    "not",
    "no ",
    "does not",
    "do not",
    "cannot",
    "can not",
    "may not",
    "khong tu dong",
)
_WITHIN_CUES = ("within", "trong vong", "trong")
_NOT_WITHIN_CUES = ("not within", "khong trong vong", "khong trong")


class ClaimEvidenceStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class ClaimEvidenceValidationResult:
    status: ClaimEvidenceStatus


class ClaimEvidenceValidationService:
    async def validate(
        self,
        *,
        answer: str,
        source_registry: PromptSourceRegistry,
        cited_source_labels: tuple[str, ...],
    ) -> ClaimEvidenceValidationResult:
        if not answer.strip():
            return ClaimEvidenceValidationResult(ClaimEvidenceStatus.INSUFFICIENT)
        evidence = _evidence_for_labels(
            source_registry=source_registry,
            cited_source_labels=cited_source_labels,
        )
        if not evidence.strip():
            return ClaimEvidenceValidationResult(ClaimEvidenceStatus.INSUFFICIENT)
        status = _validate_answer_against_evidence(answer=answer, evidence=evidence)
        return ClaimEvidenceValidationResult(status)


def _validate_answer_against_evidence(*, answer: str, evidence: str) -> ClaimEvidenceStatus:
    folded_answer = fold_text(answer)
    folded_evidence = fold_text(evidence)

    if _polarity_is_contradicted(folded_answer, folded_evidence):
        return ClaimEvidenceStatus.CONTRADICTED
    if _numbers_are_contradicted(folded_answer, folded_evidence):
        return ClaimEvidenceStatus.CONTRADICTED
    if _answer_claims_unspecified_but_source_has_value(
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return ClaimEvidenceStatus.CONTRADICTED
    if _answer_has_grounded_signal(answer=folded_answer, evidence=folded_evidence):
        return ClaimEvidenceStatus.SUPPORTED
    if _answer_is_low_substance(folded_answer):
        return ClaimEvidenceStatus.SUPPORTED
    if has_explicit_not_specified(evidence) and _answer_mentions_unspecified(folded_answer):
        return ClaimEvidenceStatus.SUPPORTED
    return ClaimEvidenceStatus.INSUFFICIENT


def _evidence_for_labels(
    *,
    source_registry: PromptSourceRegistry,
    cited_source_labels: tuple[str, ...],
) -> str:
    parts: list[str] = []
    for label in cited_source_labels:
        marker = f"[{label}]" if not label.startswith("[") else label
        source = source_registry.by_marker(marker)
        if source is not None:
            parts.append(source.text)
    return "\n".join(parts)


def _polarity_is_contradicted(answer: str, evidence: str) -> bool:
    evidence_must_not = _has_any(evidence, _MUST_NOT_CUES)
    answer_must_not = _has_any(answer, _MUST_NOT_CUES)
    evidence_must = _has_any(evidence, _MUST_CUES) and not evidence_must_not
    answer_must = _has_any(answer, _MUST_CUES) and not answer_must_not
    if evidence_must and answer_must_not:
        return True
    if evidence_must_not and answer_must:
        return True

    evidence_not_allowed = _has_any(evidence, _NOT_ALLOWED_CUES)
    answer_not_allowed = _has_any(answer, _NOT_ALLOWED_CUES)
    evidence_allowed = _has_any(evidence, _ALLOWED_CUES) and not evidence_not_allowed
    answer_allowed = _has_any(answer, _ALLOWED_CUES) and not answer_not_allowed
    if evidence_allowed and answer_not_allowed:
        return True
    if evidence_not_allowed and answer_allowed:
        return True

    if _deadline_window_is_contradicted(answer=answer, evidence=evidence):
        return True
    if _has_any(evidence, _AUTO_CUES) and _has_any(answer, _AUTO_CUES):
        evidence_negative = _has_any(evidence, _NEGATION_CUES)
        answer_negative = _has_any(answer, _NEGATION_CUES)
        return evidence_negative != answer_negative
    return False


def _deadline_window_is_contradicted(*, answer: str, evidence: str) -> bool:
    evidence_mentions_deadline = _has_any(evidence, _WITHIN_CUES)
    answer_mentions_deadline = _has_any(answer, _WITHIN_CUES)
    if not evidence_mentions_deadline or not answer_mentions_deadline:
        return False
    evidence_not_within = _has_any(evidence, _NOT_WITHIN_CUES)
    answer_not_within = _has_any(answer, _NOT_WITHIN_CUES)
    if _has_any(evidence, _MUST_CUES) and not evidence_not_within and answer_not_within:
        return True
    return evidence_not_within and not answer_not_within


def _numbers_are_contradicted(answer: str, evidence: str) -> bool:
    answer_pairs = set(_number_unit_pairs(answer))
    evidence_pairs = set(_number_unit_pairs(evidence))
    if answer_pairs and evidence_pairs and answer_pairs.isdisjoint(evidence_pairs):
        return True
    answer_numbers = set(_numbers(answer))
    evidence_numbers = set(_numbers(evidence))
    return bool(answer_numbers and evidence_numbers and answer_numbers.isdisjoint(evidence_numbers))


def _answer_claims_unspecified_but_source_has_value(*, answer: str, evidence: str) -> bool:
    return _answer_mentions_unspecified(answer) and bool(_number_unit_pairs(evidence))


def _answer_has_grounded_signal(*, answer: str, evidence: str) -> bool:
    answer_pairs = set(_number_unit_pairs(answer))
    if answer_pairs and answer_pairs.issubset(set(_number_unit_pairs(evidence))):
        return True
    answer_numbers = set(_numbers(answer))
    if answer_numbers and answer_numbers.issubset(set(_numbers(evidence))):
        return True
    substantive_terms = {
        term
        for term in re.findall(r"\w+", answer)
        if len(term) >= 4 and term not in {"khong", "duoc", "phai", "trong", "answer"}
    }
    if len(substantive_terms) < 2:
        return False
    matched = {term for term in substantive_terms if term in evidence}
    return len(matched) >= min(3, len(substantive_terms))


def _answer_is_low_substance(answer: str) -> bool:
    terms = {
        term
        for term in re.findall(r"\w+", answer)
        if len(term) >= 4 and term not in {"khong", "duoc", "phai", "trong", "answer"}
    }
    return len(terms) <= 3


def _answer_mentions_unspecified(answer: str) -> bool:
    return any(
        cue in answer
        for cue in (
            "khong quy dinh",
            "khong neu",
            "khong xac dinh",
            "khong co ty le co dinh",
            "does not specify",
            "does not state",
            "not fixed",
            "no fixed",
        )
    )


def _number_unit_pairs(text: str) -> tuple[tuple[str, str], ...]:
    pairs = []
    for match in _NUMBER_UNIT_RE.finditer(text):
        number = match.group(1).replace(",", ".")
        unit = match.group(2).strip("_ ")
        pairs.append((number, unit))
    return tuple(pairs)


def _numbers(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).replace(",", ".") for match in _NUMBER_RE.finditer(text))


def _has_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)
