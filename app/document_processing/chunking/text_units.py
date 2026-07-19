from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from app.document_processing.tokenization.base import TokenCounter

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_DELIMITERS = frozenset(".!?;:")


class TextUnitKind(StrEnum):
    PARAGRAPH = "PARAGRAPH"
    SENTENCE = "SENTENCE"
    TOKEN_WINDOW = "TOKEN_WINDOW"


@dataclass(frozen=True, slots=True)
class TextUnit:
    page_number: int
    text: str = field(repr=False)
    token_count: int | None = None
    overlap_token_count: int = 0
    kind: TextUnitKind = TextUnitKind.PARAGRAPH

    def __post_init__(self) -> None:
        if self.page_number < 1:
            msg = "page_number must be 1-based."
            raise ValueError(msg)
        if not self.text.strip():
            msg = "text must not be empty."
            raise ValueError(msg)
        if self.token_count is not None and self.token_count < 0:
            msg = "token_count must not be negative."
            raise ValueError(msg)
        if self.overlap_token_count < 0:
            msg = "overlap_token_count must not be negative."
            raise ValueError(msg)


def split_paragraphs(page_number: int, text: str) -> tuple[TextUnit, ...]:
    return tuple(
        TextUnit(page_number=page_number, text=paragraph.strip())
        for paragraph in _PARAGRAPH_SPLIT_RE.split(text)
        if paragraph.strip()
    )


def split_sentences(unit: TextUnit) -> tuple[TextUnit, ...]:
    text = unit.text
    pieces: list[TextUnit] = []
    start = 0
    index = 0
    while index < len(text):
        character = text[index]
        next_character = text[index + 1] if index + 1 < len(text) else ""
        is_sentence_delimiter = character in _SENTENCE_DELIMITERS and (
            not next_character or next_character.isspace()
        )
        is_line_boundary = character == "\n"
        if is_sentence_delimiter or is_line_boundary:
            sentence = text[start : index + 1].strip()
            if sentence:
                pieces.append(
                    TextUnit(
                        page_number=unit.page_number,
                        text=sentence,
                        kind=TextUnitKind.SENTENCE,
                    )
                )
            start = index + 1
            while start < len(text) and text[start].isspace():
                start += 1
            index = start
            continue
        index += 1

    tail = text[start:].strip()
    if tail:
        pieces.append(TextUnit(page_number=unit.page_number, text=tail, kind=TextUnitKind.SENTENCE))
    return tuple(pieces)


def split_text_unit_to_token_windows(
    unit: TextUnit,
    token_counter: TokenCounter,
    *,
    max_tokens: int,
    overlap_tokens: int,
) -> tuple[TextUnit, ...]:
    if max_tokens <= 0:
        msg = "max_tokens must be greater than zero."
        raise ValueError(msg)
    if overlap_tokens < 0:
        msg = "overlap_tokens must not be negative."
        raise ValueError(msg)
    if overlap_tokens >= max_tokens:
        msg = "overlap_tokens must be smaller than max_tokens."
        raise ValueError(msg)

    tokens = token_counter.encode(unit.text)
    if len(tokens) <= max_tokens:
        return (
            TextUnit(
                page_number=unit.page_number,
                text=unit.text,
                token_count=len(tokens),
                kind=unit.kind,
            ),
        )

    stride = max_tokens - overlap_tokens
    windows: list[TextUnit] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        window_text, token_count, adjusted_end = _decode_bounded_window(
            token_counter,
            tokens,
            start,
            end,
            max_tokens,
        )
        if window_text:
            windows.append(
                TextUnit(
                    page_number=unit.page_number,
                    text=window_text,
                    token_count=token_count,
                    overlap_token_count=min(overlap_tokens, token_count) if start > 0 else 0,
                    kind=TextUnitKind.TOKEN_WINDOW,
                )
            )
        if adjusted_end >= len(tokens):
            break
        next_start = max(start + 1, adjusted_end - overlap_tokens)
        start = max(next_start, start + stride)
    return tuple(windows)


def _decode_bounded_window(
    token_counter: TokenCounter,
    tokens: Sequence[int],
    start: int,
    end: int,
    max_tokens: int,
) -> tuple[str, int, int]:
    adjusted_end = end
    while adjusted_end > start:
        text = token_counter.decode(tokens[start:adjusted_end]).strip()
        if not text:
            adjusted_end -= 1
            continue
        token_count = token_counter.count(text)
        if token_count <= max_tokens:
            return text, token_count, adjusted_end
        adjusted_end -= 1
    return "", 0, max(start + 1, end)
