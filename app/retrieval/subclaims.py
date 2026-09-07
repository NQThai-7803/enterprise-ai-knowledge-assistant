"""Safe decomposition of compound questions for retrieval assistance."""

from __future__ import annotations

import re

_CONJUNCTION_PATTERN = re.compile(r"\s+(?:và|va|and)\s+", re.IGNORECASE)
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


def _compound_clauses(value: str) -> tuple[str, ...]:
    """Split requested facts without splitting a leading source/title qualifier."""
    first_comma = value.find(",")
    boundaries = tuple(
        match
        for match in _CONJUNCTION_PATTERN.finditer(value)
        if first_comma < 0 or match.start() > first_comma
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
