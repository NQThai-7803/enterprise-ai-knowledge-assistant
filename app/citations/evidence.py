from __future__ import annotations

import re

from app.citations.parser import SOURCE_MARKER_PATTERN
from app.retrieval.question_analysis import fold_text

_NUMBER_PATTERN = re.compile(
    r"\b\d{1,4}(?::\d{2})?(?:[.,]\d+)?\b",
    re.UNICODE,
)

_TERM_PATTERN = re.compile(r"\w+", re.UNICODE)
_REPLACEMENT_RELATION_CUES = (
    "thay the",
    "replace",
    "replaces",
    "replacing",
    "substitute",
    "substitutes",
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
_RELATION_STOP_TERMS = frozenset(
    {
        "khong",
        "thay",
        "the",
        "replace",
        "replaces",
        "replacing",
        "substitute",
        "substitutes",
        "bat",
        "buoc",
        "mandatory",
        "required",
        "bao",
        "hiem",
        "suc",
        "khoe",
        "health",
        "insurance",
    }
)


def extract_exact_evidence(
    *,
    answer: str,
    marker: str,
    source_text: str,
) -> str | None:
    claim = _claim_for_marker(
        answer=answer,
        marker=marker,
    )

    if not claim:
        return None

    relation_evidence = _replacement_relation_evidence(
        claim=claim,
        source_text=source_text,
    )
    if relation_evidence is not None:
        return relation_evidence

    normalized_source = " ".join(source_text.split()).strip()
    if claim in normalized_source:
        # A deterministic repair may copy a complete source clause verbatim.
        # Preserve that exact clause before fuzzy overlap can favor a nearby
        # sentence that happens to share generic words such as "change" or
        # "policy".
        return claim

    candidates = _source_candidates(source_text)
    if not candidates:
        return None

    best_candidate: str | None = None
    best_score = 0.0

    for candidate in candidates:
        score = _evidence_score(
            claim=claim,
            candidate=candidate,
        )

        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate is None:
        return None

    # Không highlight khi bằng chứng quá yếu.
    if best_score < 4.0:
        return None

    exact_value = _exact_value_evidence(
        claim=claim,
        candidate=best_candidate,
    )

    if exact_value is not None:
        return exact_value

    return best_candidate


def _claim_for_marker(
    *,
    answer: str,
    marker: str,
) -> str:
    answer_markers = {match.group(0) for match in SOURCE_MARKER_PATTERN.finditer(answer)}
    if answer_markers == {marker}:
        claim = answer
    else:
        blocks = re.split(
            r"(?<=[.!?;])\s+|\n+",
            answer,
        )

        marker_blocks = [block for block in blocks if marker in block]

        claim = " ".join(marker_blocks) if marker_blocks else answer

    claim = SOURCE_MARKER_PATTERN.sub("", claim)

    return " ".join(claim.split()).strip()


def _source_candidates(
    source_text: str,
) -> tuple[str, ...]:
    raw_candidates = re.split(
        r"(?<=[.!?;])\s+|\n+",
        source_text,
    )

    atomic_candidates: list[str] = []

    for raw in raw_candidates:
        candidate = " ".join(raw.split()).strip()

        if len(candidate) < 8:
            continue

        if candidate not in atomic_candidates:
            atomic_candidates.append(candidate)

    candidates: list[str] = []
    for index, candidate in enumerate(atomic_candidates):
        _append_unique_candidate(candidates, candidate)
        for window_size in (2, 3):
            window = atomic_candidates[index : index + window_size]
            if len(window) != window_size:
                continue
            combined = " ".join(window).strip()
            if len(combined) <= 700:
                _append_unique_candidate(candidates, combined)

    return tuple(candidates)


def _append_unique_candidate(candidates: list[str], candidate: str) -> None:
    if candidate not in candidates:
        candidates.append(candidate)


def _replacement_relation_evidence(
    *,
    claim: str,
    source_text: str,
) -> str | None:
    folded_claim = fold_text(claim)
    if not any(cue in folded_claim for cue in _REPLACEMENT_RELATION_CUES):
        return None

    entity_terms = tuple(
        dict.fromkeys(
            term
            for term in _TERM_PATTERN.findall(folded_claim)
            if len(term) >= 3 and term not in _RELATION_STOP_TERMS
        )
    )
    if len(entity_terms) < 2:
        return None

    normalized_source = " ".join(source_text.split())
    folded_source = fold_text(normalized_source)
    if not all(_contains_folded_term(folded_source, term) for term in entity_terms[:2]):
        return None
    if not any(cue in folded_source for cue in _PRIMARY_RELATION_CUES):
        return None
    if not any(cue in folded_source for cue in _SUPPLEMENTAL_RELATION_CUES):
        return None

    positions: list[int] = []
    for term in entity_terms[:3]:
        position = folded_source.find(term)
        if position >= 0:
            positions.append(position)
    for cue in (*_PRIMARY_RELATION_CUES, *_SUPPLEMENTAL_RELATION_CUES):
        position = folded_source.find(cue)
        if position >= 0:
            positions.append(position)

    if not positions:
        return None

    start = max(0, min(positions) - 120)
    end = min(len(normalized_source), max(positions) + 360)
    return normalized_source[start:end].strip()


def _contains_folded_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _evidence_score(
    *,
    claim: str,
    candidate: str,
) -> float:
    folded_claim = fold_text(claim)
    folded_candidate = fold_text(candidate)

    claim_terms = {term for term in _TERM_PATTERN.findall(folded_claim) if len(term) >= 3}

    candidate_terms = {term for term in _TERM_PATTERN.findall(folded_candidate) if len(term) >= 3}

    overlap = claim_terms.intersection(
        candidate_terms,
    )

    score = float(len(overlap))

    claim_numbers = set(_NUMBER_PATTERN.findall(folded_claim))

    candidate_numbers = set(_NUMBER_PATTERN.findall(folded_candidate))

    for number in claim_numbers:
        if number in candidate_numbers:
            # Giá trị số, giờ, năm... là tín hiệu evidence mạnh.
            score += 6.0

    if folded_claim in folded_candidate:
        score += 10.0

    # Ưu tiên passage ngắn, tập trung.
    if len(candidate) <= 240:
        score += 1.0

    return score


def _exact_value_evidence(
    *,
    claim: str,
    candidate: str,
) -> str | None:
    claim_values = _extract_values(claim)

    if not claim_values:
        return None

    candidate_folded = fold_text(candidate)

    matched_values = [value for value in claim_values if fold_text(value) in candidate_folded]

    if not matched_values:
        return None

    if len(matched_values) == 1:
        return matched_values[0]

    return " | ".join(matched_values)


def _extract_values(text: str) -> tuple[str, ...]:
    value_pattern = re.compile(
        r"""
        # Time range: 8:00 - 16:00
        \b\d{1,2}:\d{2}
        (?:\s*[-–—]\s*\d{1,2}:\d{2})?\b

        |

        # Rate: 8 giờ/ngày, 40 giờ/tuần
        \b\d+(?:[.,]\d+)?\s*
        (?:giờ|gio)
        \s*/\s*
        (?:ngày|ngay|tuần|tuan|tháng|thang|năm|nam)\b

        |

        # General number + unit
        \b\d+(?:[.,]\d+)?\s*
        (?:
            giờ|gio|
            ngày|ngay|
            tuần|tuan|
            tháng|thang|
            năm|nam|
            phút|phut|
            người|nguoi|
            %
        )\b

        |

        # Standalone year
        \b(?:19|20)\d{2}\b
        """,
        re.IGNORECASE | re.UNICODE | re.VERBOSE,
    )

    values: list[str] = []

    for match in value_pattern.finditer(text):
        value = " ".join(match.group(0).split())

        if value not in values:
            values.append(value)

    return tuple(values)
