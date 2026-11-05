from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_WORD_RE = re.compile(r"\w+", re.UNICODE)

_VIETNAMESE_BASE_TRANSLATION = str.maketrans(
    {
        "\u0111": "d",
        "\u0110": "d",
        "\u01b0": "u",
        "\u01af": "u",
        "\u01a1": "o",
        "\u01a0": "o",
    }
)

ANSWER_TYPES = frozenset(
    {
        "PERSON",
        "ORGANIZATION",
        "DATE",
        "YEAR",
        "NUMBER",
        "COUNT",
        "AMOUNT",
        "PERCENTAGE",
        "TIME",
        "TIME_RANGE",
        "TIMELINE",
        "DURATION",
        "YES_NO",
        "LIST",
        "DEFINITION",
        "PURPOSE",
        "POLICY_CONDITION",
        "EXPLANATION",
        "OTHER",
    }
)


@dataclass(frozen=True, slots=True)
class QuestionAnalysis:
    answer_type: str
    is_yes_no: bool = False
    asks_for_time_range: bool = False
    asks_for_timeline: bool = False
    asks_for_person: bool = False
    asks_for_amount: bool = False
    asks_for_percentage: bool = False
    asks_for_count: bool = False
    asks_for_duration: bool = False
    asks_for_policy_condition: bool = False
    asks_for_explicit_value: bool = False

    def __post_init__(self) -> None:
        if self.answer_type not in ANSWER_TYPES:
            msg = "answer_type is not supported."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RetrievalQueryVariants:
    """Safe retrieval forms; the original question remains answer-facing."""

    original: str
    normalized: str
    diacritic_insensitive: str

    def __post_init__(self) -> None:
        for name in ("original", "normalized", "diacritic_insensitive"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")


_CONVERSATIONAL_REPLACEMENTS = {
    "bn": "bao nhieu",
    "ko": "khong",
    "khong": "khong",
    "dc": "duoc",
    "cty": "cong ty",
    "nv": "nhan vien",
    "tieng": "gio",
    "wfh": "remote",
}


def retrieval_query_variants(question: str) -> RetrievalQueryVariants:
    """Build conservative retrieval-only forms without changing question meaning."""
    original = " ".join(question.strip().split())
    if not original:
        raise ValueError("question must not be empty.")
    normalized = re.sub(r"\s+", " ", original)
    normalized = re.sub(r"\s*([?!.,:;])\s*", r"\1 ", normalized).strip()
    folded = fold_text(normalized)
    tokens = re.findall(r"\w+|[^\w\s]", folded, re.UNICODE)
    folded_tokens = " ".join(tokens).strip()
    expanded: list[str] = []
    for token in tokens:
        expanded.extend(_CONVERSATIONAL_REPLACEMENTS.get(token, token).split())
    normalized_retrieval = " ".join(expanded).strip()
    canonical_retrieval = _canonicalize_retrieval_language(normalized_retrieval)
    semantic_normalized = (
        canonical_retrieval
        if canonical_retrieval != normalized_retrieval or normalized_retrieval != folded_tokens
        else normalized
    )
    return RetrievalQueryVariants(
        original=original,
        normalized=semantic_normalized,
        diacritic_insensitive=canonical_retrieval or folded,
    )


def _canonicalize_retrieval_language(value: str) -> str:
    """Normalize narrow conversational policy phrases without adding facts."""
    canonical = re.sub(r"\bproduction\s+incident\b", "su co", value)
    # Retrieval-only vocabulary: common English developer phrasing should
    # find a Vietnamese policy clause about the same repository/credential.
    canonical = re.sub(r"\bsource\s+code\b", "ma nguon", canonical)
    canonical = re.sub(r"\bgithub\b", "kho ma nguon", canonical)
    if any(cue in canonical for cue in ("ho tro", "tro cap", "phuc loi", "benefit", "support")):
        # In benefit questions, conversational Vietnamese ``có con`` names
        # the same life event that policy tables normally label ``sinh con``.
        canonical = re.sub(r"\bco con\b", "sinh con", canonical)
    if any(
        cue in canonical
        for cue in (
            "nghi phep",
            "on call",
            "on-call",
            "hybrid",
            "remote",
            "phu cap",
            "tro cap",
            "bao hiem",
        )
    ):
        canonical = re.sub(r"\btoi\b", "nhan vien", canonical)
        canonical = re.sub(r"\bma phai\b", "nhung phai", canonical)
    canonical = re.sub(
        r"\bcan tuan thu bao mat (?:nao|gi)\b",
        "yeu cau bao mat gi",
        canonical,
    )
    canonical = re.sub(
        r"\bphai (?:bao dam|dam bao) an toan gi\b",
        "yeu cau bao mat gi",
        canonical,
    )
    if re.search(r"\b(?:checkout|check\s*-?\s*out)\b", canonical):
        canonical = f"{canonical} cham cong dieu chinh"
    if "nam vien" in canonical:
        canonical = re.sub(r"\bnam vien\b", "noi tru", canonical)
    if "yeu cau bao mat gi" in canonical and any(
        cue in canonical for cue in ("hybrid", "lam o nha", "lam viec tu xa")
    ):
        return "lam viec tu xa yeu cau bao mat"
    return canonical


def analyze_question(question: str) -> QuestionAnalysis:
    folded = fold_text(question)
    padded = f" {folded} "
    is_yes_no = (
        _is_yes_no_question(folded)
        and "bao nhieu" not in folded
        and "how many" not in folded
        and "how much" not in folded
    )
    asks_for_person = _asks_for_person(folded)
    asks_for_organization = _asks_for_organization(folded)
    asks_for_percentage = (
        "phan tram" in folded or "%" in question or _asks_for_percentage_like(folded)
    )
    asks_for_timeline = _asks_for_timeline(folded)
    asks_for_amount = (
        False
        if asks_for_percentage or asks_for_timeline
        else (_asks_for_amount(folded) or _asks_for_salary_band_value(folded))
    )
    asks_for_count = _asks_for_count(folded)
    # A yes/no question can mention a time field (for example, whether remote
    # staff must keep core hours) without asking the model to return the range.
    # Treating the field name itself as a range request activates numeric
    # extraction and can discard the governing policy clause.
    asks_for_clock_time = _asks_for_time(folded)
    asks_for_named_endpoint = asks_for_clock_time and any(
        cue in folded
        for cue in ("bat dau", "ket thuc", "starts at", "start at", "ends at", "end at")
    )
    asks_for_time_range = _asks_for_time_range(folded) and not (
        is_yes_no or asks_for_named_endpoint
    )
    asks_for_duration = (
        False
        if asks_for_amount or asks_for_time_range or asks_for_clock_time
        else _asks_for_duration(folded)
    )
    asks_for_date = _asks_for_date(folded)
    asks_for_policy_condition = _asks_for_policy_condition(folded)
    explicit_value = any(
        (
            asks_for_percentage,
            asks_for_amount,
            asks_for_count,
            asks_for_duration,
            asks_for_time_range,
            asks_for_timeline,
            asks_for_date,
            "bao nhieu" in folded,
            " may" in folded and not asks_for_organization,
            any(cue in folded for cue in ("grade nao", "so nao", "muc nao")),
            " how many " in padded,
            " how much " in padded,
            " how long " in padded,
            " muc nao" in folded,
            " toi thieu" in folded,
        )
    )

    if asks_for_person:
        answer_type = "PERSON"
    elif asks_for_percentage:
        answer_type = "PERCENTAGE"
    elif _asks_for_year(folded):
        answer_type = "YEAR"
    elif asks_for_date:
        answer_type = "DATE"
    elif asks_for_time_range:
        answer_type = "TIME_RANGE"
    elif asks_for_timeline:
        answer_type = "TIMELINE"
    elif asks_for_clock_time:
        answer_type = "TIME"
    elif asks_for_duration:
        answer_type = "DURATION"
    elif asks_for_amount:
        answer_type = "AMOUNT"
    elif asks_for_count:
        answer_type = "COUNT"
    elif asks_for_organization:
        answer_type = "ORGANIZATION"
    elif is_yes_no:
        answer_type = "YES_NO"
    elif _asks_for_purpose(folded):
        answer_type = "PURPOSE"
    elif _asks_for_definition(folded):
        answer_type = "DEFINITION"
    elif asks_for_policy_condition:
        answer_type = "POLICY_CONDITION"
    elif _asks_for_list(folded):
        answer_type = "LIST"
    elif _asks_for_explanation(folded):
        answer_type = "EXPLANATION"
    elif explicit_value:
        answer_type = "NUMBER"
    else:
        answer_type = "OTHER"

    return QuestionAnalysis(
        answer_type=answer_type,
        is_yes_no=is_yes_no,
        asks_for_time_range=asks_for_time_range,
        asks_for_timeline=asks_for_timeline,
        asks_for_person=asks_for_person,
        asks_for_amount=asks_for_amount,
        asks_for_percentage=asks_for_percentage,
        asks_for_count=asks_for_count,
        asks_for_duration=asks_for_duration,
        asks_for_policy_condition=asks_for_policy_condition,
        asks_for_explicit_value=explicit_value,
    )


def question_terms(question: str, *, min_characters: int = 3) -> tuple[str, ...]:
    terms = []
    for term in _WORD_RE.findall(fold_text(question)):
        cleaned = term.strip("_")
        if not cleaned:
            continue
        if cleaned.isdecimal() or len(cleaned) >= min_characters:
            terms.append(cleaned)
    return tuple(dict.fromkeys(terms))


def fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).casefold()
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return normalized.translate(_VIETNAMESE_BASE_TRANSLATION)


