from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.models import ChatMessageRole

_FOLLOW_UP_PREFIXES = (
    "con ",
    "the con ",
    "vay con ",
    "vay ",
    "neu vay ",
    "truong hop do ",
    "truong hop nay ",
    "nguoi do ",
    "nguoi nay ",
    "what about ",
    "how about ",
    "and after ",
    "if ",
    "when ",
    "does it ",
    "is it ",
    "are there ",
    "do they ",
)

_FOLLOW_UP_REFERENCES = (
    "thi sao",
    "truong hop nay",
    "truong hop do",
    "nguoi nay",
    "nguoi do",
    "nhu vay",
    "cai do",
    "che do do",
    "che do nay",
    " no ",
    " ho ",
    " he ",
    " him ",
    " she ",
    " her ",
    " they ",
    " them ",
    " it ",
)

_FRAME_PREFIXES = (
    "the con ",
    "vay con ",
    "con ",
    "what about ",
    "how about ",
    "and ",
)

_FRAME_SUFFIXES = (
    " thi nhu the nao",
    " thi sao",
)

_CONDITIONAL_PREFIXES = (
    "sau ",
    "neu ",
    "khi ",
    "trong truong hop ",
    "after ",
    "if ",
    "when ",
    "for ",
)

_ACRONYM_PATTERN = re.compile(r"\b[A-Z][A-Z0-9&/+.-]{1,}\b")
_WORD_PATTERN_TEMPLATE = r"(?<!\w){word}(?!\w)"
_QUESTION_TARGET_SUFFIXES = (
    " la ai",
    " la gi",
    " duoc quy dinh nhu the nao",
)
_QUANTITY_TOPIC_MARKERS = (" bao nhieu", " how many")
_CHANGE_QUESTION_SUFFIX = "thay \u0111\u1ed5i nh\u01b0 th\u1ebf n\u00e0o"
_QUESTION_TERMINATORS = " ?!."
_VIETNAMESE_BASE_TRANSLATION = str.maketrans(
    {
        "\u0111": "d",
        "\u0110": "d",
        "\u01b0": "u",
        "\u01af": "u",
        "\u01a1": "o",
        "\u01a0": "o",
    }
)


@dataclass(frozen=True, slots=True)
class ResolvedConversationQuestion:
    original_question: str = field(repr=False)
    standalone_question: str = field(repr=False)
    context_dependent: bool
    source_user_message_ids: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if not self.original_question.strip():
            msg = "original_question must not be empty."
            raise ValueError(msg)
        if not self.standalone_question.strip():
            msg = "standalone_question must not be empty."
            raise ValueError(msg)
        object.__setattr__(self, "original_question", self.original_question.strip())
        object.__setattr__(self, "standalone_question", self.standalone_question.strip())
        object.__setattr__(
            self,
            "source_user_message_ids",
            tuple(self.source_user_message_ids),
        )


def resolve_conversation_question(
    question: str,
    *,
    messages: Sequence[object],
) -> ResolvedConversationQuestion:
    current_question = question.strip()
    previous_user_messages = tuple(_user_messages(messages))
    if not previous_user_messages or not is_context_dependent_question(current_question):
        return ResolvedConversationQuestion(
            original_question=current_question,
            standalone_question=current_question,
            context_dependent=False,
        )

    anchor_index = _latest_standalone_anchor_index(previous_user_messages)
    relevant_messages = previous_user_messages[anchor_index:]
    previous_question = _message_content(relevant_messages[0])
    for previous_message in relevant_messages[1:]:
        message_question = _message_content(previous_message)
        if is_context_dependent_question(message_question):
            previous_question = _resolve_against_previous_question(
                previous_question=previous_question,
                current_question=message_question,
            )
        else:
            previous_question = message_question
    standalone_question = _resolve_against_previous_question(
        previous_question=previous_question,
        current_question=current_question,
    )
    if not standalone_question.strip():
        standalone_question = current_question

    return ResolvedConversationQuestion(
        original_question=current_question,
        standalone_question=standalone_question,
        context_dependent=True,
        source_user_message_ids=tuple(_message_id(message) for message in relevant_messages),
    )


