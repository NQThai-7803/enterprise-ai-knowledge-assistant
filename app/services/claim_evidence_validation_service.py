from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.citations.models import PromptSourceRegistry
from app.retrieval.evidence_quality import is_non_answer_context
from app.retrieval.leave_relations import (
    annual_leave_relation_intent,
    annual_leave_seniority_increment,
    ordinary_annual_leave_allocation,
    requested_seniority_years,
)
from app.retrieval.question_analysis import analyze_question, fold_text, retrieval_query_variants
from app.retrieval.structured import (
    has_explicit_not_specified,
    monetary_example_rows,
    monetary_period_bound_numbers,
    monetary_value_numbers,
    monetary_value_period_pairs,
    requested_monetary_period,
)

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
    "prohibits",
    "restricts",
    "restricted",
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
    "does not prohibit",
    "do not prohibit",
    "does not restrict",
    "do not restrict",
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
    "chinh toi",
    "cua chinh toi",
    "chinh ban",
    "cua chinh ban",
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
    "cua nguoi khac",
    "nhan vien khac",
    "cua nhan vien khac",
    "nguoi lao dong khac",
    "cua nguoi lao dong khac",
    "dong nghiep khac",
    "other employee",
    "other employees",
    "another employee",
    "another person",
    "another person s",
    "other person",
    "other person s",
    "other people",
    "others information",
    "others",
)

_SCOPED_POLICY_SUBJECT_CUES: dict[str, tuple[str, ...]] = {
    "EMPLOYEE": ("nhan vien", "nguoi lao dong", "employee", "employees", "worker"),
    "SELF": ("toi", "minh", "i ", " my ", " me "),
}

_SCOPED_POLICY_ACTION_CUES: dict[str, tuple[str, ...]] = {
    # Related disclosure verbs belong to one bounded family.  This supports a
    # policy clause that enumerates discuss/share/provide without treating an
    # arbitrary verb with the same object as equivalent.
    "DISCLOSE": (
        "trao doi",
        "chia se",
        "cung cap",
        "phat tan",
        "discuss",
        "discussing",
        "share",
        "sharing",
        "provide",
        "providing",
        "disclose",
        "disclosing",
        "tell",
    ),
    "USE": ("su dung", " use "),
    "REQUEST": ("yeu cau", "request"),
    "ACCESS": ("truy cap", "access"),
    "COPY": ("sao chep", "copy"),
    "ARCHIVE": ("luu tru", "archive"),
}

