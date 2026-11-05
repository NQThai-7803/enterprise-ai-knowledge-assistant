"""Safe decomposition of compound questions for retrieval assistance."""

from __future__ import annotations

import re

from app.retrieval.question_analysis import fold_text

_CONJUNCTION_PATTERN = re.compile(r"\s+(?:và|va|and)\s+", re.IGNORECASE)
_PAIRED_CONSTRUCTION_PATTERN = re.compile(
    r"\b(?:vừa|vua)\s+(?P<first>.+?)\s+(?:vừa|vua)\s+(?P<second>.+)$",
    re.IGNORECASE,
)
_COORDINATED_OBJECT_PATTERN = re.compile(
    r"^(?P<prefix>.+?\b(?:xử\s+lý|xu\s+ly|handle|process)\s+)"
    r"(?P<first>[^,;?]+?)\s+(?:với|voi|and)\s+"
    r"(?P<second>[^,;?]+?)\s+(?:thế\s+nào|the\s+nao|ra\s+sao|how)\??$",
    re.IGNORECASE,
)
_SUBJECT_BOUNDARY_PATTERN = re.compile(
    r"\b(?:thì|thi|có|co|cần|can|phải|phai|được|duoc|thuộc|thuoc|là|la|về|ve|regarding|has|have|is|are)\b",
    re.IGNORECASE,
)


def information_need_queries(question: str) -> tuple[str, ...]:
    """Return retrieval-only queries for independently answerable clauses.

    This intentionally uses only the user's words.  It is not an answer
    generator and does not add facts or synonyms.  The original question is
    always retained by the caller for prompting and validation.
    """

    value = " ".join(question.split()).strip()
    if not value:
        return ()
    paired_queries = _paired_information_need_queries(value)
    if paired_queries:
        return paired_queries
    coordinated_queries = _coordinated_object_queries(value)
    if coordinated_queries:
        return coordinated_queries
    if _is_single_value_frequency_request(value):
        return ()
    clauses = _compound_clauses(value)
    if len(clauses) < 2 or any(len(clause.split()) < 2 for clause in clauses):
        return ()

    first_clause = clauses[0]
    boundary = _SUBJECT_BOUNDARY_PATTERN.search(first_clause)
    qualifier = first_clause.split(",", 1)[0].strip(" ,;:") if "," in first_clause else ""
    if qualifier and (boundary is None or boundary.start() > first_clause.index(",")):
        subject = qualifier
    else:
        subject = first_clause[: boundary.start()].strip(" ,;:") if boundary else ""
    subject = re.sub(r"\s+(?:và|va|and)$", "", subject, flags=re.IGNORECASE)
    condition_match = re.search(
        r"\b((?:vào|vao)\s+[^,;?]{1,80}?)\s+(?:thì|thi)\b",
        first_clause,
        re.IGNORECASE,
    )
    shared_condition = condition_match.group(1).strip() if condition_match else ""
    queries: list[str] = []
    for index, clause in enumerate(clauses[:3]):
        query = clause
        clause_boundary = _SUBJECT_BOUNDARY_PATTERN.search(clause)
        clause_prefix = clause[: clause_boundary.start()].strip(" ,;:") if clause_boundary else ""
        has_independent_subject = (
            index > 0
            and not qualifier
            and len(clause_prefix.split()) >= 2
            and not clause_prefix.casefold().startswith(
                ("khi nao", "muc ot", "muc overtime", "when ")
            )
        )
        if subject and not has_independent_subject and subject.casefold() not in clause.casefold():
            query = f"{subject} {clause}"
        if index > 0 and shared_condition and shared_condition.casefold() not in query.casefold():
            query = f"{query} {shared_condition}"
        if query.casefold() != value.casefold():
            queries.append(query)
    return tuple(dict.fromkeys(queries))


def _is_single_value_frequency_request(value: str) -> bool:
    """Keep an amount and its recurrence period as one structured fact."""

    folded = fold_text(value)
    asks_for_value = bool(re.search(r"\b(?:bao\s+nhieu|how\s+much)\b", folded))
    asks_for_frequency = bool(
        re.search(
            r"\b(?:bao\s+lau[^?]{0,40}\bmot\s+lan|how\s+often|frequency|"
            r"every\s+how\s+long)\b",
            folded,
        )
    )
    has_conjunction = bool(re.search(r"\b(?:va|and)\b", folded))
    return asks_for_value and asks_for_frequency and has_conjunction


def _compound_clauses(value: str) -> tuple[str, ...]:
    """Split requested facts without splitting a leading source/title qualifier."""
    first_comma = value.find(",")
    then_match = re.search(r"\b(?:thì|thi|then)\b", value, re.IGNORECASE)
    boundaries = tuple(
        match
        for match in _CONJUNCTION_PATTERN.finditer(value)
        if (first_comma < 0 or match.start() > first_comma)
        and not _is_predicate_conjunction_before_then(value, match, then_match)
    )
    if not boundaries:
        return (value.strip(" ,;:?!"),)

    clauses: list[str] = []
    start = 0
    for boundary in boundaries:
        clause = value[start : boundary.start()].strip(" ,;:?!")
        if clause:
            clauses.append(clause)
        start = boundary.end()
    final_clause = value[start:].strip(" ,;:?!")
    if final_clause:
        clauses.append(final_clause)
    return tuple(clauses)


def _paired_information_need_queries(value: str) -> tuple[str, ...]:
    match = _PAIRED_CONSTRUCTION_PATTERN.search(value.strip(" ,;:?!"))
    if match is None:
        return ()
    prefix = value[: match.start()].strip(" ,;:")
    prefix = re.sub(r"(?:,\s*)?(?:vậy|vay|then)$", "", prefix, flags=re.IGNORECASE).strip(" ,;:")
    if len(prefix.split()) < 2:
        return ()
    queries = tuple(
        f"{prefix} {part.strip(' ,;:?!')}"
        for part in (match.group("first"), match.group("second"))
        if len(part.split()) >= 2
    )
    return queries if len(queries) == 2 else ()


def _coordinated_object_queries(value: str) -> tuple[str, ...]:
    match = _COORDINATED_OBJECT_PATTERN.match(value.strip())
    if match is None:
        return ()
    prefix = match.group("prefix").strip()
    condition = re.split(r"\b(?:thì|thi|then)\b", prefix, maxsplit=1, flags=re.IGNORECASE)[0].strip(
        " ,;:"
    )
    if len(condition.split()) >= 2:
        prefix = condition
    queries = tuple(
        f"{prefix} {part.strip(' ,;:?!')}"
        for part in (match.group("first"), match.group("second"))
        if len(part.split()) >= 2
    )
    return queries if len(queries) == 2 else ()


def _is_predicate_conjunction_before_then(
    value: str,
    conjunction: re.Match[str],
    then_match: re.Match[str] | None,
) -> bool:
    if then_match is None or conjunction.start() > then_match.start():
        return False
    following = value[conjunction.end() :]
    return (
        re.match(
            r"(?:phải|phai|cần|can|được|duoc|không|khong|must|need|needs|has\s+to)\b",
            following,
            re.IGNORECASE,
        )
        is not None
    )