def is_context_dependent_question(question: str) -> bool:
    normalized = _fold_text(re.sub(r"\s+", " ", question.strip()))

    if not normalized:
        return False

    if any(normalized.startswith(prefix) for prefix in _FOLLOW_UP_PREFIXES):
        return True

    word_count = len(normalized.split())
    padded = f" {normalized} "
    return word_count <= 12 and any(reference in padded for reference in _FOLLOW_UP_REFERENCES)


def render_user_reference_history(messages: Sequence[object]) -> str:
    from app.chat.conversation_context_builder import render_conversation_history

    return render_conversation_history(tuple(_user_messages(messages)))


def _resolve_against_previous_question(
    *,
    previous_question: str,
    current_question: str,
) -> str:
    previous_question = previous_question.strip()
    current_question = current_question.strip()

    target = _extract_previous_question_target(previous_question)
    if not target:
        target = _extract_short_reference_topic(previous_question)
    if target:
        pronoun_resolved = _replace_pronoun_reference(current_question, target)
        if pronoun_resolved != current_question:
            return _ensure_question(pronoun_resolved)

    mode_topic = _extract_previous_mode_topic(previous_question)
    if mode_topic:
        mode_resolved = _replace_pronoun_reference(
            current_question,
            f"che do {mode_topic}",
        )
        if mode_resolved != current_question:
            return _ensure_question(mode_resolved)

    focus = _extract_follow_up_focus(current_question)
    if focus:
        condition_replaced = _replace_parallel_condition(previous_question, focus)
        if condition_replaced is not None:
            return _ensure_question(condition_replaced)
        if _starts_with_any(focus, _CONDITIONAL_PREFIXES):
            return _append_focus_to_previous_question(previous_question, focus)
        acronym_replaced = _replace_parallel_acronym(previous_question, focus)
        if acronym_replaced is not None:
            return _ensure_question(acronym_replaced)
        quantity_replaced = _replace_parallel_quantity_focus(previous_question, focus)
        if quantity_replaced is not None:
            return _ensure_question(quantity_replaced)
        topic_expanded = _expand_explicit_topic_follow_up(current_question, focus)
        if topic_expanded is not None:
            return _ensure_question(topic_expanded)
        if len(_fold_text(focus).split()) >= 2:
            return _ensure_question(focus)
        return _append_focus_to_previous_question(previous_question, focus)

    return _merge_previous_topic_with_current_question(previous_question, current_question)


def _user_messages(messages: Sequence[object]) -> tuple[object, ...]:
    users: list[object] = []
    for message in messages:
        try:
            role = ChatMessageRole(message.role)
        except ValueError:
            continue
        if role == ChatMessageRole.USER and _message_content(message):
            users.append(message)
    return tuple(users)


