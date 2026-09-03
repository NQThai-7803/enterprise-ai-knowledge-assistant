from __future__ import annotations

import re
from dataclasses import dataclass

from app.retrieval.question_analysis import QuestionAnalysis, fold_text, question_terms

_NUMBER_UNIT_RE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:\([^)]{1,80}\)\s*)?([^\W\d_/%]+|%|vnd|\u0111|\u20ab)",
    re.UNICODE,
)
_PERCENT_RE = re.compile(r"(?<!\d)\d+(?:[.,]\d+)?\s*%")
_COUNT_VALUE_RE = re.compile(
    r"(?<!\d)\d+(?:[.,]\d+)?\s*(?:nguoi|nhan\s+su|nhan\s+vien|employees?|people)\b"
)
_MONEY_VALUE_RE = re.compile(
    r"(?<!\d)\d+(?:[.,]\d+)?(?:\s*(?:-|\u2013|\u2014)\s*\d+(?:[.,]\d+)?)?\s*"
    r"(?:trieu|dong|vnd|d|\u20ab)\b"
)
_TIME_RE = re.compile(
    r"(?<!\d)(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)?\s*(?:-|\u2013|\u2014|den|to)\s*"
    r"(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)?",
    re.IGNORECASE,
)
_CLOCK_RE = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)(?!\d)")
_KEY_VALUE_RE = re.compile(r"^\s*([^:|]{2,80})\s*[:|]\s*(.{1,240})\s*$")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*Ã¢â‚¬Â¢]|\d+[.)])\s+")
_ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9&/+.-]{1,}\b")
_TITLE_TOKEN_RE = re.compile(r"\b[^\W\d_][\w'-]*\b", re.UNICODE)

_VALUELESS_TABLE_CUES = (
    "noi dung",
    "hang muc",
    "muc",
    "loai",
    "doi tuong",
    "dieu kien",
    "quy dinh",
    "chinh sach",
    "record",
    "field",
    "value",
)

_VALUE_CUES = (
    "%",
    "gio",
    "ngay",
    "tuan",
    "thang",
    "nam",
    "dong",
    "trieu",
    "minutes",
    "hours",
    "days",
    "weeks",
    "months",
    "years",
)