def asks_for_organization_activity(question: str) -> bool:
    """Detect requests for an organization's lines of business or activity."""

    folded = fold_text(question)
    has_organization = any(
        re.search(rf"\b{re.escape(cue)}\b", folded) is not None
        for cue in ("cong ty", "doanh nghiep", "company", "business")
    )
    asks_areas = any(
        re.search(rf"\b{re.escape(cue)}\b", folded) is not None
        for cue in (
            "mang gi",
            "linh vuc",
            "hoat dong",
            "business areas",
            "areas of business",
            "what does the company do",
        )
    )
    return has_organization and asks_areas


def _is_yes_no_question(folded: str) -> bool:
    stripped = folded.strip()
    return (
        stripped.startswith(("co ", "co phai ", "is ", "are ", "do ", "does ", "can "))
        or any(
            cue in stripped
            for cue in (
                "hay xac nhan",
                "vui long xac nhan",
                "please confirm",
                "confirm whether",
                "confirm that",
            )
        )
        or " dung khong" in stripped
        or " phai khong" in stripped
        or stripped.endswith(" khong")
        or stripped.endswith(" khong?")
        or stripped.endswith(" khong.")
    )


def _asks_for_person(folded: str) -> bool:
    stripped = folded.strip()
    padded = f" {stripped} "
    ai_product_context = any(
        re.search(pattern, stripped)
        for pattern in (
            r"\bpublic\s+ai\b",
            r"\bcong\s+cu\s+ai\b",
            r"\bdich\s+vu\s+ai\b",
            r"\bai\s+tao\b",
            r"\bket\s+qua\s+ai\b",
            r"\bchatgpt\b",
        )
    )
    if ai_product_context and not any(cue in stripped for cue in (" la ai", "ai la ", " who ")):
        return False
    # "Who approves/reviews this request?" asks for a workflow actor, which
    # may be a role (for example, the direct manager) rather than a person's
    # name. Treating it as a PERSON lookup biases ranking toward document
    # metadata containing named authors/approvers and incorrectly activates
    # full-name completeness checks.
    asks_for_workflow_actor = any(
        cue in padded
        for cue in (
            " duyet ",
            " phe duyet ",
            " xac nhan ",
            " approve ",
            " approves ",
            " review ",
            " reviews ",
        )
    ) and not any(cue in stripped for cue in (" ten gi", " ten la gi", " name"))
    if asks_for_workflow_actor:
        return False
    return (
        " la ai" in stripped
        or stripped.endswith(" ai")
        or " ai " in padded
        or " who " in padded
        or stripped.startswith("who ")
        or " ten gi" in stripped
        or " ten la gi" in stripped
    )