def _latest_standalone_anchor_index(messages: Sequence[object]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if not is_context_dependent_question(_message_content(messages[index])):
            return index
    return 0


def _message_content(message: object) -> str:
    content = getattr(message, "content", "")
    return content.strip() if isinstance(content, str) else ""


def _message_id(message: object) -> UUID:
    message_id = message.id
    if not isinstance(message_id, UUID):
        msg = "message id must be a UUID."
        raise ValueError(msg)
    return message_id


def _extract_follow_up_focus(question: str) -> str:
    text = _strip_terminal(question)
    folded = _fold_text(text)

    for prefix in sorted(_FRAME_PREFIXES, key=len, reverse=True):
        if folded.startswith(prefix):
            return _strip_frame_suffix(text[len(prefix) :])

    return _strip_frame_suffix(text)


def _strip_frame_suffix(text: str) -> str:
    stripped = _strip_terminal(text)
    folded = _fold_text(stripped)
    for suffix in sorted(_FRAME_SUFFIXES, key=len, reverse=True):
        if folded.endswith(suffix):
            return _strip_terminal(stripped[: -len(suffix)])
    return stripped


def _replace_parallel_acronym(previous_question: str, focus: str) -> str | None:
    focus = _strip_terminal(focus)
    if not _looks_like_acronym(focus):
        return None
    match = _ACRONYM_PATTERN.search(previous_question)
    if match is None:
        return None
    if match.group(0) == focus:
        return previous_question
    return f"{previous_question[: match.start()]}{focus}{previous_question[match.end() :]}"


def _looks_like_acronym(text: str) -> bool:
    return (
        bool(text)
        and len(text.split()) == 1
        and len(text) <= 12
        and text.upper() == text
        and any(character.isalpha() for character in text)
    )


def _append_focus_to_previous_question(previous_question: str, focus: str) -> str:
    previous = _strip_terminal(previous_question)
    focus = _strip_terminal(focus)
    if _starts_with_any(focus, _CONDITIONAL_PREFIXES):
        quantity_topic = _extract_quantity_topic(previous_question)
        if quantity_topic:
            return _ensure_question(f"{quantity_topic} {focus} {_CHANGE_QUESTION_SUFFIX}")
        return _ensure_question(f"{previous} {focus}")
    return _ensure_question(f"{previous} - {focus}")


def _replace_parallel_condition(previous_question: str, focus: str) -> str | None:
    if not _starts_with_any(focus, _CONDITIONAL_PREFIXES):
        return None
    # A condition following a quantity question asks how that entitlement changes,
    # not for the original base quantity with a condition merely appended.  Let
    # ``_append_focus_to_previous_question`` turn that first follow-up into a
    # change question.  Subsequent conditions can then replace the prior one.
    if _extract_quantity_topic(previous_question):
        return None
    previous = _strip_terminal(previous_question)
    folded_previous = _fold_text(previous)
    condition_separator = re.search(
        r"\s+-\s+(?=(?:sau|neu|khi|trong truong hop|after|if|when|for)\b)",
        folded_previous,
    )
    if condition_separator is not None:
        previous = previous[: condition_separator.start()].rstrip()
    else:
        generated_condition = re.search(
            r"\s+(?:sau|neu|khi|trong truong hop|after|if|when|for)\b"
            r".*\bthay doi nhu the nao$",
            folded_previous,
        )
        if generated_condition is not None:
            previous = previous[: generated_condition.start()].rstrip()
    return f"{previous} - {_strip_terminal(focus)}"


def _expand_explicit_topic_follow_up(question: str, focus: str) -> str | None:
    """Make a short explicit topic switch independently answerable.

    Frames such as ``Còn salary review thì sao?`` name a new topic but do not
    state an attribute.  A bare ``salary review?`` is unnecessarily ambiguous
    for retrieval/generation, while replaying the previous attribute would
    pollute the topic switch.  Expand only short, non-question topics into a
    generic policy-description question.
    """

    folded_question = _fold_text(_strip_terminal(question))
    folded_focus = _fold_text(_strip_terminal(focus))
    words = folded_focus.split()
    if len(words) < 2 or len(words) > 6:
        return None
    question_cues = (
        "bao nhieu",
        "la ai",
        "la gi",
        "nhu the nao",
        "how many",
        "how much",
        "who ",
        "what ",
        "when ",
        "where ",
        "why ",
        "does ",
        "is ",
        "are ",
    )
    if any(cue in f"{folded_focus} " for cue in question_cues):
        return None
    if folded_question.startswith(("what about ", "how about ")):
        return f"How is {_strip_terminal(focus)} defined"
    if folded_question.startswith(("con ", "the con ", "vay con ", "vay ")) or any(
        folded_question.endswith(suffix.strip()) for suffix in _FRAME_SUFFIXES
    ):
        return f"{_strip_terminal(focus)} được quy định như thế nào"
    return None


def _replace_parallel_quantity_focus(previous_question: str, focus: str) -> str | None:
    folded_previous = _fold_text(_strip_terminal(previous_question))
    quantity_positions = tuple(
        position
        for marker in _QUANTITY_TOPIC_MARKERS
        if (position := folded_previous.find(marker)) > 0
    )
    if not quantity_positions:
        return None
    quantity_start = min(quantity_positions)
    attribute_markers = (
        "han muc",
        "phu cap",
        "tro cap",
        "muc ho tro",
        "so ngay",
        "thoi luong",
        "ty le",
    )
    marker_matches = tuple(
        match
        for marker in attribute_markers
        if (match := re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", folded_previous)) is not None
        and match.end() <= quantity_start
    )
    if not marker_matches:
        return None
    marker_match = max(marker_matches, key=lambda match: match.end())
    previous = _strip_terminal(previous_question)
    prefix = previous[: marker_match.end()].rstrip()
    suffix = previous[quantity_start:].lstrip()
    return f"{prefix} {_strip_terminal(focus)} {suffix}"


def _extract_quantity_topic(previous_question: str) -> str:
    text = _strip_terminal(previous_question)
    folded = _fold_text(text)
    marker_positions = [
        folded.find(marker) for marker in _QUANTITY_TOPIC_MARKERS if folded.find(marker) > 0
    ]
    if not marker_positions:
        return ""
    marker_position = min(marker_positions)
    marker = next(
        marker for marker in _QUANTITY_TOPIC_MARKERS if folded.find(marker) == marker_position
    )
    prefix = _strip_terminal(text[:marker_position])
    suffix = _strip_terminal(text[marker_position + len(marker) :])
    folded_prefix = _fold_text(prefix)
    if folded_prefix.endswith(" co") and suffix:
        subject = _strip_terminal(prefix[: -len(" co")])
        if subject:
            return f"{suffix} của {subject}"
    return prefix


def _merge_previous_topic_with_current_question(
    previous_question: str,
    current_question: str,
) -> str:
    previous = _strip_terminal(previous_question)
    current = _strip_terminal(current_question)
    return _ensure_question(f"{previous} - {current}")


def _extract_previous_question_target(previous_question: str) -> str:
    text = _strip_terminal(previous_question)
    folded = _fold_text(text)

    for suffix in _QUESTION_TARGET_SUFFIXES:
        if folded.endswith(suffix):
            return _strip_terminal(text[: -len(suffix)])

    for prefix in ("who is ", "who are ", "what is ", "what are "):
        if folded.startswith(prefix):
            return _strip_terminal(text[len(prefix) :])

    if folded.startswith("how is ") and folded.endswith(" defined"):
        return _strip_terminal(text[len("how is ") : -len(" defined")])

    return ""


def _extract_short_reference_topic(previous_question: str) -> str:
    text = _strip_terminal(previous_question)
    folded = _fold_text(text)
    words = folded.split()
    if not words or len(words) > 6:
        return ""
    if any(marker.strip() in folded for marker in _QUANTITY_TOPIC_MARKERS):
        return ""
    if any(folded.startswith(prefix) for prefix in _FOLLOW_UP_PREFIXES):
        return ""
    return text


def _extract_previous_mode_topic(previous_question: str) -> str:
    folded = _fold_text(_strip_terminal(previous_question))
    for pattern in (
        r"\blam\s+([\w-]{2,40})\s+(?:thi|co|can|phai|duoc)\b",
        r"\bche do\s+([\w-]{2,40})\s+(?:thi|co|can|phai|duoc)\b",
    ):
        match = re.search(pattern, folded)
        if match is not None:
            return match.group(1)
    return ""


def _replace_pronoun_reference(question: str, replacement: str) -> str:
    replacements = (
        "che do nay",
        "che do do",
        "nguoi nay",
        "nguoi do",
        "that person",
        "this person",
        "no",
        "ho",
        "he",
        "him",
        "she",
        "her",
        "they",
        "them",
        "it",
    )
    folded = _fold_text(question)
    for pronoun in replacements:
        match = re.search(
            _WORD_PATTERN_TEMPLATE.format(word=re.escape(pronoun)),
            folded,
        )
        if match is not None:
            return f"{question[: match.start()]}{replacement}{question[match.end() :]}"
    return question


def _starts_with_any(text: str, prefixes: tuple[str, ...]) -> bool:
    folded = _fold_text(text)
    return any(folded.startswith(prefix) for prefix in prefixes)


def _ensure_question(text: str) -> str:
    stripped = _strip_terminal(text)
    return f"{stripped}?"


def _strip_terminal(text: str) -> str:
    return text.strip().rstrip(_QUESTION_TERMINATORS).strip()


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).casefold()
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return normalized.translate(_VIETNAMESE_BASE_TRANSLATION)
