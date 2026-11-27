from __future__ import annotations

import re

_WHITESPACE_PATTERN = re.compile(r"\s+")
# BR-14: PDF bullets set in the Symbol/Wingdings fonts are extracted as Private Use Area code
# points (U+F0B7, U+F0A7, U+F0D8, ...) that no UI font can draw.
# shortcut: every U+F000-U+F0FF becomes "•", so a Greek letter set in Symbol would too; the real
# mapping belongs at extraction (TASKS, with corpus v3).
_SYMBOL_FONT_PUA_PATTERN = re.compile("[-]")


def display_text(text: str) -> str:
    """Citation text as shown to the user: Symbol/Wingdings PUA bullets become "•".

    Same length as the input, so offsets and the excerpt's character budget still hold. Only
    for excerpts and evidence shown in a citation; chunks, prompts and validation keep the text.
    """

    return _SYMBOL_FONT_PUA_PATTERN.sub("•", text)


# BR-15: a word for evidence matching; "…" (the excerpt's own cut mark) is never part of one.
_SPAN_WORD_PATTERN = re.compile(r"[^\s…]+")
_MIN_SPAN_COVERAGE = 0.6


def evidence_spans(excerpt: str, evidence_text: str | None) -> list[tuple[int, int]]:
    """Where ``evidence_text`` sits in ``excerpt``, as [start, end) character offsets (BR-15).

    Display only. The evidence is matched word by word and in order, so it may skip words of
    the excerpt (a heading between two of its parts) and give several spans; its first word may
    be the end of an excerpt word and its last word the start of one. A part of one word inside
    longer evidence is ignored as chance, and [] is returned when less than 60% of the evidence
    words are found. Both texts are compared as shown (``display_text``), which keeps offsets.
    """

    if not evidence_text or not excerpt:
        return []
    # Case-sensitive: both texts come from the same chunk, and offsets must stay exact.
    words = [
        (match.start(), match.end(), match.group())
        for match in _SPAN_WORD_PATTERN.finditer(display_text(excerpt))
    ]
    wanted = _SPAN_WORD_PATTERN.findall(display_text(evidence_text))
    if not wanted:
        return []

    def run_at(k: int, i: int) -> tuple[int, int, int]:
        """Words matched from excerpt word k and evidence word i: (count, start, end)."""

        count, start, end = 0, words[k][0], words[k][1]
        while k + count < len(words) and i + count < len(wanted):
            word_start, word_end, word = words[k + count]
            target = wanted[i + count]
            if word == target:
                end = word_end
            elif i + count == len(wanted) - 1 and word.startswith(target):
                end = word_start + len(target)
            elif i + count == 0 and count == 0 and word.endswith(target):
                start, end = word_end - len(target), word_end
            else:
                break
            count += 1
        return count, start, end

    spans: list[tuple[int, int]] = []
    matched, i, j = 0, 0, 0
    while i < len(wanted):
        best = (0, 0, 0, 0)  # count, excerpt word, start, end
        for k in range(j, len(words)):
            count, start, end = run_at(k, i)
            if count > best[0]:
                best = (count, k, start, end)
        count, k, start, end = best
        if count == 0 or (count == 1 and len(wanted) > 1):
            i += 1  # not in the excerpt (or only by chance): skip this evidence word
            continue
        spans.append((start, end))
        matched += count
        i, j = i + count, k + count
    if matched < _MIN_SPAN_COVERAGE * len(wanted):
        return []
    return spans


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


def build_evidence_centered_excerpt(
    *,
    source_text: str,
    evidence_text: str | None,
    max_characters: int,
    starts_mid_word: bool = False,
) -> str:
    """Build an excerpt that retains the exact evidence when it is known.

    ``starts_mid_word``: the source opens with the token overlap of the previous chunk, which
    can begin inside a word (BR-14). That partial first word is dropped and "…" marks the cut,
    unless the evidence itself starts there.
    """

    normalized = _WHITESPACE_PATTERN.sub(" ", source_text).strip()
    evidence = _WHITESPACE_PATTERN.sub(" ", evidence_text or "").strip()
    if starts_mid_word and max_characters > 1:
        first_space = normalized.find(" ")
        evidence_index = normalized.find(evidence) if evidence else -1
        if first_space > 0 and (evidence_index < 0 or evidence_index > first_space):
            excerpt = build_evidence_centered_excerpt(
                source_text=normalized[first_space + 1 :],
                evidence_text=evidence_text,
                max_characters=max_characters - 1,
            )
            return excerpt if excerpt.startswith("…") else f"…{excerpt}"
    if not evidence or len(normalized) <= max_characters:
        return build_excerpt(source_text=source_text, max_characters=max_characters)

    evidence_index = normalized.find(evidence)
    if evidence_index < 0:
        return build_excerpt(source_text=source_text, max_characters=max_characters)

    leading_ellipsis = evidence_index > 0
    trailing_ellipsis = evidence_index + len(evidence) < len(normalized)
    ellipsis_count = int(leading_ellipsis) + int(trailing_ellipsis)
    content_budget = max_characters - ellipsis_count
    if content_budget <= 0 or len(evidence) > content_budget:
        return build_excerpt(source_text=evidence, max_characters=max_characters)

    surrounding_budget = content_budget - len(evidence)
    start = max(0, evidence_index - surrounding_budget // 2)
    end = min(len(normalized), evidence_index + len(evidence) + surrounding_budget // 2)
    if end - start < content_budget:
        if start == 0:
            end = min(len(normalized), content_budget)
        elif end == len(normalized):
            start = max(0, end - content_budget)

    excerpt = normalized[start:end].strip()
    if start > 0:
        boundary = excerpt.find(" ")
        if boundary >= 0:
            excerpt = excerpt[boundary + 1 :].lstrip()
        excerpt = f"…{excerpt}"
    if end < len(normalized):
        boundary = excerpt.rfind(" ")
        if boundary > 0 and len(excerpt) >= max_characters:
            excerpt = excerpt[:boundary].rstrip()
        excerpt = f"{excerpt}…"
    return excerpt[:max_characters]
