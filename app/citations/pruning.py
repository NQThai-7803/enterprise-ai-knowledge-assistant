from __future__ import annotations

import re
from collections.abc import Sequence

from app.citations.evidence import extract_exact_evidence
from app.citations.models import PromptSourceRegistry


def prune_redundant_markers(
    *,
    answer: str,
    ordered_markers: Sequence[str],
    source_registry: PromptSourceRegistry,
) -> tuple[str, ...]:
    retained: list[str] = []

    # key:
    # same internal document + same exact evidence
    best_by_evidence: dict[
        tuple[object, str],
        tuple[str, float],
    ] = {}

    for marker in ordered_markers:
        source = source_registry.by_marker(marker)

        if source is None:
            retained.append(marker)
            continue

        evidence_text = extract_exact_evidence(
            answer=answer,
            marker=marker,
            source_text=source.text,
        )

        # Không có exact evidence thì không tự dedupe.
        if not evidence_text:
            retained.append(marker)
            continue

        # WEB hoặc nguồn không có document_id:
        # không gom chung.
        if source.document_id is None:
            retained.append(marker)
            continue

        normalized_evidence = _normalize_evidence(evidence_text)

        key = (
            source.document_id,
            normalized_evidence,
        )

        score = (
            source.reranker_score if source.reranker_score is not None else source.semantic_score
        )

        numeric_score = score if score is not None else source.hybrid_score

        existing = best_by_evidence.get(key)

        if existing is None:
            best_by_evidence[key] = (
                marker,
                numeric_score,
            )
            continue

        existing_marker, existing_score = existing

        if numeric_score > existing_score:
            best_by_evidence[key] = (
                marker,
                numeric_score,
            )

    selected = {marker for marker, _score in best_by_evidence.values()}

    # Marker không có evidence/document_id được giữ ở retained.
    selected.update(retained)

    return tuple(marker for marker in ordered_markers if marker in selected)


def remove_pruned_markers(
    *,
    answer: str,
    retained_markers: Sequence[str],
) -> str:
    retained = set(retained_markers)

    def replace(
        match: re.Match[str],
    ) -> str:
        marker = match.group(0)

        if marker in retained:
            return marker

        return ""

    cleaned = re.sub(
        r"\[SOURCE_[1-9][0-9]*\]",
        replace,
        answer,
    )

    # cleanup spaces left by removed markers
    cleaned = re.sub(
        r"[ \t]{2,}",
        " ",
        cleaned,
    )

    cleaned = re.sub(
        r"[ \t]+([,.;:!?])",
        r"\1",
        cleaned,
    )

    return cleaned.strip()


def _normalize_evidence(
    evidence_text: str,
) -> str:
    return " ".join(evidence_text.casefold().split())
