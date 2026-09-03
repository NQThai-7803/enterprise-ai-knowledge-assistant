from __future__ import annotations

import re

_WHITESPACE_PATTERN = re.compile(r"\s+")


def build_excerpt(*, source_text: str, max_characters: int) -> str:
    if max_characters <= 0:
        msg = "max_characters must be greater than zero."
        raise ValueError(msg)
    normalized = _WHITESPACE_PATTERN.sub(" ", source_text).strip()
    if not normalized:
        msg = "source text must not be blank."
        raise ValueError(msg)
    if len(normalized) <= max_characters:
        return normalized
    if max_characters == 1:
        return "…"

    limit = max_characters - 1
    candidate = normalized[:limit].rstrip()
    boundary = candidate.rfind(" ")
    if boundary > 0:
        candidate = candidate[:boundary].rstrip()
    if not candidate:
        candidate = normalized[:limit].rstrip()
    return f"{candidate}…"


def build_evidence_centered_excerpt(
    *,
    source_text: str,
    evidence_text: str | None,
    max_characters: int,
) -> str:
    """Build an excerpt that retains the exact evidence when it is known."""

    normalized = _WHITESPACE_PATTERN.sub(" ", source_text).strip()
    evidence = _WHITESPACE_PATTERN.sub(" ", evidence_text or "").strip()
    if not evidence or len(normalized) <= max_characters:
        return build_excerpt(source_text=source_text, max_characters=max_characters)

    evidence_index = normalized.find(evidence)
    if evidence_index < 0:
        return build_excerpt(source_text=source_text, max_characters=max_characters)

    leading_ellipsis = evidence_index > 0
    trailing_ellipsis = evidence_index + len(evidence) < len(normalized)
    ellipsis_count = int(leading_ellipsis) + int(trailing_ellipsis)
    content_budget = max_characters - ellipsis_count
    if content_budget <= 0 or len(evidence) > content_budget:
        return build_excerpt(source_text=evidence, max_characters=max_characters)

    surrounding_budget = content_budget - len(evidence)
    start = max(0, evidence_index - surrounding_budget // 2)
    end = min(len(normalized), evidence_index + len(evidence) + surrounding_budget // 2)
    if end - start < content_budget:
        if start == 0:
            end = min(len(normalized), content_budget)
        elif end == len(normalized):
            start = max(0, end - content_budget)

    excerpt = normalized[start:end].strip()
    if start > 0:
        boundary = excerpt.find(" ")
        if boundary >= 0:
            excerpt = excerpt[boundary + 1 :].lstrip()
        excerpt = f"…{excerpt}"
    if end < len(normalized):
        boundary = excerpt.rfind(" ")
        if boundary > 0 and len(excerpt) >= max_characters:
            excerpt = excerpt[:boundary].rstrip()
        excerpt = f"{excerpt}…"
    return excerpt[:max_characters]