def _asks_for_organization(folded: str) -> bool:
    """Recognize a requested unit even when casual wording contains `mấy`."""

    return any(
        re.search(pattern, folded) is not None
        for pattern in (
            r"\b(?:bo phan|phong ban|don vi|nhom) nao\b",
            r"\b(?:which|what) (?:department|team|unit)\b",
        )
    )


def _asks_for_year(folded: str) -> bool:
    padded = f" {folded} "
    return (
        " nam nao" in folded
        or " nam may" in folded
        or " thanh lap " in padded
        or " founded " in padded
        or " founding year " in padded
        or " established " in padded
    )


def _asks_for_percentage_like(folded: str) -> bool:
    if re.search(r"\bty\s+le\b", folded) or re.search(r"\bpercentage\b", folded):
        return True
    if re.search(r"\b(?:ot\s+bao nhieu|bao nhieu\s+ot)\b", folded):
        return True
    if any(
        cue in f" {folded} "
        for cue in (
            " muc ot ",
            " ty le ot ",
            " muc overtime ",
            " overtime rate ",
            " ot rate ",
        )
    ):
        return True
    if "bao nhieu" not in folded and "how much" not in folded:
        return False
    if any(cue in folded for cue in ("cong them", "tra them", "paid extra")) and any(
        cue in folded for cue in ("lam them", "overtime", "ban dem", "night work")
    ):
        return True
    if "toi thieu" not in folded and "it nhat" not in folded and "at least" not in folded:
        return False
    return any(
        cue in folded
        for cue in (
            "ot",
            "lam them",
            "overtime",
            "ban dem",
            "night work",
            "tra",
            "paid",
            "pay",
        )
    )


