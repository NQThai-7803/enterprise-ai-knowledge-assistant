from __future__ import annotations

import re

from app.citations.models import PromptSourceRegistry

_SHORT_NUMERIC_CITATION_RE = re.compile(r"\[([1-9][0-9]*)\]")


def normalize_llm_citation_markers(
    answer: str,
    *,
    source_registry: PromptSourceRegistry,
) -> str:
    """
    Normalize only safe shorthand numeric citations emitted by an LLM.

    Example:
        [1] -> [SOURCE_1]

    A shorthand marker is converted only when the corresponding
    source exists in the current prompt source registry.

    This function never invents a source.
    """

    valid_markers = {source.marker for source in source_registry.sources}

    def replace(match: re.Match[str]) -> str:
        index = match.group(1)
        canonical = f"[SOURCE_{index}]"

        if canonical in valid_markers:
            return canonical

        # Leave invalid shorthand untouched.
        # Citation validation will reject it later.
        return match.group(0)

    return _SHORT_NUMERIC_CITATION_RE.sub(replace, answer)
