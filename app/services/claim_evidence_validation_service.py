from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.citations.models import PromptSourceRegistry
from app.retrieval.evidence_quality import is_non_answer_context
from app.retrieval.question_analysis import analyze_question, fold_text, retrieval_query_variants
from app.retrieval.structured import has_explicit_not_specified

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_CLOCK_VALUE_RE = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3])\s*(?::|h|gio)\s*[0-5]\d(?!\d)")
_NUMBER_UNIT_RE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:\([^)]{1,80}\)\s*)?([^\W\d_/%]+|%|vnd|\u0111|\u20ab)",
    re.UNICODE,
)

_MULTI_VALUE_YES_NO_CUES = (
    "moi",
    "tat ca",
    "deu",
    "all",
    "every",
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

_YES_NO_FOCUS_STOP_TERMS = frozenset(
    {
        "co",
        "duoc",
        "khong",
        "phai",
        "dung",
        "la",
        "ve",
        "cua",
        "cho",
        "hay",
        "thi",
        "yes",
        "no",
        "is",
        "are",
        "do",
        "does",
        "can",
    }
)

_YES_NO_POSITIVE_NEGATION_CUES = (
    "khong cam",
    "khong bi han che",
    "khong bi gioi han",
    "not prohibited",
    "not restricted",
    "not forbidden",
)

_YES_NO_EXTRA_NEGATIVE_CUES = (
    "khong thay the",
    "does not replace",
    "do not replace",
    "not replace",
)

_YES_NO_GENERIC_NEGATIVE_CUES = (
    "khong ",
    "not ",
    "does not ",
    "do not ",
    "cannot ",
    "can not ",
    "may not ",
)

_YES_NO_NON_POLAR_NEGATION_CUES = (
    "khong chi",
    "khong nhung",
    "not only",
)

_YES_NO_EXTRA_POSITIVE_CUES = (
    "co quyen",
    "duoc quyen",
    "entitled",
)

_YES_NO_SELF_REFERENCE_CUES = (
    "chinh minh",
    "cua minh",
    "ban than",
    "own",
    "their own",
    "his own",
    "her own",
)

_PERSON_LOOKUP_STOP_TERMS = frozenset(
    {
        "ai",
        "ban",
        "bo",
        "ceo",
        "cfo",
        "chro",
        "cong",
        "coo",
        "cto",
        "cua",
        "digital",
        "doc",
        "don",
        "giam",
        "la",
        "nghe",
        "nhan",
        "nova",
        "phan",
        "phong",
        "phu",
        "su",
        "tai",
        "tech",
        "technology",
        "tong",
        "trach",
        "tro",
        "vai",
        "vi",
        "who",
    }
)
_YES_NO_OTHER_REFERENCE_CUES = (
    "nguoi khac",
    "nhan vien khac",
    "nguoi lao dong khac",
    "dong nghiep khac",
    "other employee",
    "other employees",
    "another employee",
    "others",
)

_REPLACEMENT_RELATION_CUES = (
    "thay the",
    "replace",
    "replaces",
    "replacing",
    "substitute",
    "substitutes",
)

_PRIMARY_RELATION_CUES = (
    "bat buoc",
    "theo luat",
    "mandatory",
    "required",
    "statutory",
    "compulsory",
)

_SUPPLEMENTAL_RELATION_CUES = (
    "bo sung",
    "bo tro",
    "them",
    "tang cuong",
    "additional",
    "supplementary",
    "supplemental",
    "extra",
    "optional",
)

_RELATION_ENTITY_STOP_TERMS = _YES_NO_FOCUS_STOP_TERMS.union(
    {
        "thay",
        "the",
        "replace",
        "replaces",
        "replacing",
        "substitute",
        "substitutes",
        "bat",
        "buoc",
        "theo",
        "luat",
        "mandatory",
        "required",
        "statutory",
        "compulsory",
        "bo",
        "sung",
        "tro",
        "them",
        "tang",
        "cuong",
        "additional",
        "supplementary",
        "supplemental",
        "extra",
        "optional",
        "bao",
        "dam",
        "lam",
        "viec",
        "hiem",
        "suc",
        "khoe",
        "health",
        "insurance",
        "plan",
        "program",
        "che",
        "do",
        "loai",
        "hinh",
        "category",
    }
)

_YES_NO_REQUIRED_ANCHOR_STOP_TERMS = _RELATION_ENTITY_STOP_TERMS.union(
    {
        "nhan",
        "vien",
        "nguoi",
        "lao",
        "dong",
        "noi",
        "dung",
        "van",
        "quan",
        "muc",
        "luong",
        "chinh",
        "minh",
        "gui",
        "chuyen",
        "tu",
        "to",
        "for",
        "with",
    }
)

_VALUE_ALIGNMENT_STOP_TERMS = frozenset(
    {
        "bao",
        "nhieu",
        "may",
        "nao",
        "duoc",
        "theo",
        "muc",
        "toi",
        "da",
        "ngay",
        "gio",
        "tuan",
        "thang",
        "nam",
        "phan",
        "tram",
        "dong",
        "vnd",
        "tien",
        "phu",
        "cap",
        "ho",
        "tro",
        "lam",
        "moi",
        "amount",
        "value",
        "salary",
        "allowance",
        "percent",
        "percentage",
        "much",
        "many",
        "what",
        "which",
        "thuong",
        "thi",
    }
)

_CLAIM_ALIGNMENT_STOP_TERMS = frozenset(
    {
        "nhan",
        "vien",
        "nguoi",
        "lao",
        "dong",
        "cong",
        "ty",
        "co",
        "khong",
        "duoc",
        "phai",
        "thi",
        "la",
        "gi",
        "nao",
        "cua",
        "cho",
        "ve",
        "theo",
        "yeu",
        "cau",
        "bao",
        "dam",
        "lam",
        "viec",
        "what",
        "which",
        "who",
        "how",
        "is",
        "are",
        "the",
        "and",
        "for",
        "does",
        "required",
    }
)

_VALUE_CONDITION_CUES = {
    "weekly_rest": (
        "chu nhat",
        "nghi hang tuan",
        "nghi hang tuan",
        "weekly rest",
        "weekend",
        "sunday",
    ),
    "holiday": ("ngay le", "tet", "holiday", "public holiday"),
    "normal_workday": (
        "ngay lam viec binh thuong",
        "normal workday",
        "weekday",
    ),
    "night": ("ban dem", "ca dem", "night work", "night shift"),
}

_SPECIFIC_VALUE_FIELD_CUES = (
    "noi tru",
    "inpatient",
    "ngoai tru",
    "outpatient",
    "an trua",
    "lunch",
    "nha khoa",
    "dental",
    "thai san",
    "maternity",
    "tai nan",
    "accident",
)

_SECURITY_CONTROL_CUES = (
    "ket noi an toan",
    "xac thuc nhieu lop",
    "thiet bi duoc phe duyet",
    "thiet bi duoc quan ly",
    "khong de nguoi khong co tham quyen",
    "ma hoa",
    "multi factor",
    "managed device",
    "safe connection",
    "unauthorized",
    "vpn",
    "mfa",
)


class ClaimEvidenceStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class ClaimEvidenceValidationResult:
    status: ClaimEvidenceStatus
    polarity: str | None = None


def _question_focused_evidence_polarity(
    *,
    question: str,
    evidence: str,
) -> str | None:
    segments = _question_focused_evidence_segments(
        question=question,
        evidence=evidence,
    )

    for segment in segments:
        polarity = infer_yes_no_polarity(segment)

        if polarity is not None:
            return polarity

    return None


def infer_yes_no_polarity(text: str) -> str | None:
    folded = fold_text(text).strip()

    explicit = re.match(
        r"^(co|khong|yes|no)\s*[.,:;!?-]",
        folded,
    )
    if explicit is not None:
        token = explicit.group(1)
        return "YES" if token in {"co", "yes"} else "NO"

    if folded in {"co", "yes"}:
        return "YES"

    if folded in {"khong", "no"}:
        return "NO"

    if _has_any(folded, _YES_NO_POSITIVE_NEGATION_CUES):
        return "YES"

    if (
        _has_any(folded, _NOT_ALLOWED_CUES)
        or _has_any(folded, _MUST_NOT_CUES)
        or _has_any(folded, _YES_NO_EXTRA_NEGATIVE_CUES)
    ):
        return "NO"

    if _has_any(
        folded,
        _YES_NO_GENERIC_NEGATIVE_CUES,
    ) and not _has_any_phrase(
        folded,
        _YES_NO_NON_POLAR_NEGATION_CUES,
    ):
        return "NO"

    if (
        _has_any(folded, _ALLOWED_CUES)
        or _has_any(folded, _MUST_CUES)
        or _has_any(folded, _YES_NO_EXTRA_POSITIVE_CUES)
    ):
        return "YES"

    return None


def _is_multi_value_yes_no_question(
    question: str,
) -> bool:
    if not analyze_question(question).is_yes_no:
        return False

    folded_question = fold_text(retrieval_query_variants(question).normalized)

    return any(cue in folded_question for cue in _MULTI_VALUE_YES_NO_CUES)


def _multi_value_yes_no_answer_is_supported(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    if not _is_multi_value_yes_no_question(question):
        return False

    if infer_yes_no_polarity(answer) != "NO":
        return False

    folded_answer = fold_text(answer)
    folded_evidence = fold_text(evidence)

    if _answer_lists_multiple_supported_values(
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return True

    return _evidence_contains_alternative_value_for_question(
        question=question,
        evidence=evidence,
    )


def _answer_lists_multiple_supported_values(*, answer: str, evidence: str) -> bool:
    answer_pairs = set(_number_unit_pairs(answer))
    evidence_pairs = set(_number_unit_pairs(evidence))
    if len(answer_pairs) < 2:
        return False
    if not answer_pairs.issubset(evidence_pairs):
        return False
    answer_numbers = {number for number, _ in answer_pairs}
    return len(answer_numbers) >= 2


def _evidence_contains_alternative_value_for_question(
    *,
    question: str,
    evidence: str,
) -> bool:
    folded_question = fold_text(question)
    folded_evidence = fold_text(evidence)
    question_pairs = tuple(dict.fromkeys(_number_unit_pairs(folded_question)))
    if not question_pairs:
        return False
    evidence_pairs = tuple(_number_unit_pairs(folded_evidence))
    if not evidence_pairs:
        return False
    if not _multi_value_focus_matches_question(question=question, evidence=evidence):
        return False
    for question_number, question_unit in question_pairs:
        same_unit_numbers = {
            evidence_number
            for evidence_number, evidence_unit in evidence_pairs
            if evidence_unit == question_unit
        }
        if question_number in same_unit_numbers and len(same_unit_numbers) >= 2:
            return True
    return False


def _multi_value_focus_matches_question(
    *,
    question: str,
    evidence: str,
) -> bool:
    focus_terms = frozenset(
        term
        for term in _yes_no_question_focus_terms(question)
        if term
        not in {
            "moi",
            "tat",
            "ca",
            "deu",
            "all",
            "every",
            "nhan",
            "vien",
            "nguoi",
            "lao",
            "dong",
            "employee",
            "employees",
            "day",
            "days",
            "gio",
            "ngay",
            "nam",
            "thang",
            "tuan",
            "year",
            "years",
            "month",
            "months",
            "week",
            "weeks",
        }
    )
    if not focus_terms:
        return True
    return _yes_no_focus_match_count(text=evidence, focus_terms=focus_terms) >= 1


class ClaimEvidenceValidationService:
    async def validate(
        self,
        *,
        answer: str,
        source_registry: PromptSourceRegistry,
        cited_source_labels: tuple[str, ...],
        question: str | None = None,
        require_subject_attribute_alignment: bool = False,
    ) -> ClaimEvidenceValidationResult:
        if not answer.strip():
            return ClaimEvidenceValidationResult(ClaimEvidenceStatus.INSUFFICIENT)

        evidence = _evidence_for_labels(
            source_registry=source_registry,
            cited_source_labels=cited_source_labels,
        )

        if not evidence.strip():
            return ClaimEvidenceValidationResult(ClaimEvidenceStatus.INSUFFICIENT)

        status = _validate_answer_against_evidence(
            answer=answer,
            evidence=evidence,
            question=question,
            require_subject_attribute_alignment=require_subject_attribute_alignment,
        )

        validated_polarity: str | None = None

        if (
            status == ClaimEvidenceStatus.SUPPORTED
            and question is not None
            and analyze_question(question).is_yes_no
        ):
            validated_polarity = infer_yes_no_polarity(answer)

            if validated_polarity is None:
                validated_polarity = _question_focused_evidence_polarity(
                    question=question,
                    evidence=evidence,
                )

        return ClaimEvidenceValidationResult(
            status=status,
            polarity=validated_polarity,
        )

    def select_supporting_source_labels(
        self,
        *,
        answer: str,
        source_registry: PromptSourceRegistry,
        question: str,
        preferred_source_labels: tuple[str, ...] = (),
        max_sources: int = 2,
    ) -> tuple[str, ...]:
        preferred = {
            label.strip()[1:-1] if label.strip().startswith("[") else label.strip()
            for label in preferred_source_labels
            if label.strip()
        }

        supported: list[tuple[float, int, str]] = []
        for index, source in enumerate(source_registry.sources):
            if is_non_answer_context(source.text):
                continue

            status = _validate_answer_against_evidence(
                answer=answer,
                evidence=source.text,
                question=question,
            )
            if status != ClaimEvidenceStatus.SUPPORTED:
                continue

            score = _supporting_source_score(
                question=question,
                answer=answer,
                evidence=source.text,
            )
            if source.label in preferred:
                score += 2.0
            supported.append((score, index, source.label))

        if supported:
            return tuple(
                label
                for _, _, label in sorted(supported, key=lambda row: (-row[0], row[1]))[
                    :max_sources
                ]
            )

        return _select_relation_supporting_source_pair(
            answer=answer,
            source_registry=source_registry,
            question=question,
            max_sources=max_sources,
        )


def _validate_answer_against_evidence(
    *,
    answer: str,
    evidence: str,
    question: str | None = None,
    require_subject_attribute_alignment: bool = False,
) -> ClaimEvidenceStatus:
    folded_answer = _normalize_broken_number_groups(fold_text(answer))
    folded_evidence = _normalize_broken_number_groups(fold_text(evidence))

    analysis = analyze_question(question) if question is not None else None
    is_yes_no = analysis is not None and analysis.is_yes_no

    if (
        not is_yes_no
        and not require_subject_attribute_alignment
        and (analysis is None or not analysis.asks_for_explicit_value)
        and (analysis is None or not analysis.asks_for_person)
        and _answer_is_verbatim_supported(answer=folded_answer, evidence=folded_evidence)
    ):
        # A complete copied policy clause is direct support. Unrelated policy
        # statements elsewhere in a wide chunk must not reverse its polarity.
        return ClaimEvidenceStatus.SUPPORTED

    if not (
        analysis is not None
        and analysis.asks_for_time_range
        and len(_CLOCK_VALUE_RE.findall(folded_answer)) >= 2
    ) and _numbers_are_contradicted(folded_answer, folded_evidence):
        return ClaimEvidenceStatus.CONTRADICTED

    if _answer_claims_unspecified_but_source_has_value(
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return ClaimEvidenceStatus.CONTRADICTED

    if _passive_action_polarity_is_contradicted(
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return ClaimEvidenceStatus.CONTRADICTED

    if question is not None and _security_control_requirement_is_missing(
        question=question,
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return ClaimEvidenceStatus.INSUFFICIENT

    if question is not None and _ordered_first_action_requirement_is_missing(
        question=question,
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return ClaimEvidenceStatus.INSUFFICIENT

    if (
        analysis is not None
        and analysis.asks_for_time_range
        and len(_CLOCK_VALUE_RE.findall(folded_answer)) < 2
    ):
        return ClaimEvidenceStatus.INSUFFICIENT

    if (
        question is not None
        and analysis is not None
        and analysis.asks_for_explicit_value
        and not _explicit_value_answer_is_subject_aligned(
            question=question,
            answer=folded_answer,
            evidence=folded_evidence,
        )
    ):
        return ClaimEvidenceStatus.INSUFFICIENT

    if is_yes_no and question is not None:
        if is_non_answer_context(evidence):
            return ClaimEvidenceStatus.INSUFFICIENT

        answer_polarity = infer_yes_no_polarity(answer)
        if answer_polarity is not None:
            relation_status = _replacement_relation_semantic_status(
                question=question,
                answer_polarity=answer_polarity,
                evidence_segments=(evidence,),
            )
            if relation_status is not None:
                return relation_status

        if _yes_no_answer_restates_question(
            question=question,
            answer=answer,
        ):
            return ClaimEvidenceStatus.INSUFFICIENT

        if _multi_value_yes_no_answer_is_supported(
            question=question,
            answer=answer,
            evidence=evidence,
        ):
            return ClaimEvidenceStatus.SUPPORTED

        focused_segments = _question_focused_evidence_segments(
            question=question,
            evidence=evidence,
        )

        # A sample question or question-list entry alone
        # is not evidence for a yes/no answer.
        if not focused_segments:
            return ClaimEvidenceStatus.INSUFFICIENT

        focused_segments = tuple(
            segment
            for segment in focused_segments
            if not _segment_mismatches_question_object(
                question=question,
                segment=segment,
            )
        )

        if not focused_segments:
            return ClaimEvidenceStatus.INSUFFICIENT

        if not _yes_no_evidence_has_required_anchor(
            question=question,
            evidence=evidence,
        ):
            return ClaimEvidenceStatus.INSUFFICIENT

        focused_evidence = "\n".join(focused_segments)
        folded_focused_evidence = fold_text(focused_evidence)

        role_person_status = _yes_no_role_person_correction_status(
            question=question,
            answer=answer,
            evidence_segments=focused_segments,
        )
        if role_person_status is not None:
            return role_person_status

        semantic_status = _yes_no_semantic_status_from_segments(
            question=question,
            answer=answer,
            evidence_segments=focused_segments,
        )

        if semantic_status is not None:
            return semantic_status

        if _polarity_is_contradicted(
            folded_answer,
            folded_focused_evidence,
        ):
            return ClaimEvidenceStatus.CONTRADICTED

        if _answer_has_grounded_signal(
            answer=folded_answer,
            evidence=folded_focused_evidence,
        ):
            return ClaimEvidenceStatus.SUPPORTED

        return ClaimEvidenceStatus.INSUFFICIENT

    if (
        analysis is not None
        and analysis.asks_for_person
        and _person_lookup_answer_name_missing(
            question=fold_text(question or ""),
            answer=folded_answer,
            evidence=folded_evidence,
        )
    ):
        return ClaimEvidenceStatus.INSUFFICIENT

    if _answer_is_verbatim_supported(answer=folded_answer, evidence=folded_evidence):
        return ClaimEvidenceStatus.SUPPORTED

    if _polarity_is_contradicted(
        folded_answer,
        folded_evidence,
    ):
        return ClaimEvidenceStatus.CONTRADICTED

    if (
        question is not None
        and analysis is not None
        and require_subject_attribute_alignment
        and not analysis.asks_for_explicit_value
        and not analysis.asks_for_person
        and not _non_value_answer_is_subject_attribute_aligned(
            question=question,
            answer=folded_answer,
            evidence=folded_evidence,
        )
    ):
        return ClaimEvidenceStatus.INSUFFICIENT

    if _answer_has_grounded_signal(
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return ClaimEvidenceStatus.SUPPORTED

    if _answer_is_low_substance(folded_answer) and (
        (
            analysis is not None
            and not analysis.asks_for_explicit_value
            and (
                not analysis.asks_for_person
                or not _person_lookup_answer_name_missing(
                    question=fold_text(question or ""),
                    answer=folded_answer,
                    evidence=folded_evidence,
                )
            )
        )
        or _low_substance_answer_is_verbatim_supported(
            answer=folded_answer,
            evidence=folded_evidence,
        )
    ):
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
    return "\n\n".join(parts)


def _question_focused_evidence_segments(
    *,
    question: str,
    evidence: str,
) -> tuple[str, ...]:
    folded_question = fold_text(question)

    question_tokens = tuple(re.findall(r"\w+", folded_question))

    focus_terms = {
        token
        for token in question_tokens
        if len(token) >= 3 and token not in _YES_NO_FOCUS_STOP_TERMS
    }

    bigrams = {
        " ".join(question_tokens[index : index + 2]) for index in range(len(question_tokens) - 1)
    }

    trigrams = {
        " ".join(question_tokens[index : index + 3]) for index in range(len(question_tokens) - 2)
    }

    # Preserve blank-line/source boundaries but join PDF line wraps
    # that occur inside the same sentence or bullet.
    paragraphs = tuple(
        re.sub(
            r"[ \t]*\r?\n[ \t]*",
            " ",
            paragraph,
        ).strip()
        for paragraph in re.split(
            r"\r?\n\s*\r?\n",
            evidence,
        )
        if paragraph.strip()
    )

    normalized_evidence = "\n\n".join(paragraphs)

    raw_segments = re.split(
        r"(?:\n{2,}|[•]+|(?<=[.!?;])\s+)",
        normalized_evidence,
    )

    role_anchor_terms = _yes_no_role_anchor_terms(question)

    scored: list[tuple[int, float, str]] = []

    for index, raw_segment in enumerate(raw_segments):
        segment = raw_segment.strip(" \t\r\n-•")

        if not segment:
            continue

        # A question/example entry is not evidence for its answer.
        if segment.rstrip().endswith("?") or is_non_answer_context(segment):
            continue

        folded_segment = fold_text(segment)

        if _segment_mismatches_question_object(
            question=question,
            segment=segment,
        ):
            continue

        matched_terms = {term for term in focus_terms if term in folded_segment}

        matched_bigrams = {phrase for phrase in bigrams if phrase in folded_segment}

        matched_trigrams = {phrase for phrase in trigrams if phrase in folded_segment}

        score = len(matched_terms) * 2.0 + len(matched_bigrams) * 5.0 + len(matched_trigrams) * 8.0

        if _is_replacement_relation_question(folded_question):
            score += _replacement_relation_segment_score(
                folded_segment=folded_segment,
                entity_terms=_replacement_relation_entity_terms(folded_question),
            )

        matched_role_anchors = {
            term for term in role_anchor_terms if _contains_folded_term(folded_segment, term)
        }
        if matched_role_anchors:
            score += len(matched_role_anchors) * 3.0

        if score > 0:
            scored.append((index, score, segment))

    if not scored:
        return ()

    best_score = max(score for _, score, _ in scored)

    minimum_score = max(
        3.0,
        best_score * 0.55,
    )

    selected = [row for row in scored if row[1] >= minimum_score]

    # IMPORTANT:
    # keep relevance order. Do not sort back to document order,
    # because semantic validation consumes the strongest evidence first.
    selected.sort(
        key=lambda row: (
            -row[1],
            row[0],
        )
    )

    return tuple(segment for _, _, segment in selected[:3])


def _yes_no_semantic_status(
    *,
    answer: str,
    evidence: str,
) -> ClaimEvidenceStatus | None:
    answer_polarity = infer_yes_no_polarity(answer)
    evidence_polarity = infer_yes_no_polarity(evidence)

    if answer_polarity is None or evidence_polarity is None:
        return None

    if answer_polarity != evidence_polarity:
        return ClaimEvidenceStatus.CONTRADICTED

    return ClaimEvidenceStatus.SUPPORTED


def _yes_no_required_anchor_terms(
    question: str,
) -> frozenset[str]:
    anchors: list[str] = []
    for raw_token in re.findall(r"\b\w+\b", question, re.UNICODE):
        token = raw_token.strip("_")
        if not token:
            continue
        folded = fold_text(token)
        if len(folded) < 2 or folded in _YES_NO_REQUIRED_ANCHOR_STOP_TERMS:
            continue
        if token.isupper() and len(folded) >= 2:
            anchors.append(folded)
            continue
        if len(folded) >= 4 and any(character.isupper() for character in token[1:]):
            anchors.append(folded)

    return frozenset(dict.fromkeys(anchors))


def _yes_no_evidence_has_required_anchor(
    *,
    question: str,
    evidence: str,
) -> bool:
    anchors = _yes_no_required_anchor_terms(question)
    if not anchors:
        return True

    folded_question = fold_text(question)
    required_count = len(anchors) if _is_replacement_relation_question(folded_question) else 1
    folded_evidence = fold_text(evidence)
    matched_count = sum(1 for anchor in anchors if _contains_folded_term(folded_evidence, anchor))
    return matched_count >= required_count


def _yes_no_question_focus_terms(
    question: str,
) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(
            r"\w+",
            fold_text(question),
        )
        if len(token) >= 3 and token not in _YES_NO_FOCUS_STOP_TERMS
    )


def _yes_no_focus_match_count(
    *,
    text: str,
    focus_terms: frozenset[str],
) -> int:
    if not focus_terms:
        return 0

    text_terms = frozenset(
        re.findall(
            r"\w+",
            fold_text(text),
        )
    )

    return len(text_terms.intersection(focus_terms))


def _yes_no_role_person_correction_status(
    *,
    question: str,
    answer: str,
    evidence_segments: tuple[str, ...],
) -> ClaimEvidenceStatus | None:
    if infer_yes_no_polarity(answer) != "NO":
        return None
    role_anchor_terms = _yes_no_role_anchor_terms(question)
    if not role_anchor_terms:
        return None
    question_terms = frozenset(re.findall(r"\w+", fold_text(question)))
    correction_terms = tuple(
        dict.fromkeys(
            term
            for term in re.findall(r"\w+", fold_text(answer))
            if len(term) >= 3
            and term not in question_terms
            and term not in _YES_NO_FOCUS_STOP_TERMS
            and term not in _YES_NO_REQUIRED_ANCHOR_STOP_TERMS
            and not term.isdecimal()
        )
    )
    if len(correction_terms) < 2:
        return None
    required_correction_matches = min(2, len(correction_terms))
    for segment in evidence_segments:
        folded_segment = fold_text(segment)
        if not any(_contains_folded_term(folded_segment, role) for role in role_anchor_terms):
            continue
        matched_corrections = sum(
            1 for term in correction_terms if _contains_folded_term(folded_segment, term)
        )
        if matched_corrections >= required_correction_matches:
            return ClaimEvidenceStatus.SUPPORTED
    return None


def _yes_no_role_anchor_terms(question: str) -> frozenset[str]:
    return frozenset(
        fold_text(token)
        for token in re.findall(r"\b\w+\b", question, re.UNICODE)
        if token.isupper()
        and len(fold_text(token)) >= 2
        and fold_text(token) not in _YES_NO_REQUIRED_ANCHOR_STOP_TERMS
    )


def _yes_no_semantic_status_from_segments(
    *,
    question: str,
    answer: str,
    evidence_segments: tuple[str, ...],
) -> ClaimEvidenceStatus | None:
    answer_polarity = infer_yes_no_polarity(answer)

    if answer_polarity is None:
        return None

    relation_status = _replacement_relation_semantic_status(
        question=question,
        answer_polarity=answer_polarity,
        evidence_segments=evidence_segments,
    )

    if relation_status is not None:
        return relation_status

    focus_terms = _yes_no_question_focus_terms(question)

    answer_focus_matches = _yes_no_focus_match_count(
        text=answer,
        focus_terms=focus_terms,
    )

    required_focus_matches = min(
        2,
        len(focus_terms),
    )

    saw_same_polarity = False
    saw_opposite_polarity = False

    for segment in evidence_segments:
        evidence_polarity = infer_yes_no_polarity(segment)

        if evidence_polarity is None:
            continue

        if evidence_polarity != answer_polarity:
            saw_opposite_polarity = True
            continue

        saw_same_polarity = True

        if _answer_has_grounded_signal(
            answer=fold_text(answer),
            evidence=fold_text(segment),
        ):
            return ClaimEvidenceStatus.SUPPORTED

        if (
            required_focus_matches > 0
            and answer_focus_matches >= required_focus_matches
            and _yes_no_focus_match_count(
                text=segment,
                focus_terms=focus_terms,
            )
            >= required_focus_matches
        ):
            return ClaimEvidenceStatus.SUPPORTED

    if saw_opposite_polarity and not saw_same_polarity:
        return ClaimEvidenceStatus.CONTRADICTED

    return None


def _supporting_source_score(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> float:
    focused_segments = _question_focused_evidence_segments(
        question=question,
        evidence=evidence,
    )
    focused_evidence = "\n".join(focused_segments)
    focus_terms = _yes_no_question_focus_terms(question)
    score = float(
        _yes_no_focus_match_count(
            text=answer,
            focus_terms=focus_terms,
        )
        + _yes_no_focus_match_count(
            text=focused_evidence,
            focus_terms=focus_terms,
        )
    )
    if _answer_is_verbatim_supported(
        answer=fold_text(answer),
        evidence=fold_text(evidence),
    ):
        # A source containing the complete answer clause is stronger provenance
        # than a nearby passage that only overlaps the question topic.
        score += 100.0
    if (
        _replacement_relation_semantic_status(
            question=question,
            answer_polarity=infer_yes_no_polarity(answer) or "",
            evidence_segments=focused_segments,
        )
        == ClaimEvidenceStatus.SUPPORTED
    ):
        score += 20.0
    anchors = _yes_no_required_anchor_terms(question)
    if anchors:
        folded_evidence = fold_text(evidence)
        matched_anchors = sum(
            1 for anchor in anchors if _contains_folded_term(folded_evidence, anchor)
        )
        score += matched_anchors * 18.0
        if matched_anchors == 0:
            score -= 30.0
    if _has_self_reference(folded_text=fold_text(question)) and _has_self_reference(
        folded_text=fold_text(focused_evidence)
    ):
        score += 12.0
    return score


def _select_relation_supporting_source_pair(
    *,
    answer: str,
    source_registry: PromptSourceRegistry,
    question: str,
    max_sources: int,
) -> tuple[str, ...]:
    if max_sources < 2:
        return ()

    folded_question = fold_text(question)
    if not _is_replacement_relation_question(folded_question):
        return ()

    answer_polarity = infer_yes_no_polarity(answer)
    if answer_polarity is None:
        return ()

    answer_sources = [
        (index, source)
        for index, source in enumerate(source_registry.sources)
        if not is_non_answer_context(source.text)
    ]

    for left_index, left_source in answer_sources:
        for right_index, right_source in answer_sources:
            if right_index <= left_index:
                continue
            combined = f"{left_source.text}\n\n{right_source.text}"
            focused = _question_focused_evidence_segments(
                question=question,
                evidence=combined,
            )
            if (
                _replacement_relation_semantic_status(
                    question=question,
                    answer_polarity=answer_polarity,
                    evidence_segments=focused,
                )
                == ClaimEvidenceStatus.SUPPORTED
            ):
                return (
                    left_source.label,
                    right_source.label,
                )

    return ()


def _segment_mismatches_question_object(
    *,
    question: str,
    segment: str,
) -> bool:
    folded_question = fold_text(question)
    if not _has_self_reference(folded_question):
        return False
    folded_segment = fold_text(segment)
    return _has_other_reference(folded_segment) and not _has_self_reference(folded_segment)


def _has_self_reference(folded_text: str) -> bool:
    return _has_any_phrase(folded_text, _YES_NO_SELF_REFERENCE_CUES)


def _has_other_reference(folded_text: str) -> bool:
    return _has_any_phrase(folded_text, _YES_NO_OTHER_REFERENCE_CUES)


def _is_replacement_relation_question(folded_question: str) -> bool:
    return _has_any_phrase(folded_question, _REPLACEMENT_RELATION_CUES)


def _replacement_relation_entity_terms(folded_question: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            term.strip("_")
            for term in re.findall(r"\w+", folded_question)
            if len(term.strip("_")) >= 3 and term.strip("_") not in _RELATION_ENTITY_STOP_TERMS
        )
    )


def _replacement_relation_segment_score(
    *,
    folded_segment: str,
    entity_terms: tuple[str, ...],
) -> float:
    if not entity_terms:
        return 0.0
    matched_entities = tuple(
        term for term in entity_terms if _contains_folded_term(folded_segment, term)
    )
    if not matched_entities:
        return 0.0

    has_primary = _has_any_phrase(folded_segment, _PRIMARY_RELATION_CUES)
    has_supplemental = _has_any_phrase(folded_segment, _SUPPLEMENTAL_RELATION_CUES)
    if not has_primary and not has_supplemental:
        return 0.0

    score = 6.0 + len(matched_entities) * 3.0
    if has_primary:
        score += 8.0
    if has_supplemental:
        score += 8.0
    return score


def _replacement_relation_semantic_status(
    *,
    question: str,
    answer_polarity: str,
    evidence_segments: tuple[str, ...],
) -> ClaimEvidenceStatus | None:
    folded_question = fold_text(question)
    if not _is_replacement_relation_question(folded_question):
        return None

    if answer_polarity not in {"YES", "NO"}:
        return None

    folded_evidence = fold_text(" ".join(evidence_segments))
    if not folded_evidence:
        return None

    entity_terms = _replacement_relation_entity_terms(folded_question)
    if len(entity_terms) < 2:
        return None

    primary_entities = _category_entities_near_cues(
        folded_evidence=folded_evidence,
        entity_terms=entity_terms,
        cues=_PRIMARY_RELATION_CUES,
    )
    supplemental_entities = _category_entities_near_cues(
        folded_evidence=folded_evidence,
        entity_terms=entity_terms,
        cues=_SUPPLEMENTAL_RELATION_CUES,
    )

    if not primary_entities or not supplemental_entities:
        return None

    if len(primary_entities.union(supplemental_entities)) < 2:
        return None

    if answer_polarity == "NO":
        return ClaimEvidenceStatus.SUPPORTED

    return ClaimEvidenceStatus.CONTRADICTED


def _category_entities_near_cues(
    *,
    folded_evidence: str,
    entity_terms: tuple[str, ...],
    cues: tuple[str, ...],
) -> set[str]:
    matches: set[str] = set()
    for term in entity_terms:
        for match in re.finditer(
            rf"(?<!\w){re.escape(term)}(?!\w)",
            folded_evidence,
        ):
            window = folded_evidence[
                max(0, match.start() - 180) : min(len(folded_evidence), match.end() + 180)
            ]
            if _has_any_phrase(window, cues):
                matches.add(term)
                break
    return matches


def _contains_folded_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _polarity_is_contradicted(answer: str, evidence: str) -> bool:
    if _passive_action_polarity_is_contradicted(answer=answer, evidence=evidence):
        return True

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


def _passive_action_polarity_is_contradicted(*, answer: str, evidence: str) -> bool:
    """Reject reversing a source's `duoc <action>` passive policy statement."""

    def negated_actions(value: str) -> tuple[str, ...]:
        actions: list[str] = []
        for match in re.finditer(r"\bkhong\s+duoc\s+((?:\w+\s+){0,2}\w+)", value):
            tokens = match.group(1).split()
            if tokens:
                actions.append(" ".join(tokens[:2]))
        return tuple(actions)

    def has_positive_action(value: str, action: str) -> bool:
        return (
            re.search(
                rf"(?<!khong\s)\bduoc\s+{re.escape(action)}\b",
                value,
            )
            is not None
        )

    return any(has_positive_action(evidence, action) for action in negated_actions(answer)) or any(
        has_positive_action(answer, action) for action in negated_actions(evidence)
    )


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


def _normalize_broken_number_groups(text: str) -> str:
    return re.sub(r"(?<=\d)([.,])\s*-\s*(?=\d{3}\b)", r"\1", text)


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


def _security_control_requirement_is_missing(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    asks_for_controls = _asks_for_security_controls(question)
    if not asks_for_controls:
        return False
    available_controls = tuple(cue for cue in _SECURITY_CONTROL_CUES if cue in evidence)
    return bool(available_controls) and not any(cue in answer for cue in available_controls)


def _ordered_first_action_requirement_is_missing(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    """Require the answer to preserve the action explicitly ordered first in evidence."""
    folded_question = fold_text(question)
    if not any(cue in folded_question for cue in ("lam gi truoc", "what first", "do first")):
        return False

    stop_terms = {
        "answer",
        "claim",
        "evidence",
        "first",
        "gi",
        "lam",
        "ly",
        "manager",
        "must",
        "nguoi",
        "phai",
        "quan",
        "the",
        "truoc",
    }
    ordered_clauses = tuple(
        clause.strip()
        for clause in re.split(r"[.;\n]", evidence)
        if "truoc" in clause or " first" in clause
    )
    for clause in ordered_clauses:
        action_terms = {
            term for term in re.findall(r"\w+", clause) if len(term) >= 3 and term not in stop_terms
        }
        if len(action_terms.intersection(set(re.findall(r"\w+", answer)))) >= 2:
            return False
    return bool(ordered_clauses)


def _asks_for_security_controls(question: str) -> bool:
    folded_question = fold_text(question)
    return (
        "bao mat" in folded_question
        and any(
            cue in folded_question
            for cue in (
                "yeu cau",
                "bao dam",
                "can tuan thu",
                "tuan thu",
                "requirements",
                "controls",
            )
        )
    ) or (
        "an toan" in folded_question
        and any(cue in folded_question for cue in ("bao dam", "dam bao", "gi", "controls"))
    )


def _person_lookup_answer_name_missing(*, question: str, answer: str, evidence: str) -> bool:
    candidates = _person_name_claim_candidates(question=question, answer=answer)
    return not candidates or not any(
        re.search(rf"(?<!\w){re.escape(candidate)}(?!\w)", evidence) is not None
        for candidate in candidates
    )


def _person_name_claim_candidates(*, question: str, answer: str) -> tuple[str, ...]:
    question_terms = set(re.findall(r"\w+", question))
    answer_terms = tuple(re.findall(r"\w+", answer))
    candidates: list[str] = []
    for length in range(4, 1, -1):
        for index in range(0, len(answer_terms) - length + 1):
            terms = answer_terms[index : index + length]
            if any(term in _PERSON_LOOKUP_STOP_TERMS for term in terms):
                continue
            if sum(1 for term in terms if term not in question_terms) < 2:
                continue
            if not all(len(term) >= 2 for term in terms):
                continue
            candidate = " ".join(terms)
            if candidate not in candidates:
                candidates.append(candidate)
    return tuple(candidates)


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


def _low_substance_answer_is_verbatim_supported(*, answer: str, evidence: str) -> bool:
    normalized = " ".join(answer.split()).strip(" .,:;!?-\t\r\n")
    normalized_evidence = " ".join(evidence.split())
    if not normalized or normalized in {"co", "khong", "yes", "no"}:
        return False
    if not _answer_is_low_substance(normalized):
        return False
    return normalized in normalized_evidence


def _answer_is_verbatim_supported(*, answer: str, evidence: str) -> bool:
    normalized = " ".join(answer.split()).strip(" .,:;!?-\t\r\n")
    normalized_evidence = " ".join(evidence.split())
    if len(normalized) < 24 or normalized in {"co", "khong", "yes", "no"}:
        return False
    return normalized in normalized_evidence


def _explicit_value_answer_is_subject_aligned(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    analysis = analyze_question(question)
    answer_numbers = set(_numbers(answer))
    if not answer_numbers:
        return has_explicit_not_specified(evidence) and _answer_mentions_unspecified(answer)

    if _is_pay_date_question(question) and not _pay_date_numbers_are_locally_bound(
        answer_numbers=answer_numbers,
        evidence=evidence,
    ):
        return False

    folded_question = fold_text(retrieval_query_variants(question).normalized)
    remote_cues = ("remote", "hybrid", "lam o nha", "lam viec tu xa", "work from home")
    asks_for_remote_value = any(cue in folded_question for cue in remote_cues)
    question_focus = {
        term
        for term in re.findall(r"\w+", folded_question)
        if len(term) >= 3 and term not in _VALUE_ALIGNMENT_STOP_TERMS
    }
    if asks_for_remote_value:
        question_focus.difference_update({"hybrid", "remote", "nha"})
    if not question_focus and not asks_for_remote_value:
        return True
    requested_condition = _value_condition_family(folded_question)
    if asks_for_remote_value:
        if analysis.asks_for_duration:
            if not _explicit_remote_duration_is_aligned(
                answer_numbers=answer_numbers,
                evidence=evidence,
                remote_cues=remote_cues,
            ):
                return False
        elif not _explicit_remote_value_is_aligned(
            answer_numbers=answer_numbers,
            evidence=evidence,
            remote_cues=remote_cues,
        ):
            return False
    if (
        not asks_for_remote_value
        and requested_condition is None
        and any(cue in folded_question for cue in _SPECIFIC_VALUE_FIELD_CUES)
        and not _explicit_value_is_nearest_to_requested_subject(
            question=folded_question,
            answer_numbers=answer_numbers,
            evidence=evidence,
            question_focus=question_focus,
        )
    ):
        return False

    segments = tuple(
        segment.strip()
        for segment in re.split(r"(?:\r?\n|(?<=[.!?;])\s+)", evidence)
        if segment.strip()
    )
    for index, segment in enumerate(segments):
        if answer_numbers.isdisjoint(_numbers(segment)):
            continue
        start = max(0, index - 1)
        # OCR/table extraction may wrap the field label after a value and a
        # semicolon-created segment. Keep two following segments for binding.
        end = min(len(segments), index + 3)
        local_evidence = " ".join(segments[start:end])
        condition_evidence = " ".join(segments[index : min(len(segments), index + 2)])
        if asks_for_remote_value and not any(cue in local_evidence for cue in remote_cues):
            continue
        if requested_condition is not None and not _has_value_condition(
            condition_evidence,
            requested_condition,
        ):
            continue
        matched = {term for term in question_focus if _contains_folded_term(local_evidence, term)}
        if matched or asks_for_remote_value:
            return True
    return False


def _explicit_remote_value_is_aligned(
    *,
    answer_numbers: set[str],
    evidence: str,
    remote_cues: tuple[str, ...],
) -> bool:
    numeric_matches = tuple(_NUMBER_RE.finditer(evidence))
    cue_spans = tuple(
        cue_match.span()
        for cue in remote_cues
        for cue_match in re.finditer(rf"(?<!\w){re.escape(cue)}(?!\w)", evidence)
    )
    if not cue_spans:
        return False

    def preceding_distance(value_match: re.Match[str]) -> int | None:
        distances = tuple(
            value_match.start() - cue_end
            for _, cue_end in cue_spans
            if cue_end <= value_match.start()
        )
        return min(distances) if distances else None

    available = tuple(
        distance for match in numeric_matches if (distance := preceding_distance(match)) is not None
    )
    if not available:
        return False
    best_distance = min(available)
    return any(
        _normalized_number(match.group(0)) in answer_numbers
        and preceding_distance(match) == best_distance
        for match in numeric_matches
    )


def _explicit_remote_duration_is_aligned(
    *,
    answer_numbers: set[str],
    evidence: str,
    remote_cues: tuple[str, ...],
) -> bool:
    if not any(cue in evidence for cue in remote_cues):
        return False
    for match in _NUMBER_RE.finditer(evidence):
        if _normalized_number(match.group(0)) not in answer_numbers:
            continue
        local = evidence[max(0, match.start() - 80) : min(len(evidence), match.end() + 80)]
        if any(unit in local for unit in ("ngay", "tuan", "day", "week")):
            return True
    return False


def _explicit_value_is_nearest_to_requested_subject(
    *,
    question: str,
    answer_numbers: set[str],
    evidence: str,
    question_focus: set[str],
) -> bool:
    """Keep a value bound to its requested row/field in multi-value evidence."""

    if len(answer_numbers) != 1:
        return True
    numeric_matches = tuple(_NUMBER_RE.finditer(evidence))
    if len({_normalized_number(match.group(0)) for match in numeric_matches}) < 2:
        return True

    subject_phrases = _requested_value_subject_phrases(
        question=question,
        question_focus=question_focus,
    )
    phrase_spans = tuple(
        match.span()
        for phrase in subject_phrases
        for match in re.finditer(rf"(?<!\w){re.escape(phrase)}(?!\w)", evidence)
    )
    if not phrase_spans:
        return False

    def distance_to_subject(match: re.Match[str]) -> int:
        return min(
            max(phrase_start - match.end(), match.start() - phrase_end, 0)
            for phrase_start, phrase_end in phrase_spans
        )

    best_distance = min(distance_to_subject(match) for match in numeric_matches)
    answer_distance = min(
        (
            distance_to_subject(match)
            for match in numeric_matches
            if _normalized_number(match.group(0)) in answer_numbers
        ),
        default=None,
    )
    return answer_distance is not None and answer_distance <= best_distance + 24


def _requested_value_subject_phrases(
    *,
    question: str,
    question_focus: set[str],
) -> tuple[str, ...]:
    specific_phrases = tuple(
        cue for cue in _SPECIFIC_VALUE_FIELD_CUES if _contains_folded_term(question, cue)
    )
    if specific_phrases:
        return specific_phrases

    tokens = re.findall(r"\w+", question)
    runs: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in question_focus:
            current.append(token)
            continue
        if current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)

    phrases: list[str] = []
    for run in runs:
        for size in (3, 2):
            for index in range(len(run) - size + 1):
                phrases.append(" ".join(run[index : index + size]))
    if phrases:
        return tuple(dict.fromkeys(phrases))
    return tuple(term for term in question_focus if len(term) >= 4)


def _normalized_number(value: str) -> str:
    return value.replace(",", ".")


def _is_pay_date_question(question: str) -> bool:
    folded = fold_text(question)
    return any(term in folded for term in ("luong", "payroll", "salary")) and any(
        cue in folded for cue in ("ngay nao", "when", "pay date", "ngay tra")
    )


def _pay_date_numbers_are_locally_bound(
    *,
    answer_numbers: set[str],
    evidence: str,
) -> bool:
    """Reject dates borrowed from unrelated payroll fields in the same chunk."""

    segments = tuple(
        segment.strip()
        for segment in re.split(r"(?:\r?\n|(?<=[.!?;])\s+)", evidence)
        if segment.strip()
    )
    pay_date_numbers: set[str] = set()
    for index, segment in enumerate(segments):
        if not any(cue in segment for cue in ("ngay tra luong", "pay date")):
            continue
        # A semicolon-wrapped condition can sit between the value and its
        # field label in extracted tables, so retain two preceding segments.
        start = max(0, index - 2)
        end = min(len(segments), index + 2)
        pay_date_numbers.update(_numbers(" ".join(segments[start:end])))
    return bool(pay_date_numbers) and answer_numbers.issubset(pay_date_numbers)


def _value_condition_family(value: str) -> str | None:
    for family, cues in _VALUE_CONDITION_CUES.items():
        if any(cue in value for cue in cues):
            return family
    return None


def _has_value_condition(value: str, expected_family: str) -> bool:
    return any(cue in value for cue in _VALUE_CONDITION_CUES[expected_family])


def _non_value_answer_is_subject_attribute_aligned(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    if _numbers(answer):
        return _explicit_value_answer_is_subject_aligned(
            question=question,
            answer=answer,
            evidence=evidence,
        )
    folded_question = fold_text(question)
    asks_for_eligibility = any(
        cue in folded_question for cue in ("khi nao", "when", "eligib")
    ) and any(cue in folded_question for cue in ("tham gia", "duoc huong", "eligib"))
    if asks_for_eligibility:
        return _eligibility_condition_answer_is_aligned(
            question=question,
            answer=answer,
            evidence=evidence,
        )
    if _asks_for_security_controls(question):
        return any(cue in answer and cue in evidence for cue in _SECURITY_CONTROL_CUES)
    ordered_question_focus = tuple(
        dict.fromkeys(
            term
            for term in re.findall(r"\w+", fold_text(question))
            if len(term) >= 3 and term not in _CLAIM_ALIGNMENT_STOP_TERMS
        )
    )
    question_focus = set(ordered_question_focus)
    if len(question_focus) < 2:
        return True
    if (
        "call" in question_focus
        and "call" in answer
        and "call" in evidence
        and any(cue in fold_text(question) for cue in ("phu cap", "allowance", "stipend"))
        and any(cue in answer for cue in ("phu cap", "allowance", "stipend"))
        and any(cue in evidence for cue in ("phu cap", "allowance", "stipend"))
    ):
        return True
    requested_attribute = ordered_question_focus[-1]
    requested_attribute_is_explicit = _contains_folded_term(evidence, requested_attribute)

    raw_answer_terms = tuple(re.findall(r"\w+", answer))
    answer_terms = {
        term
        for term in raw_answer_terms
        if len(term) >= 3 and term not in _CLAIM_ALIGNMENT_STOP_TERMS and term not in question_focus
    }
    if not answer_terms:
        return False
    answer_phrases = {
        f"{left} {right}"
        for left, right in zip(raw_answer_terms, raw_answer_terms[1:], strict=False)
        if left in answer_terms and right in answer_terms
    }

    segments = tuple(
        segment.strip()
        for segment in re.split(r"(?:\r?\n|(?<=[.!?;])\s+)", evidence)
        if segment.strip()
    )
    for index, local_evidence in enumerate(segments):
        matched_question = {
            term for term in question_focus if _contains_folded_term(local_evidence, term)
        }
        matched_answer = {
            term for term in answer_terms if _contains_folded_term(local_evidence, term)
        }
        matched_phrase = any(phrase in local_evidence for phrase in answer_phrases)
        previous_is_attribute_header = (
            index > 0
            and len(segments[index - 1]) <= 120
            and _contains_folded_term(segments[index - 1], requested_attribute)
        )
        if (requested_attribute in matched_question or previous_is_attribute_header) and (
            matched_phrase or (not answer_phrases and len(matched_answer) >= 2)
        ):
            return True
        if not requested_attribute_is_explicit:
            evidence_window = " ".join(segments[max(0, index - 1) : min(len(segments), index + 2)])
            window_question_matches = {
                term for term in question_focus if _contains_folded_term(evidence_window, term)
            }
            window_answer_matches = {
                term for term in answer_terms if _contains_folded_term(evidence_window, term)
            }
            window_phrase_match = any(phrase in evidence_window for phrase in answer_phrases)
            if len(window_question_matches) >= 2 and (
                window_phrase_match or (not answer_phrases and len(window_answer_matches) >= 2)
            ):
                return True
    return False


def _eligibility_condition_answer_is_aligned(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    folded_question = fold_text(question)
    if not (
        any(cue in folded_question for cue in ("khi nao", "when", "eligib"))
        and any(cue in folded_question for cue in ("tham gia", "duoc huong", "eligib"))
    ):
        return False

    entity_terms = {
        term
        for term in re.findall(r"\w+", folded_question)
        if len(term) >= 4
        and term
        not in {
            "duoc",
            "eligible",
            "eligibility",
            "tham",
            "when",
        }
    }
    if entity_terms and not any(term in answer and term in evidence for term in entity_terms):
        return False

    answer_has_primary_condition = (
        "sau thu viec" in answer
        or "hoan thanh thu viec" in answer
        or "nhan vien chinh thuc" in answer
    )
    evidence_has_primary_condition = (
        "sau thu viec" in evidence
        or ("sau khi hoan thanh" in evidence and "thu viec" in evidence)
        or "nhan vien chinh thuc" in evidence
    )
    if evidence_has_primary_condition and not answer_has_primary_condition:
        return False

    condition_families = (
        (answer_has_primary_condition, evidence_has_primary_condition),
        (
            "danh sach bao hiem" in answer,
            "danh sach bao hiem" in evidence,
        ),
        (
            "dieu khoan loai tru" in answer,
            "dieu khoan loai tru" in evidence,
        ),
    )
    return any(
        answer_has_condition and evidence_has_condition
        for answer_has_condition, evidence_has_condition in condition_families
    )


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


def _yes_no_answer_restates_question(
    *,
    question: str,
    answer: str,
) -> bool:
    folded_question = fold_text(question).strip(" \t\r\n?!.,;:")
    folded_answer = fold_text(answer).strip(" \t\r\n?!.,;:")

    if not folded_question or not folded_answer:
        return False

    folded_answer = re.sub(
        r"^(?:co|khong|yes|no)\b[\s,.:;-]*",
        "",
        folded_answer,
    ).strip()

    folded_question = re.sub(
        r"(?:\s+(?:dung|phai)\s+khong|\s+khong)$",
        "",
        folded_question,
    ).strip()

    return bool(folded_question) and folded_answer == folded_question


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


def _has_any_phrase(
    text: str,
    cues: tuple[str, ...],
) -> bool:
    for cue in cues:
        normalized_cue = cue.strip()

        if not normalized_cue:
            continue

        if re.search(
            rf"(?<!\w){re.escape(normalized_cue)}(?!\w)",
            text,
        ):
            return True

    return False
