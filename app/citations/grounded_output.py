from __future__ import annotations

import json
import re
from collections.abc import Collection
from dataclasses import dataclass

_SOURCE_IDENTIFIER_RE = re.compile(r"SOURCE_[1-9][0-9]*\Z")
_BRACKETED_SOURCE_IDENTIFIER_RE = re.compile(r"\[SOURCE_[1-9][0-9]*\]\Z")


@dataclass(frozen=True, slots=True)
class GroundedLLMOutput:
    answer: str
    citations: tuple[str, ...]


def parse_grounded_llm_output(
    content: str,
    *,
    allowed_identifiers: Collection[str] | None = None,
) -> GroundedLLMOutput:
    raw = _strip_single_json_fence(content.strip())
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("LLM output is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("LLM output must be a JSON object.")

    answer = payload.get("answer")
    citations = payload.get("citations")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("LLM answer must not be empty.")
    normalized_answer = answer.strip()
    if _answer_contains_citation_marker(normalized_answer):
        raise ValueError("LLM answer must not contain citation markers.")
    if _is_citation_only_answer(normalized_answer):
        raise ValueError("LLM answer must contain non-citation text.")
    if not any(character.isalpha() for character in normalized_answer):
        raise ValueError("LLM answer must contain natural-language text.")

    if not isinstance(citations, list) or not citations:
        raise ValueError("LLM citations must not be empty.")

    allowed = set(allowed_identifiers) if allowed_identifiers is not None else None
    normalized_citations: list[str] = []
    for citation in citations:
        if not isinstance(citation, str) or not citation.strip():
            raise ValueError("Invalid citation identifier.")
        identifier = citation.strip()
        if _BRACKETED_SOURCE_IDENTIFIER_RE.fullmatch(identifier) is not None:
            raise ValueError("Citation identifiers must not be bracketed.")
        if _SOURCE_IDENTIFIER_RE.fullmatch(identifier) is None:
            raise ValueError("Invalid citation identifier.")
        if allowed is not None and identifier not in allowed:
            raise ValueError("Citation identifier is not in the source registry.")
        if identifier not in normalized_citations:
            normalized_citations.append(identifier)

    return GroundedLLMOutput(answer=normalized_answer, citations=tuple(normalized_citations))


def _strip_single_json_fence(raw: str) -> str:
    lines = raw.splitlines()
    if len(lines) < 3:
        return raw
    if lines[0].strip().lower() not in {"```json", "```"}:
        return raw
    if lines[-1].strip() != "```":
        return raw
    return "\n".join(lines[1:-1]).strip()


def _answer_contains_citation_marker(answer: str) -> bool:
    return (
        re.search(r"\[?SOURCE_[1-9][0-9]*\]?", answer) is not None
        or re.search(r"\[[1-9][0-9]*\]", answer) is not None
    )


def _is_citation_only_answer(answer: str) -> bool:
    without_source_identifiers = re.sub(r"\[?SOURCE_[1-9][0-9]*\]?", "", answer)
    without_public_markers = re.sub(r"\[[1-9][0-9]*\]", "", without_source_identifiers)
    return not re.search(r"[^\s,.;:()\[\]]", without_public_markers)
