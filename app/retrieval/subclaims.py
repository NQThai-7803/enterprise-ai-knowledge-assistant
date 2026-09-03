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
    clauses = tuple(
        clause.strip(" ,;:?!")
        for clause in _CONJUNCTION_PATTERN.split(value)
        if clause.strip(" ,;:?!")
    )
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
