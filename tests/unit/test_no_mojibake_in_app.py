"""Guard: application source must not contain UTF-8 text that was decoded as cp1252.

Each pattern is the cp1252 rendering of a UTF-8 lead byte plus a continuation byte, so correct
Vietnamese never contains it. A bare "\u00c3" is allowed (it is a valid uppercase Vietnamese
letter); it is only flagged when a continuation-byte character follows it.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
TEXT_SUFFIXES = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".jinja", ".j2", ".html"}
MOJIBAKE_RE = re.compile(
    "\u00c3[\u0080-\u00bf]"  # e.g. "\u00c3\u00b4" for U+00F4
    "|\u00e1\u00bb"  # lead of U+1EC0..U+1EFF (Vietnamese letters with two marks)
    "|\u00c4\u2018"  # U+0111
    "|\u00e2\u20ac"  # U+2010..U+203F, including the U+2022 bullet
    "|\u00ef\u201a"  # U+F0xx private-use symbol-font characters
)


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


def test_app_directory_is_scanned() -> None:
    assert (APP_DIR / "services" / "grounded_answer_service.py").is_file()


def test_app_source_has_no_mojibake() -> None:
    assert [f"{path}:{number}" for path, number, _ in _mojibake_hits()] == []


def test_guard_pattern_flags_mojibake_but_not_vietnamese() -> None:
    assert MOJIBAKE_RE.search("c\u00c3\u00b4ng vi\u00e1\u00bb\u2021c")
    assert MOJIBAKE_RE.search("\u00c4\u2018i\u00e1\u00bb\u0081u")
    assert MOJIBAKE_RE.search("\u00e2\u20ac\u00a2 m\u1ee5c")
    assert MOJIBAKE_RE.search("\u00ef\u201a\u00b7")
    assert not MOJIBAKE_RE.search(
        "c\u00f4ng vi\u1ec7c trong \u0111i\u1ec1u ki\u1ec7n b\u00ecnh th\u01b0\u1eddng"
    )
    assert not MOJIBAKE_RE.search("NG\u00c3 BA \u2022 \u20ab \uf0b7")