def _asks_for_date(folded: str) -> bool:
    return (
        " ngay nao" in folded
        or " ngay may" in folded
        or " vao ngay nao" in folded
        or " when " in f" {folded} "
        or folded.startswith("when ")
    )


def _asks_for_time(folded: str) -> bool:
    return " may gio" in folded or " gio nao" in folded or " what time" in folded


def _asks_for_time_range(folded: str) -> bool:
    padded = f" {folded} "
    return (
        re.search(r"\btu\s+may\s+gio\s+(?:toi|den)\s+may\s+gio\b", folded) is not None
        or " khoang nao" in padded
        or " khung gio" in padded
        or " khung bat dau" in padded
        or " khung ket thuc" in padded
        or " gio cot loi" in padded
        or " core hour" in padded
        or " start window" in padded
        or " end window" in padded
        or " time range" in padded
        or " time interval" in padded
        or " between what time" in padded
    )


def _asks_for_amount(folded: str) -> bool:
    asks_quantity = " bao nhieu" in folded or " how much" in folded
    asks_paid_leave_duration = (
        asks_quantity
        and any(unit in folded for unit in (" ngay", " gio", " tuan", " thang", " nam"))
        and (" paid leave" in folded or (" nghi" in folded and " huong luong" in folded))
    )
    if asks_paid_leave_duration:
        return False
    if asks_quantity and "nam vien" in folded:
        return True
    if not asks_quantity:
        padded = f" {folded} "
        asks_oncall_policy_clause = "call" in folded or " truc" in padded
        if not asks_oncall_policy_clause and any(
            cue in padded
            for cue in (
                " allowance ",
                " phu cap ",
                " stipend ",
                " tro cap ",
            )
        ):
            return True
        if " han muc " in padded and any(
            cue in padded
            for cue in (
                " bao hiem ",
                " dental ",
                " inpatient ",
                " nha khoa ",
                " ngoai tru ",
                " noi tru ",
                " outpatient ",
            )
        ):
            return True
    money_terms = (
        "dong",
        "trieu",
        "tien",
        "luong",
        "phu cap",
        "tro cap",
        "ho tro",
        "chi tra",
        "han muc",
        "noi tru",
        "ngoai tru",
        "allowance",
        "salary",
        "support",
        "amount",
    )
    return asks_quantity and any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded) is not None for term in money_terms
    )