_REPLACEMENT_RELATION_TERMS = frozenset(
    {
        "thay",
        "the",
        "replace",
        "replaces",
        "replacing",
        "substitute",
        "substitutes",
    }
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
_RELATION_ENTITY_STOP_TERMS = frozenset(
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


@dataclass(frozen=True, slots=True)
class StructuredRecord:
    section: str
    row_text: str
    field_pairs: tuple[tuple[str, str], ...] = ()
    row_label: str = ""
    row_value: str = ""
    row_condition: str = ""
    neighboring_header: str = ""


def structured_retrieval_text(text: str) -> str:
    records = build_structured_records(text)
    if not records:
        return text
    rendered = []
    for record in records[:24]:
        section = f"Section: {record.section}\n" if record.section else ""
        if record.field_pairs:
            fields = "\n".join(f"{key}: {value}" for key, value in record.field_pairs)
            rendered.append(f"{section}Record:\n{fields}")
            continue
        rendered.append(f"{section}Record: {record.row_text}")
    return f"{text}\n\nStructured retrieval records:\n" + "\n".join(rendered)


def build_structured_records(text: str) -> tuple[StructuredRecord, ...]:
    lines = _nonempty_lines(text)
    if not lines:
        return ()

    records: list[StructuredRecord] = []
    current_section = ""
    for index, line in enumerate(lines):
        folded_line = fold_text(line)
        key_value = _KEY_VALUE_RE.match(line)
        if key_value is not None:
            if "|" in line:
                label, value, condition = _record_parts(line)
                records.append(
                    StructuredRecord(
                        section=current_section,
                        row_text=line,
                        row_label=label,
                        row_value=value,
                        row_condition=condition,
                        neighboring_header=current_section,
                    )
                )
                continue
            label = key_value.group(1).strip()
            value = key_value.group(2).strip()
            records.append(
                StructuredRecord(
                    section=current_section,
                    row_text=line,
                    field_pairs=((label, value),),
                    row_label=label,
                    row_value=value,
                )
            )
            continue

        if _looks_like_section_header(line):
            current_section = line.strip()
            continue

        previous_line = lines[index - 1] if index > 0 else ""
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        row_lines = [line]
        if "|" not in line and _line_has_value(line) and _line_looks_like_label(previous_line):
            row_lines.insert(0, previous_line)
        if (
            "|" not in line
            and not _line_has_value(line)
            and _line_looks_like_label(line)
            and _line_has_value(next_line)
        ):
            row_lines.append(next_line)
        if len(row_lines) > 1 or _line_has_value(line) or _ACRONYM_RE.search(line):
            row_text = " | ".join(part.strip() for part in row_lines if part.strip())
            label, value, condition = _record_parts(row_text)
            records.append(
                StructuredRecord(
                    section=current_section,
                    row_text=row_text,
                    row_label=label,
                    row_value=value,
                    row_condition=condition,
                    neighboring_header=current_section,
                )
            )
            continue

        if any(cue in folded_line for cue in _VALUELESS_TABLE_CUES):
            current_section = line.strip()

    return tuple(records)


def _record_parts(row_text: str) -> tuple[str, str, str]:
    """Extract row label/value/condition without treating nearby numbers as values."""
    parts = [part.strip() for part in row_text.split("|") if part.strip()]
    if len(parts) < 2:
        return row_text.strip(), "", ""
    label = parts[0]
    value = parts[1]
    condition = " | ".join(parts[2:])
    return label, value, condition


def selected_structural_line_indexes(
    text: str,
    question: str,
    analysis: QuestionAnalysis,
    *,
    max_indexes: int = 10,
) -> tuple[int, ...]:
    lines = _nonempty_lines(text)
    if not lines:
        return ()
    folded_lines = tuple(fold_text(line) for line in lines)
    security_control_question = _asks_for_security_controls(question)
    terms = tuple(
        term
        for term in question_terms(question)
        if term
        not in {
            "bao",
            "nhieu",
            "duoc",
            "cua",
            "theo",
            "chinh",
            "sach",
            "what",
            "which",
            "when",
            "how",
            "many",
            "much",
        }
    )
    scored: list[tuple[int, int]] = []
    for index, folded_line in enumerate(folded_lines):
        score = _line_question_score(
            folded_line,
            terms=terms,
            analysis=analysis,
            security_control_question=security_control_question,
            previous_line=folded_lines[index - 1] if index > 0 else "",
            next_line=folded_lines[index + 1] if index + 1 < len(lines) else "",
        )
        if score > 0:
            scored.append((index, score))
    relation_indexes = _replacement_relation_line_indexes(
        folded_lines=folded_lines,
        terms=terms,
    )

    if not scored and not relation_indexes:
        return ()

    selected_indexes: list[int] = []
    for index in relation_indexes:
        if index not in selected_indexes:
            selected_indexes.append(index)

    if scored:
        best_score = max(score for _, score in scored)
        selected = sorted(
            ((index, score) for index, score in scored if score >= max(1, best_score - 4)),
            key=lambda row: (-row[1], row[0]),
        )
        for index, _ in selected:
            if index not in selected_indexes:
                selected_indexes.append(index)

    # Preserve every highest-scoring answer line before adding surrounding
    # headers/conditions. Otherwise one row's neighbors can consume the whole
    # excerpt and crowd out another directly relevant row.
    expanded: list[int] = []
    for index in selected_indexes[:max_indexes]:
        if index not in expanded:
            expanded.append(index)
        table_header = _nearest_table_header_index(lines, index)
        if table_header is not None and table_header not in expanded:
            expanded.append(table_header)
    for index in selected_indexes:
        for neighbor in _structural_neighbors(index, lines, analysis):
            if 0 <= neighbor < len(lines) and neighbor not in expanded:
                expanded.append(neighbor)
    if _asks_regular_night_work(analysis=analysis, terms=terms):
        expanded = [
            index
            for index in expanded
            if not _is_mismatched_regular_night_percentage(index=index, folded_lines=folded_lines)
        ]
    return tuple(expanded[:max_indexes])


def has_value_expression(text: str) -> bool:
    folded = fold_text(text)
    return (
        _NUMBER_UNIT_RE.search(folded) is not None
        or _PERCENT_RE.search(folded) is not None
        or _TIME_RE.search(folded) is not None
        or _CLOCK_RE.search(folded) is not None
    )


def has_explicit_not_specified(text: str) -> bool:
    folded = fold_text(text)
    return any(
        cue in folded
        for cue in (
            "khong quy dinh",
            "khong xac dinh",
            "khong neu",
            "khong co ty le co dinh",
            "khong co dinh ty le",
            "khong co dinh",
            "khong an dinh",
            "khong duoc neu ro",
            "does not specify",
            "does not define",
            "not specify",
            "not fixed",
            "no fixed",
        )
    )


def value_units_for_analysis(analysis: QuestionAnalysis) -> tuple[str, ...]:
    if analysis.asks_for_percentage:
        return ("%", "phan tram")
    if analysis.asks_for_time_range or analysis.answer_type == "TIME":
        return ("gio", "h", "hour", "hours")
    if analysis.asks_for_duration:
        return ("gio", "ngay", "tuan", "thang", "nam", "hour", "day", "week", "month", "year")
    if analysis.asks_for_amount:
        return ("dong", "trieu", "vnd", "Ã¢â€šÂ«")
    if analysis.asks_for_count:
        return ("nhan su", "nhan vien", "nguoi", "employee", "people")
    return _VALUE_CUES


def _line_question_score(
    folded_line: str,
    *,
    terms: tuple[str, ...],
    analysis: QuestionAnalysis,
    security_control_question: bool,
    previous_line: str,
    next_line: str,
) -> int:
    window = f"{previous_line} {folded_line} {next_line}"
    score = sum(2 for term in terms if term in folded_line)
    score += sum(1 for term in terms if term in window and term not in folded_line)
    score += sum(
        4 for left, right in zip(terms, terms[1:], strict=False) if f"{left} {right}" in folded_line
    )
    term_set = set(terms)
    if security_control_question:
        matched_controls = {
            cue
            for cue in (
                "ket noi an toan",
                "xac thuc nhieu lop",
                "thiet bi duoc phe duyet",
                "thiet bi duoc quan ly",
                "khong de nguoi khong co tham quyen",
                "multi factor",
                "managed device",
                "safe connection",
                "unauthorized",
                "vpn",
                "mfa",
            )
            if cue in window
        }
        if matched_controls:
            score += 40 + len(matched_controls) * 12
    score += sum(8 for term in term_set if len(term) >= 7 and term in folded_line)
    if {"thoi", "gian"}.issubset(term_set) and "thoi gian" in folded_line:
        score += 12
        if "ghi nhan" in folded_line:
            score += 8
    if analysis.asks_for_percentage and (
        {"chu", "nhat"}.issubset(term_set) or "sunday" in term_set or "weekend" in term_set
    ):
        if "ngay nghi hang tuan" in folded_line:
            score += 20
        if any(cue in folded_line for cue in ("ngay le", "tet", "holiday")):
            score -= 12
    asks_regular_night_work = _asks_regular_night_work(analysis=analysis, terms=terms)
    if asks_regular_night_work:
        if "lam viec ban dem" in window or "night work" in window:
            score += 24
        if "lam them vao ban dem" in window or "night overtime" in window:
            score -= 48
    if analysis.asks_for_person and any(term in folded_line for term in terms):
        score += 6
    if analysis.asks_for_explicit_value and has_value_expression(folded_line):
        score += 6
    if analysis.asks_for_count and _COUNT_VALUE_RE.search(folded_line):
        score += 10
    if analysis.asks_for_amount and _MONEY_VALUE_RE.search(folded_line):
        score += 10
    if analysis.answer_type == "DATE" and re.search(r"\bngay\s+\d{1,2}\b", folded_line):
        score += 8
    if analysis.answer_type == "YEAR" and re.search(r"\b(?:19|20)\d{2}\b", folded_line):
        score += 8
    if analysis.asks_for_percentage and _PERCENT_RE.search(folded_line):
        score += 8
    if (analysis.asks_for_time_range or analysis.answer_type == "TIME") and (
        _TIME_RE.search(folded_line) or _CLOCK_RE.search(folded_line)
    ):
        score += 8
    if analysis.answer_type == "YES_NO" and _has_policy_polarity(folded_line):
        score += 5
    if has_explicit_not_specified(folded_line):
        score += 8
    return score


def _asks_for_security_controls(question: str) -> bool:
    folded = fold_text(question)
    return (
        "bao mat" in folded
        and any(
            cue in folded for cue in ("yeu cau", "bao dam", "can tuan thu", "tuan thu", "controls")
        )
    ) or (
        "an toan" in folded
        and any(cue in folded for cue in ("bao dam", "dam bao", "gi", "controls"))
    )


def _asks_regular_night_work(
    *,
    analysis: QuestionAnalysis,
    terms: tuple[str, ...],
) -> bool:
    joined_terms = " ".join(terms)
    return (
        analysis.asks_for_percentage
        and ("lam viec ban dem" in joined_terms or "night work" in joined_terms)
        and "lam them" not in joined_terms
        and "overtime" not in set(terms)
    )


def _is_mismatched_regular_night_percentage(
    *,
    index: int,
    folded_lines: tuple[str, ...],
) -> bool:
    line = folded_lines[index]
    if _PERCENT_RE.search(line) is None:
        return False
    next_line = folded_lines[index + 1] if index + 1 < len(folded_lines) else ""
    if "lam viec ban dem" in line or "lam viec ban dem" in next_line:
        return False
    return any(
        cue in f"{line} {next_line}"
        for cue in (
            "lam them",
            "ngay nghi hang tuan",
            "ngay le",
            "night overtime",
            "weekly rest",
            "holiday",
        )
    )


def _replacement_relation_line_indexes(
    *,
    folded_lines: tuple[str, ...],
    terms: tuple[str, ...],
) -> tuple[int, ...]:
    if not _is_replacement_relation_question(terms):
        return ()

    entity_terms = tuple(
        term for term in terms if term not in _RELATION_ENTITY_STOP_TERMS and len(term) >= 3
    )
    if len(entity_terms) < 2:
        return ()

    rows: list[tuple[int, str, frozenset[str]]] = []
    for index, folded_line in enumerate(folded_lines):
        matched_entities = frozenset(
            term for term in entity_terms if _contains_folded_token(folded_line, term)
        )
        if not matched_entities:
            continue
        if any(cue in folded_line for cue in _PRIMARY_RELATION_CUES):
            rows.append((index, "primary", matched_entities))
        if any(cue in folded_line for cue in _SUPPLEMENTAL_RELATION_CUES):
            rows.append((index, "supplemental", matched_entities))

    primary_entities = set().union(*(entities for _, kind, entities in rows if kind == "primary"))
    supplemental_entities = set().union(
        *(entities for _, kind, entities in rows if kind == "supplemental")
    )
    if not primary_entities or not supplemental_entities:
        return ()
    if len(primary_entities.union(supplemental_entities)) < 2:
        return ()

    indexes = sorted({index for index, _, _ in rows})
    return tuple(indexes)


def _is_replacement_relation_question(terms: tuple[str, ...]) -> bool:
    term_set = frozenset(terms)
    return {"thay", "the"} <= term_set or bool(
        term_set.intersection(_REPLACEMENT_RELATION_TERMS - {"thay", "the"})
    )


def _contains_folded_token(text: str, token: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text) is not None


def _structural_neighbors(
    index: int,
    lines: tuple[str, ...],
    analysis: QuestionAnalysis,
) -> tuple[int, ...]:
    offsets = (-1, 0, 1)
    if analysis.asks_for_time_range or analysis.answer_type in {"YES_NO", "POLICY_CONDITION"}:
        offsets = (-2, -1, 0, 1, 2)
    if analysis.answer_type == "LIST":
        offsets = (-1, 0, 1, 2, 3)
    neighbors: list[int] = []
    for offset in offsets:
        candidate = index + offset
        if 0 <= candidate < len(lines):
            neighbors.append(candidate)
    header = _nearest_header_index(lines, index)
    if header is not None and header not in neighbors:
        neighbors.insert(0, header)
    return tuple(neighbors)


def _nearest_header_index(lines: tuple[str, ...], index: int) -> int | None:
    for candidate in range(index - 1, max(-1, index - 5), -1):
        if _looks_like_section_header(lines[candidate]):
            return candidate
    return None


def _nearest_table_header_index(lines: tuple[str, ...], index: int) -> int | None:
    cues = (
        "quyen loi",
        "tu ngay",
        "sau thu viec",
        "dieu kien",
        "han muc",
        "tinh huong",
        "muc toi thieu",
        "category",
        "condition",
        "eligibility",
        "from first day",
        "after probation",
    )
    for candidate in range(index - 1, max(-1, index - 11), -1):
        folded = fold_text(lines[candidate])
        if sum(cue in folded for cue in cues) >= 2:
            return candidate
    return None


def _nonempty_lines(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _line_has_value(line: str) -> bool:
    return has_value_expression(line) or bool(re.search(r"\b(?:19|20)\d{2}\b", fold_text(line)))


def _line_looks_like_label(line: str) -> bool:
    if not line.strip():
        return False
    folded = fold_text(_LIST_MARKER_RE.sub("", line).strip())
    if _line_has_value(folded):
        return False
    return len(folded) <= 90


def _looks_like_section_header(line: str) -> bool:
    stripped = _LIST_MARKER_RE.sub("", line).strip()
    if not stripped or len(stripped) > 90:
        return False
    if _line_has_value(stripped) or _KEY_VALUE_RE.match(stripped):
        return False
    tokens = _TITLE_TOKEN_RE.findall(stripped)
    return 1 <= len(tokens) <= 10


def _has_policy_polarity(folded_line: str) -> bool:
    return any(
        cue in folded_line
        for cue in (
            "phai",
            "bat buoc",
            "khong duoc",
            "khong tu dong",
            "duoc phep",
            "required",
            "must",
            "must not",
            "allowed",
            "not allowed",
            "automatically",
        )
    )
