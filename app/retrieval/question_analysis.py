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
    asks_for_percentage = (
        "phan tram" in folded or "%" in question or _asks_for_percentage_like(folded)
    )
    asks_for_amount = False if asks_for_percentage else _asks_for_amount(folded)
    asks_for_count = _asks_for_count(folded)
    asks_for_duration = _asks_for_duration(folded)
    asks_for_time_range = _asks_for_time_range(folded)
    asks_for_policy_condition = _asks_for_policy_condition(folded)
    explicit_value = any(
        (
            asks_for_percentage,
            asks_for_amount,
            asks_for_count,
            asks_for_duration,
            asks_for_time_range,
            "bao nhieu" in folded,
            " may" in folded,
            " nao" in folded,
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
    elif _asks_for_date(folded):
        answer_type = "DATE"
    elif asks_for_time_range:
        answer_type = "TIME_RANGE"
    elif _asks_for_time(folded):
        answer_type = "TIME"
    elif asks_for_duration:
        answer_type = "DURATION"
    elif asks_for_amount:
        answer_type = "AMOUNT"
    elif asks_for_count:
        answer_type = "COUNT"
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


def _is_yes_no_question(folded: str) -> bool:
    stripped = folded.strip()
    return (
        stripped.startswith(("co ", "co phai ", "is ", "are ", "do ", "does ", "can "))
        or " dung khong" in stripped
        or " phai khong" in stripped
        or stripped.endswith(" khong")
        or stripped.endswith(" khong?")
        or stripped.endswith(" khong.")
    )


def _asks_for_person(folded: str) -> bool:
    stripped = folded.strip()
    padded = f" {stripped} "
    return (
        " la ai" in stripped
        or stripped.endswith(" ai")
        or " ai " in padded
        or " who " in padded
        or stripped.startswith("who ")
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
    if "bao nhieu" not in folded and "how much" not in folded:
        return False
    if "toi thieu" not in folded and "it nhat" not in folded and "at least" not in folded:
        return False
    return any(
        cue in folded
        for cue in (
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
        or " vao ngay nao" in folded
        or " when " in f" {folded} "
        or folded.startswith("when ")
    )


def _asks_for_time(folded: str) -> bool:
    return " may gio" in folded or " gio nao" in folded or " what time" in folded


def _asks_for_time_range(folded: str) -> bool:
    return (
        " khoang nao" in folded
        or " khung gio" in folded
        or "gio cot loi" in folded
        or " core hour" in folded
        or " time range" in folded
        or " time interval" in folded
        or " between what time" in folded
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
    money_terms = (
        " dong ",
        " trieu ",
        " luong ",
        " phu cap ",
        " tro cap ",
        " allowance ",
        " salary ",
        " amount ",
    )
    return asks_quantity and any(term.strip() in folded for term in money_terms)


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
        " bao lau" in folded
        or " trong bao lau" in folded
        or re.search(r"bao nhieu\s+(?:\w+\s+){0,4}(?:ngay|gio|tuan|thang|nam)\b", folded)
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
