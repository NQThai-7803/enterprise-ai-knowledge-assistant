from __future__ import annotations

import re
import unicodedata

_HORIZONTAL_WHITESPACE_RE = re.compile(r"[^\S\n]+")
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")


def normalize_extracted_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\x00", "")
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = normalized.replace("\f", "\n")
    normalized = normalized.replace("\u2028", "\n").replace("\u2029", "\n\n")
    normalized = _HORIZONTAL_WHITESPACE_RE.sub(" ", normalized)
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = normalized.strip()
    return _EXCESS_BLANK_LINES_RE.sub("\n\n", normalized)


def count_usable_characters(text: str) -> int:
    count = 0
    for character in text:
        if character.isspace():
            continue
        if unicodedata.category(character).startswith("C"):
            continue
        count += 1
    return count
