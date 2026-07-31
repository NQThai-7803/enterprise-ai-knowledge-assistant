from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ChatMessageRole

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession
    from app.models.feedback import Feedback
    from app.models.message_citation import MessageCitation


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(content)) > 0", name="ck_chat_messages_content_not_blank"
        ),
        CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="ck_chat_messages_response_time_non_negative",
        ),
        CheckConstraint(
            "prompt_tokens IS NULL OR prompt_tokens >= 0",
            name="ck_chat_messages_prompt_tokens_non_negative",
        ),
        CheckConstraint(
            "completion_tokens IS NULL OR completion_tokens >= 0",
            name="ck_chat_messages_completion_tokens_non_negative",
        ),
        Index("ix_chat_messages_session_created", "session_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ChatMessageRole] = mapped_column(
        Enum(ChatMessageRole, name="chat_message_role"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="messages")
    citations: Mapped[list[MessageCitation]] = relationship(
        "MessageCitation",
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedback: Mapped[list[Feedback]] = relationship(
        "Feedback",
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
