from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.models import ChatMessage


class GroundingStatus(StrEnum):
    ANSWERED = "ANSWERED"
    NO_ANSWER = "NO_ANSWER"


@dataclass(frozen=True, slots=True)
class SelectedContextItem:
    ordinal: int
    text: str = field(repr=False)
    token_count: int
    chunk_id: UUID | None = None
    document_id: UUID | None = None
    document_title: str | None = None
    page_numbers: tuple[int, ...] | None = None
    start_page: int | None = None
    end_page: int | None = None
    semantic_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None

    def __post_init__(self) -> None:
        if self.ordinal < 1:
            msg = "Context item ordinal must be one-based."
            raise ValueError(msg)
        if not isinstance(self.text, str) or not self.text.strip():
            msg = "Context item text must not be empty."
            raise ValueError(msg)
        if self.token_count <= 0:
            msg = "Context item token count must be greater than zero."
            raise ValueError(msg)
        if self.page_numbers is not None:
            object.__setattr__(self, "page_numbers", tuple(self.page_numbers))


@dataclass(frozen=True, slots=True)
class SelectedContext:
    items: tuple[SelectedContextItem, ...]
    selected_chunk_count: int
    estimated_token_count: int

    def __post_init__(self) -> None:
        items = tuple(self.items)
        object.__setattr__(self, "items", items)
        if self.selected_chunk_count != len(items):
            msg = "selected_chunk_count must match items length."
            raise ValueError(msg)
        if self.estimated_token_count < 0:
            msg = "estimated_token_count must not be negative."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ChatAnswerResult:
    session_id: UUID
    user_message: ChatMessage
    assistant_message: ChatMessage
    grounding_status: GroundingStatus
    retrieved_chunk_count: int
    assistant_citations: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        if self.retrieved_chunk_count < 0:
            msg = "retrieved_chunk_count must not be negative."
            raise ValueError(msg)
        object.__setattr__(self, "assistant_citations", tuple(self.assistant_citations))