_SCOPED_POLICY_OBJECT_STOP_TERMS = _YES_NO_FOCUS_STOP_TERMS.union(
    {
        "toi",
        "minh",
        "chinh",
        "nhan",
        "vien",
        "nguoi",
        "lao",
        "dong",
        "employee",
        "employees",
        "worker",
        "workers",
        "information",
        "thong",
        "tin",
        "data",
        "du",
        "lieu",
        "policy",
        "sach",
        "permit",
        "permits",
        "permitted",
        "allow",
        "allows",
        "allowed",
        "prohibit",
        "prohibits",
        "prohibited",
        "restrict",
        "restricts",
        "restricted",
        "require",
        "requires",
        "required",
        "cam",
        "han",
        "che",
        "yeu",
        "cau",
        "not",
        "does",
        "do",
        "may",
        "can",
        "their",
        "own",
        "other",
        "another",
        "person",
        "people",
        "cua",
        "cho",
        "ve",
        "with",
        "from",
        "about",
        "su",
        "dung",
        "trao",
        "doi",
        "chia",
        "se",
        "cung",
        "cap",
        "phat",
        "tan",
        "truy",
        "sao",
        "chep",
        "luu",
        "discuss",
        "discussing",
        "share",
        "sharing",
        "provide",
        "providing",
        "disclose",
        "disclosing",
        "tell",
        "use",
        "using",
        "access",
        "copy",
        "archive",
        "hoac",
        "khi",
    }
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

# A user can name a concrete public service while the governing policy names
# the service category. Treat only these narrow, well-known category aliases
# as equivalent; the cited clause must still establish the requested action
# and polarity.
_YES_NO_SEMANTIC_ANCHOR_GROUPS = (
    frozenset(("github", "repository", "repo", "kho ma nguon", "kho ca nhan")),
    frozenset(("gmail", "email ca nhan")),
    frozenset(
        (
            "chatgpt",
            "public ai",
            "ai cong cong",
            "dich vu ai cong cong",
            "cong cu ai cong cong",
        )
    ),
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
        "thieu",
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
    repair_feedback: ClaimRepairFeedback | None = None


@dataclass(frozen=True, slots=True)
class ClaimRepairFeedback:
    """Bounded, machine-derived evidence constraint for a regeneration retry.

    This is deliberately a proposition summary rather than an answer.  It can
    tell a generator why a grounded claim failed without selecting an answer
    string or relaxing the post-generation validator.
    """

    failure_dimension: str
    relation: str
    source_label: str | None = None
    evidence_excerpt: str | None = None
    subject: str | None = None
    actions: tuple[str, ...] = ()
    objects: tuple[str, ...] = ()
    scope: str | None = None
    governing_predicate: str | None = None
    negated: bool | None = None
    effective_polarity: str | None = None
    effective_relation: str | None = None


@dataclass(frozen=True, slots=True)
class _ScopedPolicyProposition:
    """The material relation for a scoped yes/no policy claim.

    The representation is deliberately lexical and bounded: it only resolves
    person scope, a small action family, and concrete object terms already
    written in the claim/evidence.  It is a guard against false entailment,
    not a general-purpose policy classifier.
    """

    subject: str | None
    actions: frozenset[str]
    objects: frozenset[str]
    scope: str
    polarity: str | None
    governing_predicate: str | None
    negated: bool | None


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


def _scoped_policy_yes_no_status(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> ClaimEvidenceStatus | None:
    """Require material entailment for a question about own/other data.

    A bare lexical overlap (for example, employee + information) cannot prove
    a policy relationship.  When the question explicitly specifies possessive
    scope, each candidate evidence clause must establish the same scope and a
    compatible action before its compositional polarity may support an answer.
    """

    if not analyze_question(question).is_yes_no:
        return None
    requested = _scoped_policy_proposition(question)
    answer_polarity = infer_yes_no_polarity(answer)
    if requested.scope == "UNSPECIFIED" or not requested.actions or answer_polarity is None:
        return None

    saw_material_opposite = False
    for segment in _policy_evidence_segments(evidence):
        candidate = _scoped_policy_proposition(segment)
        if candidate.scope != requested.scope:
            continue
        if not _scoped_policy_subjects_align(requested.subject, candidate.subject):
            continue
        if not requested.actions.intersection(candidate.actions):
            continue
        if (
            requested.objects
            and candidate.objects
            and not requested.objects.intersection(candidate.objects)
        ):
            continue
        if candidate.polarity is None:
            continue
        if candidate.polarity == answer_polarity:
            return ClaimEvidenceStatus.SUPPORTED
        saw_material_opposite = True

    if saw_material_opposite:
        return ClaimEvidenceStatus.CONTRADICTED
    return ClaimEvidenceStatus.INSUFFICIENT


def _scoped_policy_proposition(text: str) -> _ScopedPolicyProposition:
    folded = f" {fold_text(text)} "
    scope = (
        "OTHER"
        if _has_any_phrase(folded, _YES_NO_OTHER_REFERENCE_CUES)
        else "OWN"
        if _has_any_phrase(folded, _YES_NO_SELF_REFERENCE_CUES)
        else "UNSPECIFIED"
    )
    subject = next(
        (
            name
            for name, cues in _SCOPED_POLICY_SUBJECT_CUES.items()
            if _has_any_phrase(folded, cues)
        ),
        None,
    )
    actions = {
        name for name, cues in _SCOPED_POLICY_ACTION_CUES.items() if _has_any_phrase(folded, cues)
    }
    # Vietnamese ``nói`` is only a disclosure action in a relational phrase;
    # treating the common noun ``nội dung`` as the same action would recreate
    # the generic-token false positive this guard is intended to prevent.
    if re.search(r"\bnoi\s+(?:ve|voi|cho)\b", folded):
        actions.add("DISCLOSE")
    objects = frozenset(
        token
        for token in re.findall(r"\w+", folded)
        if len(token) >= 3 and token not in _SCOPED_POLICY_OBJECT_STOP_TERMS
    )
    governing_predicate, negated = _policy_predicate_and_negation(folded)
    return _ScopedPolicyProposition(
        subject=subject,
        actions=frozenset(actions),
        objects=objects,
        scope=scope,
        polarity=infer_yes_no_polarity(text),
        governing_predicate=governing_predicate,
        negated=negated,
    )


def _effective_policy_relation(proposition: _ScopedPolicyProposition) -> str | None:
    """Normalize an already parsed policy relation for bounded regeneration.

    Predicate and negation remain useful validator diagnostics, but a repair
    model should not have to recompute their composition after validation has
    already established it.
    """

    if proposition.governing_predicate == "PROHIBIT":
        return "NON_PROHIBITORY" if proposition.negated else "PROHIBITORY"
    if proposition.governing_predicate == "PERMIT":
        return "NOT_PERMITTED" if proposition.negated else "PERMITTED"
    if proposition.governing_predicate == "REQUIRE":
        return "NOT_REQUIRED" if proposition.negated else "REQUIRED"
    return None


def _policy_predicate_and_negation(folded: str) -> tuple[str | None, bool | None]:
    """Keep predicate and negation separate for compositional retry feedback."""

    predicate_patterns = (
        (
            "PROHIBIT",
            r"\b(?:does\s+not\s+|do\s+not\s+|not\s+)?"
            r"(?:prohibit|prohibits|prohibited|restrict|restricts|restricted|forbid|forbidden)\b",
        ),
        (
            "PERMIT",
            r"\b(?:does\s+not\s+|do\s+not\s+|not\s+)?"
            r"(?:permit|permits|permitted|allow|allows|allowed)\b",
        ),
        (
            "REQUIRE",
            r"\b(?:does\s+not\s+|do\s+not\s+|not\s+)?"
            r"(?:require|requires|required|must)\b",
        ),
        ("PROHIBIT", r"\b(?:khong\s+)?(?:cam|han\s+che)\b"),
        ("PERMIT", r"\b(?:khong\s+)?(?:duoc\s+phep|cho\s+phep)\b"),
        ("REQUIRE", r"\b(?:khong\s+)?(?:yeu\s+cau|bat\s+buoc)\b"),
    )
    for predicate, pattern in predicate_patterns:
        match = re.search(pattern, folded)
        if match is not None:
            matched = match.group(0)
            return predicate, bool(re.search(r"\b(?:does\s+not|do\s+not|not|khong)\b", matched))
    return None, None


def _scoped_policy_relation_matches(
    requested: _ScopedPolicyProposition,
    candidate: _ScopedPolicyProposition,
) -> bool:
    return (
        candidate.scope == requested.scope
        and _scoped_policy_subjects_align(requested.subject, candidate.subject)
        and bool(requested.actions.intersection(candidate.actions))
        and not (
            requested.objects
            and candidate.objects
            and not requested.objects.intersection(candidate.objects)
        )
    )


def _policy_evidence_segments(evidence: str) -> tuple[str, ...]:
    """Split policy clauses without ranking them by shared topic tokens."""

    normalized = re.sub(r"[ \t]*\r?\n[ \t]*", " ", evidence)
    return tuple(
        segment.strip(" \t\r\n-â€¢ï‚·")
        for segment in re.split(r"(?:[â€¢ï‚·]+|(?<=[.!?;])\s+)", normalized)
        if segment.strip(" \t\r\n-â€¢ï‚·")
    )


def _scoped_policy_subjects_align(requested: str | None, evidence: str | None) -> bool:
    if requested is None or evidence is None:
        return True
    if requested == evidence:
        return True
    # A first-person employee question is normally answered by a policy that
    # governs employees in general.  This is a type-compatible generalization,
    # not a shortcut for object/scope or action alignment.
    return {requested, evidence} == {"SELF", "EMPLOYEE"}


def _claim_repair_feedback(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
    cited_source_labels: tuple[str, ...],
    status: ClaimEvidenceStatus,
) -> ClaimRepairFeedback | None:
    """Return a source-bound failure description when a policy proposition exists.

    The source order favors the cited evidence that caused a contradiction, then
    considers other retrieved sources only to identify an already-displayed
    material policy clause.  It never selects a citation for the answer.
    """

    if not analyze_question(question).is_yes_no:
        return None
    requested = _scoped_policy_proposition(question)
    answer_polarity = infer_yes_no_polarity(answer)
    if requested.scope == "UNSPECIFIED" or not requested.actions or answer_polarity is None:
        return None

    cited = {
        label.strip()[1:-1] if label.strip().startswith("[") else label.strip()
        for label in cited_source_labels
        if label.strip()
    }
    ordered_sources = sorted(
        source_registry.sources,
        key=lambda source: (source.label not in cited, source.label),
    )
    scope_mismatch: tuple[object, _ScopedPolicyProposition, str] | None = None
    for source in ordered_sources:
        if is_non_answer_context(source.text):
            continue
        for segment in _policy_evidence_segments(source.text):
            candidate = _scoped_policy_proposition(segment)
            common_subject = _scoped_policy_subjects_align(requested.subject, candidate.subject)
            common_action = bool(requested.actions.intersection(candidate.actions))
            common_object = not (
                requested.objects
                and candidate.objects
                and not requested.objects.intersection(candidate.objects)
            )
            if (
                common_subject
                and common_action
                and common_object
                and candidate.scope != requested.scope
            ):
                scope_mismatch = (source, candidate, segment)
                continue
            if not _scoped_policy_relation_matches(requested, candidate):
                continue
            if candidate.polarity is None:
                continue
            if status == ClaimEvidenceStatus.CONTRADICTED and candidate.polarity != answer_polarity:
                return _policy_repair_feedback(
                    source=source,
                    proposition=candidate,
                    excerpt=segment,
                    failure_dimension="POLARITY",
                    relation="CONTRADICTED",
                )

    if scope_mismatch is not None:
        source, candidate, segment = scope_mismatch
        return _policy_repair_feedback(
            source=source,
            proposition=candidate,
            excerpt=segment,
            failure_dimension="SCOPE",
            relation="INSUFFICIENT",
        )
    return ClaimRepairFeedback(
        failure_dimension=(
            "CONTRADICTION" if status == ClaimEvidenceStatus.CONTRADICTED else "MATERIAL_SUPPORT"
        ),
        relation=status.value,
    )


def _policy_repair_feedback(
    *,
    source: object,
    proposition: _ScopedPolicyProposition,
    excerpt: str,
    failure_dimension: str,
    relation: str,
) -> ClaimRepairFeedback:
    # PromptSource is intentionally not part of this private function's public
    # surface; both attributes are stable registry invariants.
    return ClaimRepairFeedback(
        failure_dimension=failure_dimension,
        relation=relation,
        source_label=source.label,  # type: ignore[attr-defined]
        evidence_excerpt=" ".join(excerpt.split())[:1200],
        subject=proposition.subject,
        actions=tuple(sorted(proposition.actions)),
        objects=tuple(sorted(proposition.objects))[:24],
        scope=proposition.scope,
        governing_predicate=proposition.governing_predicate,
        negated=proposition.negated,
        effective_polarity=proposition.polarity,
        effective_relation=_effective_policy_relation(proposition),
    )


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

        repair_feedback = None
        if question is not None and status != ClaimEvidenceStatus.SUPPORTED:
            repair_feedback = _claim_repair_feedback(
                question=question,
                answer=answer,
                source_registry=source_registry,
                cited_source_labels=cited_source_labels,
                status=status,
            )

        return ClaimEvidenceValidationResult(
            status=status,
            polarity=validated_polarity,
            repair_feedback=repair_feedback,
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


def _annual_leave_relation_alignment_status(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> ClaimEvidenceStatus | None:
    """Reject leave numbers that belong to a different policy relation."""

    intent = annual_leave_relation_intent(question)
    if intent == "ordinary_allocation":
        relation = ordinary_annual_leave_allocation(evidence)
    elif intent == "seniority_increment":
        years = requested_seniority_years(question)
        relation = (
            annual_leave_seniority_increment(evidence, requested_years=years)
            if years is not None
            else None
        )
    else:
        return None
    if relation is None:
        return ClaimEvidenceStatus.INSUFFICIENT

    folded_answer = fold_text(answer)
    answer_days = tuple(
        int(value) for value in re.findall(r"(?<!\d)(\d{1,2})\s+(?:ngay|days?)\b", folded_answer)
    )
    if not answer_days:
        return ClaimEvidenceStatus.INSUFFICIENT
    allowed_days = {relation.amount_days}
    if relation.seniority_increment_days is not None:
        allowed_days.add(relation.seniority_increment_days)
    if relation.amount_days not in answer_days or any(
        days not in allowed_days for days in answer_days
    ):
        return ClaimEvidenceStatus.CONTRADICTED

    if intent == "seniority_increment":
        answer_years = tuple(
            int(value)
            for value in re.findall(r"(?<!\d)(\d{1,2})\s+(?:nam|years?)\b", folded_answer)
        )
        allowed_years = {relation.seniority_years}
        if relation.seniority_interval_years is not None:
            allowed_years.add(relation.seniority_interval_years)
        if relation.seniority_years not in answer_years or any(
            year not in allowed_years for year in answer_years
        ):
            return ClaimEvidenceStatus.INSUFFICIENT
        if infer_yes_no_polarity(answer) != "YES":
            return ClaimEvidenceStatus.INSUFFICIENT
    return None


def _validate_answer_against_evidence(
    *,
    answer: str,
    evidence: str,
    question: str | None = None,
    require_subject_attribute_alignment: bool = False,
) -> ClaimEvidenceStatus:
    folded_answer = _normalize_broken_number_groups(fold_text(answer))
    folded_evidence = _normalize_broken_number_groups(fold_text(evidence))

    if question is not None and _required_policy_topic_is_missing(
        question=question,
        evidence=folded_evidence,
    ):
        # A verbatim clause is not material support when it answers a different
        # policy topic (for example, weekly rest instead of a payroll date).
        return ClaimEvidenceStatus.INSUFFICIENT
    if (
        question is not None
        and _is_remote_accident_question(question)
        and _required_policy_topic_is_missing(
            question=question,
            evidence=folded_answer,
        )
    ):
        # A relevant cited chunk cannot launder an answer about a different
        # policy topic into a supported claim.
        return ClaimEvidenceStatus.INSUFFICIENT

    analysis = analyze_question(question) if question is not None else None
    is_yes_no = analysis is not None and analysis.is_yes_no

    if question is not None and annual_leave_relation_intent(question):
        leave_status = _annual_leave_relation_alignment_status(
            question=question,
            answer=answer,
            evidence=evidence,
        )
        if leave_status is not None:
            return leave_status

    if question is not None and _prorated_leave_condition_is_missing(
        question=question,
        answer=folded_answer,
        evidence=folded_evidence,
    ):
        return ClaimEvidenceStatus.INSUFFICIENT

    if (
        question is not None
        and (
            bereavement_status := _paid_parent_bereavement_duration_status(
                question=question,
                answer=folded_answer,
                evidence=folded_evidence,
            )
        )
        is not None
    ):
        return bereavement_status

    if (
        question is not None
        and analysis is not None
        and analysis.answer_type == "TIME"
        and _attendance_clock_value_is_aligned(
            question=fold_text(retrieval_query_variants(question).normalized),
            answer=answer,
            evidence=evidence,
        )
    ):
        # Clock punctuation can make the generic number/unit parser read the
        # minute suffix as prose (for example, ``00 thi``). Validate the
        # schedule relationship before that broad contradiction heuristic.
        return ClaimEvidenceStatus.SUPPORTED

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

    if question is not None and _security_control_polarity_is_contradicted(
        question=question,
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

    if question is not None and is_yes_no:
        if _yes_no_answer_restates_question(
            question=question,
            answer=answer,
        ):
            return ClaimEvidenceStatus.INSUFFICIENT
        explicit_unspecified_status = _explicit_unspecified_value_yes_no_status(
            question=question,
            answer=answer,
            evidence=evidence,
        )
        if explicit_unspecified_status is not None:
            return explicit_unspecified_status
        named_benefit_status = _named_monetary_benefit_yes_no_status(
            question=question,
            answer=answer,
            evidence=evidence,
        )
        if named_benefit_status is not None:
            return named_benefit_status
        attendance_status = _attendance_policy_yes_no_status(
            question=question,
            answer=answer,
            evidence=evidence,
        )
        if attendance_status is not None:
            return attendance_status
        credential_status = _credential_transfer_yes_no_status(
            question=question,
            answer=answer,
            evidence=evidence,
        )
        if credential_status is not None:
            return credential_status
        scoped_policy_status = _scoped_policy_yes_no_status(
            question=question,
            answer=answer,
            evidence=evidence,
        )
        if scoped_policy_status is not None:
            return scoped_policy_status

    if (
        question is not None
        and analysis is not None
        and _conditional_allowance_yes_no_status(
            question=question,
            answer=folded_answer,
            evidence=folded_evidence,
        )
        is not None
    ):
        return _conditional_allowance_yes_no_status(
            question=question,
            answer=folded_answer,
            evidence=folded_evidence,
        )

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

        if (
            infer_yes_no_polarity(answer) == "NO"
            and _yes_no_role_anchor_terms(question)
            and _asks_role_person_assignment(question)
            and _answer_introduces_person_name(question=question, answer=answer)
            and _person_lookup_role_relation_missing(
                question=question,
                answer=answer,
                # Keep original record boundaries; focused segments join PDF
                # line wraps and cannot distinguish adjacent person records.
                evidence=evidence,
            )
        ):
            return ClaimEvidenceStatus.INSUFFICIENT

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
        and question is not None
        and _person_lookup_role_relation_missing(
            question=question,
            answer=answer,
            evidence=evidence,
        )
    ):
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


def _conditional_allowance_yes_no_status(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> ClaimEvidenceStatus | None:
    """Validate an explicit monetary allowance and its applicability clause."""

    evidence = " ".join(evidence.split())
    if not analyze_question(question).is_yes_no:
        return None
    allowance_cues = ("phu cap", "tro cap", "allowance", "stipend", "ho tro", "support")
    if not any(cue in fold_text(question) for cue in allowance_cues):
        return None
    if not any(cue in evidence for cue in allowance_cues):
        return None
    if not set(_numbers(answer)).intersection(_numbers(evidence)):
        return None
    polarity = infer_yes_no_polarity(answer)
    if polarity is None:
        return None

    question_terms = _conditional_allowance_terms(question)
    if not question_terms.intersection(_conditional_allowance_terms(evidence)):
        return None

    negative_clause = _conditional_allowance_clause(
        evidence,
        cues=("khong ap dung", "khong duoc huong", "not eligible", "does not apply"),
    )
    positive_clause = _conditional_allowance_clause(
        evidence,
        cues=("ap dung", "duoc phe duyet", "eligible", "approved", "thuong xuyen", "regular"),
    )
    if polarity == "NO":
        if not negative_clause or not any(
            cue in answer
            for cue in ("khong ap dung", "khong duoc huong", "not eligible", "does not apply")
        ):
            return ClaimEvidenceStatus.INSUFFICIENT
        return (
            ClaimEvidenceStatus.SUPPORTED
            if _conditional_allowance_scenario_matches(question, negative_clause)
            else ClaimEvidenceStatus.INSUFFICIENT
        )

    # A YES may establish benefit existence, or a qualifying scenario. It must
    # reproduce an explicit positive relationship rather than a bare amount.
    if not positive_clause:
        return ClaimEvidenceStatus.INSUFFICIENT
    if not any(cue in answer for cue in ("ap dung", "duoc", "eligible", "approved", "regular")):
        return ClaimEvidenceStatus.INSUFFICIENT
    if _conditional_allowance_scenario_matches(question, negative_clause):
        # An explicit exclusion for the premise takes precedence over the
        # benefit's general availability.  A citation that names both must not
        # allow the model to reverse the scenario's polarity.
        return ClaimEvidenceStatus.INSUFFICIENT
    if _conditional_allowance_question_has_scenario(
        question
    ) and not _conditional_allowance_scenario_matches(question, positive_clause):
        # A specific premise needs its own positive entailment.  An amount and
        # a condition for some other arrangement establish neither YES nor NO.
        return ClaimEvidenceStatus.INSUFFICIENT
    return ClaimEvidenceStatus.SUPPORTED


def _explicit_unspecified_value_yes_no_status(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> ClaimEvidenceStatus | None:
    """Validate a direct answer that a requested percentage is not fixed."""

    analysis = analyze_question(question)
    if not (analysis.is_yes_no and analysis.asks_for_percentage):
        return None
    folded_question = fold_text(question)
    asks_whether_fixed = any(
        cue in folded_question
        for cue in (
            "co dinh",
            "quy dinh",
            "ghi ro",
            "neu ro",
            "fixed",
            "specif",
            "state",
        )
    )
    if not asks_whether_fixed:
        return None
    if not has_explicit_not_specified(evidence):
        return None
    return (
        ClaimEvidenceStatus.SUPPORTED
        if _answer_mentions_unspecified(fold_text(answer))
        else ClaimEvidenceStatus.INSUFFICIENT
    )


_NAMED_BENEFIT_FOCUS_STOP_TERMS = frozenset(
    {
        "allowance",
        "benefit",
        "cap",
        "co",
        "cong",
        "company",
        "does",
        "duoc",
        "employee",
        "ho",
        "khoan",
        "khong",
        "nhan",
        "provide",
        "rieng",
        "stipend",
        "support",
        "the",
        "tien",
        "tro",
        "ty",
        "vien",
    }
)


def _named_monetary_benefit_yes_no_status(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> ClaimEvidenceStatus | None:
    """Validate existence of a directly named monetary benefit row.

    This deliberately excludes scenario questions. Eligibility under a
    premise remains governed by the stricter conditional-allowance validator.
    """

    if not analyze_question(question).is_yes_no:
        return None
    folded_question = fold_text(question)
    if not any(
        cue in folded_question
        for cue in ("phu cap", "tro cap", "allowance", "stipend", "ho tro", "benefit")
    ):
        return None
    if _conditional_allowance_question_has_scenario(question):
        return None
    if infer_yes_no_polarity(answer) != "YES":
        return None

    answer_numbers = set(_numbers(_normalize_broken_number_groups(fold_text(answer))))
    if not answer_numbers:
        return None
    focus_terms = tuple(
        dict.fromkeys(
            token
            for token in re.findall(r"\w+", folded_question)
            if len(token) >= 3 and token not in _NAMED_BENEFIT_FOCUS_STOP_TERMS
        )
    )
    if len(focus_terms) < 2:
        return None
    if not all(term in fold_text(answer) for term in focus_terms):
        return None

    evidence_segments = tuple(
        segment.strip() for segment in re.split(r"(?:\n|(?<=[.;])\s+)", evidence) if segment.strip()
    )
    for segment in evidence_segments:
        folded_segment = _normalize_broken_number_groups(fold_text(segment))
        if not answer_numbers.intersection(_numbers(folded_segment)):
            continue
        if all(term in folded_segment for term in focus_terms):
            return ClaimEvidenceStatus.SUPPORTED
    return None


def _conditional_allowance_terms(text: str) -> frozenset[str]:
    canonical = fold_text(text)
    canonical = re.sub(r"\b(?:wfh|work\s+from\s+home|lam\s+o\s+nha)\b", "remote", canonical)
    return frozenset(
        token
        for token in re.findall(r"\w+", canonical)
        if len(token) >= 3
        and token
        not in {
            "cong",
            "ty",
            "duoc",
            "co",
            "ho",
            "tro",
            "tien",
            "phu",
            "cap",
            "allowance",
            "stipend",
            "support",
            "khong",
            "ap",
            "dung",
            "cho",
            "the",
            "does",
            "not",
            "apply",
            "eligible",
        }
    )


def _conditional_allowance_clause(text: str, *, cues: tuple[str, ...]) -> str:
    for segment in re.split(r"(?:\n|(?<=[.;])\s+)", text):
        if any(cue in segment for cue in cues):
            return segment
    return ""


def _conditional_allowance_scenario_matches(question: str, clause: str) -> bool:
    question_terms = _conditional_allowance_terms(question)
    clause_terms = _conditional_allowance_terms(clause)
    shared = question_terms.intersection(clause_terms)
    if len(shared) >= 2:
        return True
    folded_question = fold_text(question)
    folded_clause = fold_text(clause)
    single_question = bool(re.search(r"\b(?:mot|one|1|single|don le|ad hoc)\b", folded_question))
    single_clause = bool(re.search(r"\b(?:mot|one|1|single|don le|ad hoc)\b", folded_clause))
    return bool(shared and single_question and single_clause)


def _conditional_allowance_question_has_scenario(question: str) -> bool:
    folded = fold_text(question)
    return bool(re.search(r"(?<!\d)\d+(?!\d)", folded)) or any(
        cue in folded
        for cue in (
            "neu ",
            "if ",
            "truong hop",
            "ngay ",
            "day ",
            "mot ",
            "single ",
            "ad hoc",
            "regular ",
            "thuong xuyen",
            "arrangement",
            "scenario",
        )
    )


def _evidence_for_labels(
    *,
    source_registry: PromptSourceRegistry,
    cited_source_labels: tuple[str, ...],
) -> str:
    parts: list[str] = []
    for label in cited_source_labels:
        marker = f"[{label}]" if not label.startswith("[") else label
        source = source_registry.by_marker(marker)
        if source is not None and not is_non_answer_context(source.text):
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
    matched_count = sum(
        1
        for anchor in anchors
        if _contains_folded_term(folded_evidence, anchor)
        or any(
            anchor in group
            and any(
                _contains_folded_term(folded_evidence, alternative)
                for alternative in group
                if alternative != anchor
            )
            for group in _YES_NO_SEMANTIC_ANCHOR_GROUPS
        )
    )
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


def _attendance_policy_yes_no_status(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> ClaimEvidenceStatus | None:
    """Validate bounded attendance scenarios with explicit policy outcomes."""

    folded_question = " ".join(fold_text(question).split())
    folded_answer = " ".join(fold_text(answer).split())
    folded_evidence = " ".join(fold_text(evidence).split())
    polarity = infer_yes_no_polarity(answer)

    late_arrival = any(
        cue in folded_question for cue in ("di muon", "toi tre", "arrive late", "late arrival")
    )
    if late_arrival:
        same_day = any(cue in folded_question for cue in ("toi nay", "cung ngay", "same day"))
        next_day = any(cue in folded_question for cue in ("ngay mai", "ngay khac", "next day"))
        if same_day:
            evidence_supports = all(
                cue in folded_evidence for cue in ("bu trong cung ngay", "quan ly chap thuan")
            )
            answer_is_bound = "bu trong cung ngay" in folded_answer
            return (
                ClaimEvidenceStatus.SUPPORTED
                if evidence_supports and answer_is_bound and polarity == "YES"
                else ClaimEvidenceStatus.CONTRADICTED
                if evidence_supports and polarity == "NO"
                else ClaimEvidenceStatus.INSUFFICIENT
            )
        if next_day:
            evidence_supports = any(
                cue in folded_evidence
                for cue in ("khong duoc tu y bu sang ngay khac", "not make up on another day")
            )
            answer_is_bound = any(
                cue in folded_answer for cue in ("bu sang ngay khac", "another day")
            )
            return (
                ClaimEvidenceStatus.SUPPORTED
                if evidence_supports and answer_is_bound and polarity == "NO"
                else ClaimEvidenceStatus.CONTRADICTED
                if evidence_supports and polarity == "YES"
                else ClaimEvidenceStatus.INSUFFICIENT
            )

    on_call = any(cue in folded_question for cue in ("on-call", "on call", "truc")) and any(
        cue in folded_question for cue in ("incident", "su co", "ot", "lam them")
    )
    if on_call:
        evidence_supports = all(
            cue in folded_evidence for cue in ("on-call", "khong tu dong")
        ) and any(
            cue in folded_evidence
            for cue in ("thoi gian thuc te xu ly", "actual incident handling time")
        )
        answer_is_bound = "khong tu dong" in folded_answer and any(
            cue in folded_answer
            for cue in ("thoi gian thuc te xu ly", "actual incident handling time")
        )
        return (
            ClaimEvidenceStatus.SUPPORTED
            if evidence_supports and answer_is_bound and polarity == "NO"
            else ClaimEvidenceStatus.CONTRADICTED
            if evidence_supports and polarity == "YES"
            else ClaimEvidenceStatus.INSUFFICIENT
        )

    remote_attendance = any(
        cue in folded_question for cue in ("remote", "lam o nha", "work from home")
    ) and any(cue in folded_question for cue in ("cham cong", "check-in", "checkout"))
    if remote_attendance:
        evidence_supports = any(
            cue in folded_evidence
            for cue in ("nghia vu cham cong", "van phai cham cong", "must clock")
        )
        answer_is_bound = any(
            cue in folded_answer
            for cue in ("nghia vu cham cong", "van phai cham cong", "must clock")
        )
        return (
            ClaimEvidenceStatus.SUPPORTED
            if evidence_supports and answer_is_bound and polarity == "YES"
            else ClaimEvidenceStatus.CONTRADICTED
            if evidence_supports and polarity == "NO"
            else ClaimEvidenceStatus.INSUFFICIENT
        )

    return None


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
    return (
        _answer_mentions_unspecified(answer)
        and not has_explicit_not_specified(evidence)
        and bool(_number_unit_pairs(evidence))
    )


def _paid_parent_bereavement_duration_status(
    *, question: str, answer: str, evidence: str
) -> ClaimEvidenceStatus | None:
    folded_question = fold_text(question)
    if not (
        any(cue in folded_question for cue in ("ba me", "bo me", "cha me", "parent"))
        and any(cue in folded_question for cue in ("mat", "chet", "qua doi", "death", "died"))
        and any(cue in folded_question for cue in ("huong luong", "paid"))
    ):
        return None
    paid_heading = re.search(r"\bnghi viec rieng huong luong\b|\bpaid bereavement\b", evidence)
    if paid_heading is None:
        return ClaimEvidenceStatus.INSUFFICIENT
    paid_section = evidence[paid_heading.end() :].split("nghi viec rieng khong huong luong", 1)[0]
    parent = re.search(r"\b(?:cha/me|cha me|ba me|bo me|parent)\b", paid_section)
    if parent is None:
        return ClaimEvidenceStatus.INSUFFICIENT
    death = re.search(r"\b(?:chet|qua doi|death|died)\b", paid_section[parent.end() :])
    if death is None or death.start() > 220:
        return ClaimEvidenceStatus.INSUFFICIENT
    row = paid_section[parent.start() : parent.end() + death.end()]
    row_days = {
        _normalized_number(value)
        for value in re.findall(r"(?<!\d)(\d{1,2})\s+(?:ngay|days?)\b", row)
    }
    answer_days = {
        _normalized_number(value)
        for value in re.findall(r"(?<!\d)(\d{1,2})\s+(?:ngay|days?)\b", answer)
    }
    if len(row_days) != 1 or not answer_days:
        return ClaimEvidenceStatus.INSUFFICIENT
    return (
        ClaimEvidenceStatus.SUPPORTED
        if answer_days == row_days
        else ClaimEvidenceStatus.CONTRADICTED
    )


def _prorated_leave_condition_is_missing(*, question: str, answer: str, evidence: str) -> bool:
    """Do not give the full-year allocation for a shorter employment period."""
    folded_question = fold_text(question)
    if not any(cue in folded_question for cue in ("phep", "nghi hang nam", "annual leave")):
        return False
    asks_for_partial_year = bool(
        re.search(r"\bchua(?:\s+lam)?\s+du\s+(?:mot|1)\s+nam\b", folded_question)
        or re.search(r"\bchua(?:\s+lam)?\s+du\s+12\s+thang\b", folded_question)
        or re.search(r"\b(?:under|less than)\s+(?:one|1)\s+year\b", folded_question)
    )
    if not asks_for_partial_year:
        return False
    proportional_cues = ("theo ty le", "tuong ung voi thoi gian", "pro rata", "proportional")
    return any(cue in evidence for cue in proportional_cues) and not any(
        cue in answer for cue in proportional_cues
    )


def _security_control_requirement_is_missing(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    asks_for_controls = _asks_for_security_controls(question)
    if not asks_for_controls:
        return False
    available_controls = {cue for cue in _SECURITY_CONTROL_CUES if cue in evidence}
    claimed_controls = {cue for cue in _SECURITY_CONTROL_CUES if cue in answer}
    if claimed_controls:
        return not claimed_controls.issubset(available_controls)
    return bool(available_controls)


def _security_control_polarity_is_contradicted(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    """Reject a prohibition of a control that the cited policy requires using."""
    if not _asks_for_security_controls(question):
        return False
    for cue in _SECURITY_CONTROL_CUES:
        control = re.escape(cue)
        prohibited_use = re.search(
            rf"\b(?:khong\s+(?:su\s+dung|dung)|(?:do\s+not|don't|not)\s+use)\s+{control}\b",
            answer,
        )
        if not prohibited_use:
            continue
        required_use = re.search(rf"\b(?:su\s+dung|dung|use)\s+{control}\b", evidence)
        preceding_evidence = (
            evidence[max(0, required_use.start() - 12) : required_use.start()]
            if required_use
            else ""
        )
        if required_use and not re.search(r"\b(?:khong|not)\s+$", preceding_evidence):
            return True
    return False


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


def _person_lookup_role_relation_missing(*, question: str, answer: str, evidence: str) -> bool:
    """Require the cited person and requested role in one source proposition.

    An orphan role at a chunk boundary can precede the next person's record.
    Mere co-occurrence of the role and that next name is not support, and a
    role in a later person's record cannot be attributed to an earlier name.
    """
    requested_roles = _yes_no_role_anchor_terms(question)
    if not requested_roles:
        return False
    names = _person_name_claim_candidates(question=fold_text(question), answer=fold_text(answer))
    if not names:
        return False
    folded_evidence = fold_text(evidence)
    for name in names:
        name_pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
        for match in re.finditer(rf"{name_pattern}[ \t]*[-|:][ \t]+", folded_evidence):
            record_tail = folded_evidence[match.end() : match.end() + 180]
            record_tail = re.split(r"\n\s*\n", record_tail, maxsplit=1)[0]
            next_record = _PERSON_RECORD_START_RE.search(record_tail)
            if next_record is not None:
                record_tail = record_tail[: next_record.start()]
            role_match = re.search(r"\(([a-z]{2,8})\)", record_tail)
            if role_match is not None and role_match.group(1) in requested_roles:
                return False
        for role in requested_roles:
            direct_patterns = (
                rf"\b{re.escape(role)}\b"
                rf"(?:[ \t]+[^.\n;:()|/-]{{1,60}}?)?"
                rf"[ \t]+(?:is|la|named|held by)[ \t]+{name_pattern}",
                rf"\b{re.escape(role)}\b[ \t]*[:-][ \t]*{name_pattern}",
                rf"{name_pattern}[ \t]+(?:is|la|serves as|giu vai tro|dam nhan)[ \t]+"
                rf"(?:the[ \t]+)?\b{re.escape(role)}\b",
                rf"{name_pattern}[ \t]*\([ \t]*{re.escape(role)}[ \t]*\)",
            )
            if any(re.search(pattern, folded_evidence) for pattern in direct_patterns):
                return False
    return True


_PERSON_RECORD_START_RE = re.compile(
    r"\n[ \t]*(?:[-•][ \t]+)?(?:[^\W\d_]+[ \t]+){1,5}[^\W\d_]+[ \t]*[-|:][ \t]+"
)


def _asks_role_person_assignment(question: str) -> bool:
    folded_question = f" {fold_text(question)} "
    return any(
        cue in folded_question
        for cue in (" la ", " is ", " are ", " co phai ", " serve as ", " held by ")
    )


def _answer_introduces_person_name(*, question: str, answer: str) -> bool:
    """Distinguish a person correction from policy answers containing acronyms."""

    question_terms = set(re.findall(r"\w+", fold_text(question)))
    name_run: list[str] = []
    previous_end = 0
    for match in re.finditer(r"[^\W\d_]+", answer):
        token = match.group()
        titlecased = token[:1].isupper() and not token.isupper()
        if titlecased and (not name_run or answer[previous_end : match.start()].isspace()):
            name_run.append(token)
        else:
            name_run = [token] if titlecased else []
        if (
            len(name_run) >= 3
            and sum(fold_text(term) not in question_terms for term in name_run) >= 2
        ):
            return True
        previous_end = match.end()
    return False


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

    example_alignment = _example_expense_amount_is_aligned(
        question=question,
        answer=answer,
        evidence=evidence,
    )
    if example_alignment is not None:
        return example_alignment

    if _is_pay_date_question(question) and not _pay_date_numbers_are_locally_bound(
        answer_numbers=answer_numbers,
        evidence=evidence,
    ):
        return False

    folded_question = fold_text(retrieval_query_variants(question).normalized)
    leave_notice_alignment = _leave_notice_value_is_aligned(
        question=folded_question,
        answer=answer,
        evidence=evidence,
    )
    if leave_notice_alignment is not None:
        return leave_notice_alignment
    if analysis.asks_for_duration and _work_schedule_duration_is_aligned(
        question=folded_question,
        answer=answer,
        evidence=evidence,
    ):
        return True
    if analysis.asks_for_time_range:
        schedule_aligned = _work_schedule_time_range_is_aligned(
            question=folded_question,
            answer=answer,
            evidence=evidence,
        )
        if schedule_aligned:
            return True
        if any(
            cue in folded_question
            for cue in (
                "gio cot loi",
                "core hour",
                "khung bat dau",
                "start window",
                "khung ket thuc",
                "end window",
            )
        ):
            return False
    if analysis.answer_type == "TIME" and _attendance_clock_value_is_aligned(
        question=folded_question,
        answer=answer,
        evidence=evidence,
    ):
        return True
    if (
        analysis.answer_type == "TIME"
        and any(cue in folded_question for cue in ("gio cot loi", "core hour"))
        and any(
            cue in folded_question for cue in ("buoi sang", "buoi chieu", "morning", "afternoon")
        )
    ):
        return _core_schedule_endpoint_is_aligned(
            question=folded_question,
            answer=answer,
            evidence=evidence,
        )
    remote_cues = ("remote", "hybrid", "lam o nha", "lam viec tu xa", "work from home")
    asks_for_remote_value = any(cue in folded_question for cue in remote_cues)
    question_focus = {
        term
        for term in re.findall(r"\w+", folded_question)
        if len(term) >= 3 and term not in _VALUE_ALIGNMENT_STOP_TERMS
    }
    if asks_for_remote_value:
        question_focus.difference_update({"hybrid", "remote", "nha"})
    requested_period = (
        requested_monetary_period(folded_question) if analysis.asks_for_amount else None
    )
    if not question_focus and not asks_for_remote_value and requested_period is None:
        return True
    answer_money_values = monetary_value_numbers(answer) or answer_numbers
    evidence_period_pairs = monetary_value_period_pairs(evidence)
    for value, period in monetary_value_period_pairs(answer):
        period_values = monetary_period_bound_numbers(evidence, period=period)
        if period_values and value not in period_values:
            return False
        if not period_values and any(
            evidence_value == value and evidence_period != period
            for evidence_value, evidence_period in evidence_period_pairs
        ):
            return False
    period_bound = False
    if requested_period is not None:
        answer_periods = {period for _, period in monetary_value_period_pairs(answer)}
        if answer_periods and answer_periods != {requested_period}:
            return False
        period_values = monetary_period_bound_numbers(evidence, period=requested_period)
        if period_values:
            subject_phrases = (
                ()
                if asks_for_remote_value
                else _requested_value_subject_phrases(
                    question=folded_question,
                    question_focus=question_focus,
                )
            )
            subject_values = monetary_period_bound_numbers(
                evidence,
                period=requested_period,
                subject_phrases=subject_phrases,
            )
            if not subject_values or answer_money_values.isdisjoint(subject_values):
                return False
            period_bound = True
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
        and not period_bound
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


def _example_expense_amount_is_aligned(*, question: str, answer: str, evidence: str) -> bool | None:
    """Validate an amount joined across adjacent example/limit table cells."""

    if not analyze_question(question).asks_for_amount:
        return None
    focus_terms = tuple(
        term
        for term in re.findall(r"\w+", fold_text(question))
        if len(term) >= 3
        and term not in _VALUE_ALIGNMENT_STOP_TERMS
        and term not in {"cong", "ty", "company", "firm"}
    )
    rows = monetary_example_rows(evidence, focus_terms=focus_terms)
    if not rows:
        return None
    answer_values = monetary_value_numbers(answer)
    requested_period = requested_monetary_period(question)
    answer_periods = {period for _, period in monetary_value_period_pairs(answer)}
    for row in rows:
        if answer_values != monetary_value_numbers(row.row_value):
            continue
        row_periods = {period for _, period in monetary_value_period_pairs(row.row_value)}
        if requested_period is not None and (
            row_periods != {requested_period} or answer_periods != {requested_period}
        ):
            continue
        return True
    return False


def _leave_notice_value_is_aligned(*, question: str, answer: str, evidence: str) -> bool | None:
    """Bind requested leave length to its advance-notice row, when present."""
    if not (
        re.search(r"\b(?:nghi|phep|leave)\b", question)
        and re.search(r"\b(?:truoc|advance|notice)\b", question)
    ):
        return None
    longer_than = re.search(r"\b(?:hon|tren|more than|over)\s+(\d+)\s+(?:ngay|day)", question)
    exact_length = re.search(r"\b(\d+)\s+(?:ngay|day)", question)
    if not longer_than and not exact_length:
        return None
    requested_length = int((longer_than or exact_length).group(1))
    normalized = re.sub(r"\s+", " ", fold_text(evidence))
    normalized = re.sub(r"(?<=\d)\s*-\s*(?:-\s*)?(?=\d)", "-", normalized)
    normalized = re.sub(r"(?<=\D)-\s*(?=\d)", "", normalized)
    range_rows = tuple(
        (int(match.group(1)), int(match.group(2)), _normalized_number(match.group(3)))
        for match in re.finditer(
            r"\bphep nam\s+(\d+)-(\d+)\s+ngay\s+truoc\s+it nhat\s+(\d+)\s+ngay",
            normalized,
        )
    )
    over_rows = tuple(
        (int(match.group(1)), _normalized_number(match.group(2)))
        for match in re.finditer(
            r"\bphep nam\s+tren\s+(\d+)\s+ngay\s+truoc\s+it nhat\s+(\d+)\s+ngay",
            normalized,
        )
    )
    if not range_rows and not over_rows:
        return False
    matching_values = {
        value
        for lower, upper, value in range_rows
        if not longer_than and lower <= requested_length <= upper
    }
    matching_values.update(
        value for threshold, value in over_rows if longer_than and requested_length >= threshold
    )
    if len(matching_values) != 1:
        return False
    notice_value = next(iter(matching_values))
    answer_notice = re.search(
        r"\b(?:truoc|bao truoc|xin truoc|gui truoc|advance notice)\s+"
        r"(?:it nhat\s+)?(\d+)\s+(?:ngay|day)",
        fold_text(answer),
    )
    if answer_notice:
        return _normalized_number(answer_notice.group(1)) == notice_value
    answer_numbers = set(_numbers(answer))
    return answer_numbers == {notice_value}


def _attendance_clock_value_is_aligned(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    """Bind an attendance clock to its policy field or paired schedule row."""

    answer_clocks = {
        re.sub(r"\s+", "", value) for value in _CLOCK_VALUE_RE.findall(fold_text(answer))
    }
    folded_evidence = fold_text(evidence)
    evidence_clocks = {
        re.sub(r"\s+", "", value) for value in _CLOCK_VALUE_RE.findall(folded_evidence)
    }
    if not answer_clocks or not answer_clocks.issubset(evidence_clocks):
        return False

    registration_question = any(
        cue in question for cue in ("dang ky", "register", "registration", "deadline")
    )
    if registration_question:
        has_registration_evidence = any(
            cue in folded_evidence
            for cue in ("dang ky", "register", "registration", "ngay lam viec lien truoc")
        )
        asks_remote = any(
            cue in question for cue in ("remote", "hybrid", "lam o nha", "work from home")
        )
        has_remote = any(
            cue in folded_evidence for cue in ("remote", "hybrid", "lam o nha", "work from home")
        )
        return has_registration_evidence and (not asks_remote or has_remote)

    asks_corresponding_end = any(
        cue in question for cue in ("may gio duoc ve", "gio duoc ve", "ket thuc", "finish", "leave")
    )
    if not asks_corresponding_end:
        return False
    return all(
        any(cue in folded_evidence for cue in cue_group)
        for cue_group in (
            ("khung bat dau", "flexible start", "start window"),
            ("khung ket thuc", "corresponding end", "end window"),
        )
    )


def _core_schedule_endpoint_is_aligned(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    """Check a morning/afternoon core-hour endpoint against its own field."""

    answer_clocks = tuple(_CLOCK_VALUE_RE.findall(fold_text(answer)))
    if len(answer_clocks) != 1:
        return False
    is_afternoon = any(cue in question for cue in ("buoi chieu", "afternoon"))
    is_morning = any(cue in question for cue in ("buoi sang", "morning"))
    asks_start = any(cue in question for cue in ("bat dau", "starts at", "start at"))
    asks_end = any(cue in question for cue in ("ket thuc", "ends at", "end at"))
    if is_afternoon == is_morning or asks_start == asks_end:
        return False
    for label in re.finditer(r"\b(?:gio cot loi|core hours?)\b", evidence):
        trailing = evidence[label.end() :]
        next_field = re.search(
            r"\b(?:khung bat dau|khung ket thuc|nghi trua|lunch break|"
            r"gio cot loi|core hours?)\b",
            trailing,
        )
        field_text = trailing[: next_field.start() if next_field else 150]
        field_lines = field_text.splitlines()
        if field_lines:
            field_text = field_lines[0]
            if not _CLOCK_VALUE_RE.search(field_text) and len(field_lines) > 1:
                field_text = field_lines[1]
        clocks = tuple(_CLOCK_VALUE_RE.findall(field_text))
        if len(clocks) != 4:
            continue
        position = (2 if is_afternoon else 0) + (0 if asks_start else 1)
        if re.sub(r"\s+", "", answer_clocks[0]) == re.sub(r"\s+", "", clocks[position]):
            return True
    return False


def _work_schedule_duration_is_aligned(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    """Bind ordinary work-duration values to their day/week schedule row."""

    asks_work_duration = any(
        cue in question
        for cue in (
            "lam bao nhieu gio",
            "lam may gio",
            "lam bao nhieu tieng",
            "lam may tieng",
            "working hours",
            "work hours",
        )
    )
    if not asks_work_duration:
        return False
    if not any(
        cue in evidence
        for cue in (
            "tong thoi gian lam viec",
            "thoi gian lam viec tieu chuan",
            "standard working time",
            "standard working hours",
        )
    ):
        return False

    answer_numbers = set(_numbers(answer))
    if not answer_numbers:
        return False
    requested_periods = tuple(
        period
        for period, cues in (
            ("ngay", ("moi ngay", "mot ngay", "per day", "daily")),
            ("tuan", ("moi tuan", "mot tuan", "per week", "weekly")),
        )
        if any(cue in question for cue in cues)
    )
    if not requested_periods:
        return False

    for match in _NUMBER_RE.finditer(evidence):
        if _normalized_number(match.group(0)) not in answer_numbers:
            continue
        bound_value = evidence[match.start() : min(len(evidence), match.end() + 40)]
        if any(
            re.match(
                rf"\d+(?:[.,]\d+)?\s*(?:gio|hours?)\s*"
                rf"(?:/|moi\s+|per\s+){re.escape(period)}\b",
                bound_value,
            )
            is not None
            for period in requested_periods
        ):
            return True
    return False


def _work_schedule_time_range_is_aligned(
    *,
    question: str,
    answer: str,
    evidence: str,
) -> bool:
    """Require schedule clock values to stay attached to the requested row."""

    answer_clocks = {re.sub(r"\s+", "", value) for value in _CLOCK_VALUE_RE.findall(answer)}
    evidence_matches = tuple(_CLOCK_VALUE_RE.finditer(evidence))
    evidence_clocks = {re.sub(r"\s+", "", match.group(0)) for match in evidence_matches}
    if len(answer_clocks) < 2 or not answer_clocks.issubset(evidence_clocks):
        return False

    if "core hour" in question or "gio cot loi" in question:
        row_cues = ("gio cot loi", "core hour")
    elif any(cue in question for cue in ("bat dau", "start window")) or (
        "vao" in question and "lam" in question
    ):
        row_cues = ("khung bat dau", "bat dau linh hoat", "start window")
    elif any(cue in question for cue in ("ket thuc", "end window")):
        row_cues = ("khung ket thuc", "ket thuc tuong ung", "end window")
    elif any(cue in question for cue in ("khung gio", "time range", "working hours")):
        row_cues = ("khung gio", "thoi gian lam viec", "working hours")
    else:
        return False

    all_row_cues = (
        "gio cot loi",
        "core hour",
        "khung bat dau",
        "bat dau linh hoat",
        "start window",
        "khung ket thuc",
        "ket thuc tuong ung",
        "end window",
        "nghi trua",
        "lunch break",
    )
    requested_spans = tuple(
        cue_match.span()
        for cue in row_cues
        for cue_match in re.finditer(rf"(?<!\w){re.escape(cue)}(?!\w)", evidence)
    )
    all_spans = tuple(
        cue_match.span()
        for cue in all_row_cues
        for cue_match in re.finditer(rf"(?<!\w){re.escape(cue)}(?!\w)", evidence)
    )
    if not requested_spans:
        return False

    for answer_clock in answer_clocks:
        matching_clocks = tuple(
            match
            for match in evidence_matches
            if re.sub(r"\s+", "", match.group(0)) == answer_clock
        )
        aligned = False
        for match in matching_clocks:
            preceding = tuple(span for span in all_spans if span[1] <= match.start())
            if preceding:
                nearest = max(preceding, key=lambda span: span[1])
                if nearest in requested_spans:
                    aligned = True
                    break
            elif any(0 <= span[0] - match.end() <= 16 for span in requested_spans):
                # OCR can place a short field label immediately after a value.
                aligned = True
                break
        if not aligned:
            return False
    return True


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
    return any(
        term in folded for term in ("luong", "payroll", "salary", "pay date", "payday")
    ) and any(cue in folded for cue in ("ngay nao", "when", "pay date", "ngay tra"))


def _required_policy_topic_is_missing(*, question: str, evidence: str) -> bool:
    """Keep a copied clause attached to the requested policy relation."""

    if _is_pay_date_question(question):
        return not any(
            cue in evidence for cue in ("tra luong", "pay date", "payday", "salary payment")
        )
    if _is_remote_accident_question(question):
        return not any(cue in evidence for cue in ("tai nan", "accident"))
    return False


def _is_remote_accident_question(question: str) -> bool:
    folded_question = fold_text(question)
    return any(
        cue in folded_question
        for cue in ("remote", "lam o nha", "lam viec tu xa", "work from home")
    ) and any(cue in folded_question for cue in ("tai nan", "accident"))


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


def _credential_transfer_yes_no_status(
    *, question: str, answer: str, evidence: str
) -> ClaimEvidenceStatus | None:
    """Bind a credential-transfer question to a same-object sharing rule."""

    folded_question = fold_text(question)
    if not any(
        cue in folded_question for cue in ("dua", "gui", "chia se", "give", "send", "share")
    ):
        return None
    object_families = (
        ("mat khau", "password", "passwords"),
        ("otp", "one time password", "one-time password"),
        ("khoa api", "api key"),
        ("token truy cap", "access token"),
    )
    requested = tuple(
        family for family in object_families if any(cue in folded_question for cue in family)
    )
    if not requested:
        return None
    folded_answer = fold_text(answer)
    if not any(cue in folded_answer for family in requested for cue in family) or not any(
        cue in folded_answer for cue in ("dua", "gui", "chia se", "give", "send", "share")
    ):
        return ClaimEvidenceStatus.INSUFFICIENT
    for segment in _policy_evidence_segments(evidence):
        folded_segment = fold_text(segment)
        if not any(cue in folded_segment for family in requested for cue in family):
            continue
        if not any(
            cue in folded_segment
            for cue in ("cam chia se", "khong duoc chia se", "must not share", "do not share")
        ):
            continue
        # An unconditional credential-sharing prohibition cannot support a
        # generated exception borrowed from a neighboring data-sharing rule.
        if any(
            cue in folded_answer
            for cue in (
                "chi duoc chia se",
                "duoc chia se khi",
                "chia se khi co phe duyet",
                "may share if",
                "with approval",
                "unless approved",
            )
        ) and not any(
            cue in folded_segment for cue in ("tru khi", "ngoai tru", "unless", "except")
        ):
            return ClaimEvidenceStatus.CONTRADICTED
        return (
            ClaimEvidenceStatus.SUPPORTED
            if infer_yes_no_polarity(answer) == "NO"
            else ClaimEvidenceStatus.CONTRADICTED
        )
    return ClaimEvidenceStatus.INSUFFICIENT


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
