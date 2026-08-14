from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer

from app.chat.models import ChatAnswerResult, GroundingStatus
from app.models import ChatMessage, ChatSession, CitationSourceType
from app.repositories.chat_message_repository import VisibleChatMessageRow
from app.repositories.chat_session_repository import ChatSessionListRow
from app.schemas.common import PaginationMeta

CHAT_SESSION_TITLE_SCHEMA_MAX_CHARACTERS = 200
CHAT_MESSAGE_SCHEMA_MAX_CHARACTERS = 12000


class ChatSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=CHAT_SESSION_TITLE_SCHEMA_MAX_CHARACTERS)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(max_length=CHAT_MESSAGE_SCHEMA_MAX_CHARACTERS)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "Chat message content must not be empty."
            raise ValueError(msg)
        return normalized


class ChatSessionSummary(BaseModel):
    id: UUID
    title: str | None
    is_archived: bool
    message_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_session_row(cls, row: ChatSessionListRow) -> ChatSessionSummary:
        return cls(
            id=row.chat_session.id,
            title=row.chat_session.title,
            is_archived=row.chat_session.is_archived,
            message_count=row.visible_message_count,
            created_at=row.chat_session.created_at,
            updated_at=row.chat_session.updated_at,
        )

    @classmethod
    def from_session(
        cls, chat_session: ChatSession, *, message_count: int = 0
    ) -> ChatSessionSummary:
        return cls(
            id=chat_session.id,
            title=chat_session.title,
            is_archived=chat_session.is_archived,
            message_count=message_count,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
        )


class CitationRead(BaseModel):
    document_id: UUID | None
    document_title: str
    chunk_id: UUID | None
    page_number: int = Field(gt=0)
    excerpt: str
    relevance_score: float | None
    citation_order: int = Field(ge=1)
    source_type: CitationSourceType | None = None
    source_url: str | None = None

    @model_serializer(mode="wrap")
    def serialize_citation(self, handler):  # noqa: ANN001, ANN202
        data = handler(self)
        if data.get("source_type") is None:
            data.pop("source_type", None)
        if data.get("source_url") is None:
            data.pop("source_url", None)
        return data

    @classmethod
    def from_citation(cls, citation: object) -> CitationRead:
        source_type = CitationSourceType(
            getattr(citation, "source_type", CitationSourceType.INTERNAL)
        )
        return cls(
            document_id=getattr(citation, "document_id", None),
            document_title=citation.document_title,
            chunk_id=getattr(citation, "chunk_id", None),
            page_number=citation.page_number,
            excerpt=citation.excerpt,
            relevance_score=citation.relevance_score,
            citation_order=citation.citation_order,
            source_type=source_type if source_type == CitationSourceType.WEB else None,
            source_url=(
                getattr(citation, "source_url", None)
                if source_type == CitationSourceType.WEB
                else None
            ),
        )


class ChatMessageRead(BaseModel):
    id: UUID
    role: Literal["USER", "ASSISTANT"]
    content: str
    response_time_ms: int | None
    citations: list[CitationRead] = Field(default_factory=list)
    created_at: datetime

    @classmethod
    def from_visible_row(
        cls,
        row: VisibleChatMessageRow,
        *,
        citations: tuple[object, ...] = (),
    ) -> ChatMessageRead:
        return cls(
            id=row.id,
            role=row.role.value,
            content=row.content,
            response_time_ms=row.response_time_ms,
            citations=[CitationRead.from_citation(citation) for citation in citations]
            if row.role.value == "ASSISTANT"
            else [],
            created_at=row.created_at,
        )

    @classmethod
    def from_message(
        cls,
        message: ChatMessage,
        *,
        citations: tuple[object, ...] = (),
    ) -> ChatMessageRead:
        return cls(
            id=message.id,
            role=message.role.value,
            content=message.content,
            response_time_ms=message.response_time_ms,
            citations=[CitationRead.from_citation(citation) for citation in citations]
            if message.role.value == "ASSISTANT"
            else [],
            created_at=message.created_at,
        )


class ChatSessionDetail(BaseModel):
    id: UUID
    title: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageRead]
    message_pagination: PaginationMeta

    @classmethod
    def from_parts(
        cls,
        *,
        chat_session: ChatSession,
        messages: tuple[VisibleChatMessageRow, ...],
        message_pagination: PaginationMeta,
        citations_by_message_id: dict[UUID, tuple[object, ...]] | None = None,
    ) -> ChatSessionDetail:
        return cls(
            id=chat_session.id,
            title=chat_session.title,
            is_archived=chat_session.is_archived,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            messages=[
                ChatMessageRead.from_visible_row(
                    message,
                    citations=(citations_by_message_id or {}).get(message.id, ()),
                )
                for message in messages
            ],
            message_pagination=message_pagination,
        )


class ChatAnswerResponse(BaseModel):
    session_id: UUID
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    grounding_status: GroundingStatus
    retrieved_chunk_count: int = Field(ge=0)

    @classmethod
    def from_result(cls, result: ChatAnswerResult) -> ChatAnswerResponse:
        return cls(
            session_id=result.session_id,
            user_message=ChatMessageRead.from_message(result.user_message),
            assistant_message=ChatMessageRead.from_message(
                result.assistant_message,
                citations=result.assistant_citations,
            ),
            grounding_status=result.grounding_status,
            retrieved_chunk_count=result.retrieved_chunk_count,
        )
