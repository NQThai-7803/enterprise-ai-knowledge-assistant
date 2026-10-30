"""Guard: application source must not contain UTF-8 text that was decoded as cp1252.

Each pattern is the cp1252 rendering of a UTF-8 lead byte plus a continuation byte, so correct
Vietnamese never contains it. A bare "Ã" is allowed (it is a valid uppercase Vietnamese
letter); it is only flagged when a continuation-byte character follows it.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
TEXT_SUFFIXES = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".jinja", ".j2", ".html"}
MOJIBAKE_RE = re.compile(
    "Ã[\u0080-¿]"  # e.g. "Ã´" for U+00F4
    "|á»"  # lead of U+1EC0..U+1EFF (Vietnamese letters with two marks)
    "|Ä‘"  # U+0111
    "|â€"  # U+2010..U+203F, including the U+2022 bullet
    "|ï‚"  # U+F0xx private-use symbol-font characters
)


# Deferred on purpose (PROMPT 3d): the two garbled leave-category labels in
# _structured_grouped_duration_answer. Repairing them alone makes two category rows share one
# key and drops a value, so they wait for a separate fix of that function (see TASKS.md).
# Exactly these two lines may match; fixing them makes the count assertion fail on purpose.
DEFERRED_FILE = "app/services/grounded_answer_service.py"
DEFERRED_LINE_PREFIX = 'category = "c'
DEFERRED_COUNT = 2


def _mojibake_hits() -> list[tuple[str, int, str]]:
    hits = []
    for path in sorted(APP_DIR.rglob("*")):
        if path.suffix not in TEXT_SUFFIXES or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if MOJIBAKE_RE.search(line):
                hits.append((path.relative_to(APP_DIR.parent).as_posix(), number, line.strip()))
    return hits


def _is_deferred(hit: tuple[str, int, str]) -> bool:
    path, _, line = hit
    return path == DEFERRED_FILE and line.startswith(DEFERRED_LINE_PREFIX)


def test_app_directory_is_scanned() -> None:
    assert (APP_DIR / "services" / "grounded_answer_service.py").is_file()


def test_app_source_has_no_mojibake() -> None:
    unexpected = [hit for hit in _mojibake_hits() if not _is_deferred(hit)]

    assert [f"{path}:{number}" for path, number, _ in unexpected] == []


def test_only_the_deferred_leave_category_labels_remain() -> None:
    deferred = [hit for hit in _mojibake_hits() if _is_deferred(hit)]

    assert len(deferred) == DEFERRED_COUNT, (
        "The deferred leave-category labels changed; if they were repaired, remove the "
        "DEFERRED_* allowance in this test."
    )


def test_guard_pattern_flags_mojibake_but_not_vietnamese() -> None:
    assert MOJIBAKE_RE.search("cÃ´ng viá»‡c")
    assert MOJIBAKE_RE.search("Ä‘iá»\u0081u")
    assert MOJIBAKE_RE.search("â€¢ mục")
    assert MOJIBAKE_RE.search("ï‚·")
    assert not MOJIBAKE_RE.search("công việc trong điều kiện bình thường")
    assert not MOJIBAKE_RE.search("NGÃ BA • ₫ ")
