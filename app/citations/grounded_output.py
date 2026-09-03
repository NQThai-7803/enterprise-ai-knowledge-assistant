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
    polarity: str | None = None


@dataclass(frozen=True, slots=True)
class StructuredGroundedClaim:
    claim_id: str
    answer: str
    citations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StructuredGroundedLLMOutput:
    claims: tuple[StructuredGroundedClaim, ...]


def parse_structured_grounded_llm_output(
    content: str,
    *,
    expected_claim_ids: Collection[str],
    allowed_identifiers: Collection[str] | None = None,
) -> StructuredGroundedLLMOutput:
    output = parse_partial_structured_grounded_llm_output(
        content,
        expected_claim_ids=expected_claim_ids,
        allowed_identifiers=allowed_identifiers,
    )
    expected = tuple(expected_claim_ids)
    if {claim.claim_id for claim in output.claims} != set(expected) or len(output.claims) != len(
        expected
    ):
        raise ValueError("Structured output must cover every required claim exactly once.")
    return output


def parse_partial_structured_grounded_llm_output(
    content: str,
    *,
    expected_claim_ids: Collection[str],
    allowed_identifiers: Collection[str] | None = None,
) -> StructuredGroundedLLMOutput:
    """Extract only individually valid expected claims from a structured response.

    Partial parsing is used solely by the bounded compound repair path. A partial
    result is never publishable: callers must validate every expected claim and
    obtain complete coverage before composing a public answer.
    """
    raw = _strip_single_json_fence(content.strip())
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("LLM output is not valid JSON.") from exc
    if isinstance(payload, list):
        claim_items = payload
    elif isinstance(payload, dict):
        claim_items = payload.get("claims")
    else:
        claim_items = None
    if not isinstance(claim_items, list):
        raise ValueError("Structured output must contain a claims list.")

    expected_set = set(expected_claim_ids)
    allowed = set(allowed_identifiers) if allowed_identifiers is not None else None
    claims: list[StructuredGroundedClaim] = []
    seen: set[str] = set()
    for item in claim_items:
        if not isinstance(item, dict):
            continue
        claim_id = item.get("claim_id")
        if isinstance(claim_id, int) or (isinstance(claim_id, str) and claim_id.strip().isdigit()):
            claim_id = f"CLAIM_{str(claim_id).strip()}"
        answer = item.get("answer")
        citations = item.get("citations")
        if (
            not isinstance(claim_id, str)
            or claim_id not in expected_set
            or claim_id in seen
            or not isinstance(answer, str)
            or not answer.strip()
            or _answer_contains_citation_marker(answer)
            or not isinstance(citations, list)
            or not citations
        ):
            continue
        normalized_citations: list[str] = []
        for citation in citations:
            if (
                not isinstance(citation, str)
                or _SOURCE_IDENTIFIER_RE.fullmatch(citation.strip()) is None
                or (allowed is not None and citation.strip() not in allowed)
            ):
                normalized_citations = []
                break
            if citation.strip() not in normalized_citations:
                normalized_citations.append(citation.strip())
        if not normalized_citations:
            continue
        claims.append(
            StructuredGroundedClaim(
                claim_id=claim_id,
                answer=answer.strip(),
                citations=tuple(normalized_citations),
            )
        )
        seen.add(claim_id)
    return StructuredGroundedLLMOutput(claims=tuple(claims))


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
    polarity = payload.get("polarity")

    normalized_polarity: str | None = None

    if polarity is not None:
        if not isinstance(polarity, str):
            raise ValueError("LLM polarity must be a string when present.")

        normalized_polarity = polarity.strip().upper()

        if normalized_polarity not in {"YES", "NO"}:
            raise ValueError("LLM polarity must be YES or NO.")
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

    return GroundedLLMOutput(
        answer=normalized_answer,
        citations=tuple(normalized_citations),
        polarity=normalized_polarity,
    )


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