def _asks_for_salary_band_value(folded: str) -> bool:
    """Recognize a compensation-band request without requiring ``bao nhieu``.

    A band/range is itself a value request when it is explicitly scoped to
    compensation.  Keeping both signals mandatory avoids classifying generic
    role, schedule, leave, or policy-range questions as monetary amounts.
    """

    if "nghi khong luong" in folded or "unpaid leave" in folded:
        return False
    salary_cues = ("luong", "salary", "pay", "compensation", "gross")
    band_cues = ("dai", "khoang", "range", "band", "khung", "min", "max")
    return any(cue in folded for cue in salary_cues) and any(cue in folded for cue in band_cues)


def _asks_for_timeline(folded: str) -> bool:
    """Recognize ordered policy timing, distinct from a monetary amount.

    A compensation term can describe an amount, but a question about a cycle,
    stage, period, or effective date asks for temporal policy evidence. Both a
    temporal form and a process/effective-date anchor are required so ordinary
    salary and payment questions retain their existing classifications.
    """

    temporal_form = any(
        cue in folded
        for cue in (
            "khoang thoi gian",
            "giai doan",
            "chu ky",
            "timeline",
            "thang nao",
            "what period",
            "which months",
            "review cycle",
            "effective date",
            "when is",
        )
    )
    process_anchor = any(
        cue in folded
        for cue in (
            "review",
            "danh gia",
            "calibration",
            "phe duyet ngan sach",
            "budget approval",
            "hieu luc",
            "effective",
        )
    )
    return temporal_form and process_anchor


def _asks_for_count(folded: str) -> bool:
    if re.search(r"bao nhieu\s+(?:\w+\s+){0,4}(?:ngay|gio|tuan|thang|nam|phan tram)", folded):
        return False
    count_terms = (
        " nhan su ",
        " nhan vien ",
        " nguoi lao dong ",
        " employee ",
        " employees ",
        " headcount ",
        " people ",
    )
    return (" bao nhieu" in folded or " how many" in folded) and any(
        term.strip() in folded for term in count_terms
    )


def _asks_for_duration(folded: str) -> bool:
    return (
        re.search(r"\bso\s+(?:ngay|gio|tuan|thang|nam)\b", folded) is not None
        or re.search(r"\bmay\s+(?:ngay|gio|tieng|tuan|thang|nam)\b", folded) is not None
        or re.search(r"\bnumber\s+of\s+(?:days?|hours?|weeks?|months?|years?)\b", folded)
        is not None
        or " bao lau" in folded
        or " trong bao lau" in folded
        or re.search(
            r"bao nhieu\s+(?:\w+\s+){0,4}(?:ngay|gio|tieng|tuan|thang|nam)\b",
            folded,
        )
        is not None
        or re.search(
            r"how many\s+(?:\w+\s+){0,4}(?:days?|hours?|weeks?|months?|years?)\b",
            folded,
        )
        is not None
        or " how long" in folded
        or " within how" in folded
        or " deadline" in folded
    )


def _asks_for_policy_condition(folded: str) -> bool:
    stripped = folded.strip()
    return (
        stripped.startswith(("neu ", "khi ", "trong truong hop "))
        or (
            " khi nao" in folded
            and any(cue in folded for cue in ("duoc huong", "eligib", "tham gia"))
        )
        or " theo chinh sach" in folded
        or " policy " in f" {folded} "
        or " condition " in f" {folded} "
    )


def _asks_for_purpose(folded: str) -> bool:
    return (
        " dung de" in folded
        or " lam gi" in folded
        or " purpose" in folded
        or " used for" in folded
        or " function" in folded
    )


def _asks_for_definition(folded: str) -> bool:
    return " la gi" in folded or folded.startswith("what is ") or folded.startswith("what are ")


def _asks_for_list(folded: str) -> bool:
    return " nhung gi" in folded or " liet ke" in folded or " list " in f" {folded} "


def _asks_for_explanation(folded: str) -> bool:
    return (
        folded.startswith(("tai sao", "vi sao", "why "))
        or " giai thich" in folded
        or " explain " in f" {folded} "
    )
