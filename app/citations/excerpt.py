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
