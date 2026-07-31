from __future__ import annotations

import re

from app.citations.models import ParsedCitationMarkers

SOURCE_MARKER_PATTERN = re.compile(r"\[SOURCE_([1-9][0-9]*)\]")


def parse_citation_markers(answer: str) -> ParsedCitationMarkers:
    occurrences = tuple(match.group(0) for match in SOURCE_MARKER_PATTERN.finditer(answer))
    seen: set[str] = set()
    ordered_unique: list[str] = []
    for marker in occurrences:
        if marker not in seen:
            seen.add(marker)
            ordered_unique.append(marker)
    return ParsedCitationMarkers(
        ordered_unique_markers=tuple(ordered_unique),
        all_marker_occurrences=occurrences,
    )
