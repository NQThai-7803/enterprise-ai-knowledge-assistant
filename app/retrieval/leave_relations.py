"""Extract annual-leave allocations and increments as source-bound relations."""

import re
from dataclasses import dataclass

from app.retrieval.question_analysis import fold_text

_LEAVE_CUES = ("phep", "nghi hang nam", "annual leave")
_ANNUAL_SCOPE_CUES = ("nghi hang nam", "phep nam", "annual leave")
_ORDINARY_CATEGORY_CUES = ("dieu kien binh thuong", "normal conditions", "ordinary work")
_OTHER_CATEGORY_CUES = (
    "chua thanh nien",
    "khuyet tat",
    "nang nhoc",
    "doc hai",
    "nguy hiem",
)
_OTHER_LEAVE_VALUE_CUES = ("tang them", "tham nien", "dang ky", "truoc it nhat", "gop")
_DAYS_PATTERN = re.compile(r"(?<!\d)(?P<days>\d{1,2})\s+(?:ngay|days?)\b")
_SENIORITY_PATTERN = re.compile(
    r"\b(?:cu\s+du|du|sau|after|every|for every)\s+"
    r"(?P<years>\d{1,2})\s+(?:nam|years?)\b"
    r"(?P<between>[^.;]{0,180}?)"
    r"(?:duoc\s+)?(?:tang\s+them|them|increases?\s+by|additional)\s+"
    r"(?P<days>\d{1,2})\s+(?:ngay|days?)\b"
)


@dataclass(frozen=True, slots=True)
class AnnualLeaveRelation:
    """One stated leave fact, not a bag of nearby dates and day counts."""

    amount_days: int
    answer_clause: str
    evidence: str
    seniority_years: int | None = None
    seniority_interval_years: int | None = None
    seniority_increment_days: int | None = None


def annual_leave_relation_intent(question: str) -> str:
    folded = fold_text(question)
    if not any(cue in folded for cue in _LEAVE_CUES):
        return ""
    if any(cue in folded for cue in ("binh thuong", "normal", "ordinary")) and any(
        cue in folded for cue in ("bao nhieu", "how many", "may ngay")
    ):
        return "ordinary_allocation"
    if (
        any(cue in folded for cue in ("them", "tang", "additional", "extra", "increase"))
        and re.search(r"(?<!\d)\d{1,2}\s+(?:nam|years?)\b", folded)
        and any(
            cue in folded
            for cue in ("thâm niên", "tham nien", "du", "after", "seniority", "quy tac")
        )
    ):
        return "seniority_increment"
    return ""


def ordinary_annual_leave_allocation(text: str) -> AnnualLeaveRelation | None:
    lines = _source_lines(text)
    folded_lines = tuple(fold_text(line) for line in lines)
    for index, label in enumerate(folded_lines):
        if not any(cue in label for cue in _ORDINARY_CATEGORY_CUES):
            continue
        has_annual_scope = any(
            any(cue in folded_lines[scope] for cue in _ANNUAL_SCOPE_CUES)
            for scope in range(max(0, index - 8), index + 1)
        )
        for value_index in (index, index + 1, index - 1):
            if not 0 <= value_index < len(lines):
                continue
            folded_value = folded_lines[value_index]
            if any(
                cue in folded_value for cue in (*_OTHER_LEAVE_VALUE_CUES, *_OTHER_CATEGORY_CUES)
            ):
                continue
            match = _DAYS_PATTERN.search(folded_value)
            if match is None:
                continue
            if not has_annual_scope and not re.search(
                r"\b(?:ngay(?:\s+lam\s+viec)?|days?)\s*/\s*(?:nam|year)\b",
                folded_value,
            ):
                continue
            clause = (
                lines[index] if value_index == index else f"{lines[index]} {lines[value_index]}"
            )
            return AnnualLeaveRelation(
                amount_days=int(match.group("days")),
                answer_clause=clause,
                evidence=clause,
            )
    return None


def annual_leave_seniority_increment(
    text: str, *, requested_years: int
) -> AnnualLeaveRelation | None:
    lines = _source_lines(text)
    folded_lines = tuple(fold_text(line) for line in lines)
    for index, line in enumerate(lines):
        if re.search(r"\b\d{1,2}\s+(?:nam|years?)\b", folded_lines[index]) is None:
            continue
        clause = line
        match = _SENIORITY_PATTERN.search(fold_lines := fold_text(clause))
        can_wrap = any(
            cue in folded_lines[index] for cue in ("cu du", "tham nien", "nghi hang nam")
        ) and not any(cue in folded_lines[index] for cue in ("khong luong", "om dau", "thai san"))
        if (
            match is None
            and can_wrap
            and index + 1 < len(lines)
            and not line.rstrip().endswith((".", ";"))
        ):
            clause = f"{line} {lines[index + 1]}"
            match = _SENIORITY_PATTERN.search(fold_lines := fold_text(clause))
        if match is None:
            continue
        interval_years = int(match.group("years"))
        if interval_years <= 0 or requested_years < interval_years:
            continue
        recurring_rule = any(cue in fold_lines for cue in ("cu du", "every", "for every"))
        if requested_years != interval_years and (
            not recurring_rule or requested_years % interval_years != 0
        ):
            continue
        if not _has_annual_leave_scope(folded_lines, index):
            continue
        if not any(cue in fold_lines for cue in _ANNUAL_SCOPE_CUES):
            for continuation in lines[index + 1 : index + 4]:
                if any(cue in fold_text(continuation) for cue in _ANNUAL_SCOPE_CUES):
                    clause = f"{clause} {continuation}"
                    break
        heading = next(
            (
                lines[scope_index]
                for scope_index in range(index - 1, max(-1, index - 13), -1)
                if any(cue in folded_lines[scope_index] for cue in _ANNUAL_SCOPE_CUES)
                and len(lines[scope_index]) <= 100
            ),
            "",
        )
        evidence = f"{heading}\n{clause}" if heading else clause
        amount_days = int(match.group("days")) * (requested_years // interval_years)
        derived_clause = (
            clause
            if requested_years == interval_years
            else (
                f"Theo quy tắc cứ đủ {interval_years} năm tăng thêm "
                f"{match.group('days')} ngày, {requested_years} năm "
                f"được tăng thêm {amount_days} ngày nghỉ hằng năm."
            )
        )
        return AnnualLeaveRelation(
            amount_days=amount_days,
            answer_clause=derived_clause,
            evidence=evidence,
            seniority_years=requested_years,
            seniority_interval_years=interval_years,
            seniority_increment_days=int(match.group("days")),
        )
    return None


def requested_seniority_years(question: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{1,2})\s+(?:nam|years?)\b", fold_text(question))
    return int(match.group(1)) if match else None


def _source_lines(text: str) -> tuple[str, ...]:
    return tuple(
        segment.strip(" \t\u2022\uf0b7-")
        for segment in re.split(r"\n+|(?<=[.!?])\s+", text)
        if segment.strip()
    )


def _has_annual_leave_scope(folded_lines: tuple[str, ...], index: int) -> bool:
    return any(
        any(cue in folded_lines[scope_index] for cue in _ANNUAL_SCOPE_CUES)
        for scope_index in range(max(0, index - 12), min(len(folded_lines), index + 4))
    )
