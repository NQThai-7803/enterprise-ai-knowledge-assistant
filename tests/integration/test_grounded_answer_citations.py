from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.chat.models import GroundingStatus
from app.core.config import Settings
from app.core.exceptions import CitationValidationFailedApplicationError
from app.llm.models import LLMGenerationResult
from app.models import (
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    DocumentAccessScope,
    DocumentPermission,
    MessageCitation,
    User,
    UserRole,
)
from app.retrieval.models import HybridRetrievalHit, HybridRetrievalResult
from app.services.grounded_answer_service import GroundedAnswerService
from tests.integration.retrieval_helpers import (
    create_chunk,
    create_document,
    create_permission,
    create_user,
)

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


class FakeCounter:
    def count(self, text: str) -> int:
        return len(text.split())

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens) -> str:  # noqa: ANN001
        return " ".join("x" for _ in tokens)


class FakeRetrievalService:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self.result = result

    async def retrieve(self, *, query: str, current_user: User, top_k: int | None = None):
        return self.result


class FakeLLMProvider:
    def __init__(self, content: str) -> None:
        self.content = content
        self.messages = ()

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.messages = messages
        return LLMGenerationResult(
            content=self.content,
            model="fake",
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=4,
            response_time_ms=25,
        )


class RevokingLLMProvider(FakeLLMProvider):
    def __init__(
        self,
        *,
        content: str,
        session_factory: async_sessionmaker[AsyncSession],
        grant_id,
    ) -> None:  # noqa: ANN001
        super().__init__(content)
        self.session_factory = session_factory
        self.grant_id = grant_id

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        async with self.session_factory() as session:
            await session.execute(
                delete(DocumentPermission).where(DocumentPermission.id == self.grant_id)
            )
            await session.commit()
        return await super().generate(
            messages=messages,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )


def settings() -> Settings:
    return Settings(
        _env_file=None,
        llm_enabled=True,
        llm_base_url="http://localhost:11434/v1",
        llm_model="fake-model",
        chat_context_max_tokens=2000,
        chat_retrieval_top_k=2,
        chat_history_max_tokens=200,
        citation_max_sources_per_answer=2,
    )


async def create_chat_session(session: AsyncSession, owner: User) -> ChatSession:
    chat = ChatSession(
        user_id=owner.id,
        title="Citations",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


def result_for_hit(hit: HybridRetrievalHit) -> HybridRetrievalResult:
    return HybridRetrievalResult(
        hits=(hit,),
        hit_count=1,
        requested_top_k=2,
        semantic_candidate_count=1,
        keyword_candidate_count=0,
        fused_candidate_count=1,
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )


def retrieval_hit(document, chunk) -> HybridRetrievalHit:  # noqa: ANN001
    return HybridRetrievalHit(
        chunk_id=chunk.id,
        document_id=document.id,
        document_title=document.title,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        page_numbers=tuple(chunk.page_numbers),
        start_page=chunk.start_page,
        end_page=chunk.end_page,
        token_count=chunk.token_count,
        hybrid_score=1.0,
        semantic_score=0.87,
        semantic_rank=1,
        keyword_score=None,
        keyword_rank=None,
        matched_by=("semantic",),
    )


def test_answer_persists_citations_with_assistant_message(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "citation-answer-owner", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
            document = await create_document(
                session,
                "citation-answer-doc",
                uploader=owner,
                title="Leave policy",
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            chunk = await create_chunk(
                session,
                "citation-answer-chunk",
                document=document,
                text="Nhan vien chinh thuc duoc huong 12 ngay nghi phep moi nam.",
                page_numbers=(14,),
            )
            session.add(
                ChatMessage(
                    session_id=chat.id,
                    role=ChatMessageRole.ASSISTANT,
                    content="Historical answer [SOURCE_999]",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )
            await session.commit()
        llm = FakeLLMProvider(
            '{"answer":"Nhan vien duoc huong 12 ngay nghi phep","citations":["SOURCE_1"]}'
        )
        service = GroundedAnswerService(
            settings=settings(),
            session_provider=async_session_factory_for_tests,
            hybrid_retrieval_service=FakeRetrievalService(
                result_for_hit(retrieval_hit(document, chunk))
            ),
            llm_provider_factory=lambda: llm,
            token_counter=FakeCounter(),
        )

        result = await service.answer_question(
            current_user=owner,
            session_id=chat.id,
            question="Nghi phep bao nhieu ngay?",
        )

        async with async_session_factory_for_tests() as session:
            messages = list(
                await session.scalars(
                    select(ChatMessage).order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                )
            )
            citations = list(await session.scalars(select(MessageCitation)))
            assert [message.role for message in messages] == [
                ChatMessageRole.ASSISTANT,
                ChatMessageRole.USER,
                ChatMessageRole.ASSISTANT,
            ]
            assert messages[0].content == "Historical answer [SOURCE_999]"
            assert "[1]" in messages[2].content
            assert "Historical answer [SOURCE_999]" not in llm.messages[1].content
            assert "--- SOURCE_999 START ---" not in llm.messages[1].content
            assert len(citations) == 1
            assert citations[0].message_id == messages[2].id
            assert citations[0].document_id == document.id
            assert citations[0].chunk_id == chunk.id
            assert citations[0].page_number == 14
            assert citations[0].citation_order == 1
            assert result.assistant_citations[0].document_title == document.title
            assert result.grounding_status == GroundingStatus.ANSWERED

    run_async(scenario())


def test_invalid_citation_persists_no_messages_or_citations(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "citation-invalid-owner", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
            document = await create_document(session, "citation-invalid-doc", uploader=owner)
            chunk = await create_chunk(session, "citation-invalid-chunk", document=document)
        service = GroundedAnswerService(
            settings=settings(),
            session_provider=async_session_factory_for_tests,
            hybrid_retrieval_service=FakeRetrievalService(
                result_for_hit(retrieval_hit(document, chunk))
            ),
            llm_provider_factory=lambda: FakeLLMProvider(
                '{"answer":"Invented source","citations":["SOURCE_999"]}'
            ),
            token_counter=FakeCounter(),
        )

        with pytest.raises(CitationValidationFailedApplicationError):
            await service.answer_question(current_user=owner, session_id=chat.id, question="Q")

        async with async_session_factory_for_tests() as session:
            message_count = await session.scalar(select(func.count()).select_from(ChatMessage))
            citation_count = await session.scalar(select(func.count()).select_from(MessageCitation))
            assert message_count == 0
            assert citation_count == 0

    run_async(scenario())


def test_permission_revoked_during_llm_call_returns_no_answer(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "citation-race-owner", role=UserRole.STAFF)
            grantee = await create_user(session, "citation-race-grantee", role=UserRole.STAFF)
            chat = await create_chat_session(session, grantee)
            document = await create_document(session, "citation-race-doc", uploader=owner)
            chunk = await create_chunk(session, "citation-race-chunk", document=document)
            grant = await create_permission(
                session,
                "citation-race-grant",
                document=document,
                creator=owner,
                user_id=grantee.id,
            )
        llm = RevokingLLMProvider(
            content='{"answer":"Do not return this generated answer","citations":["SOURCE_1"]}',
            session_factory=async_session_factory_for_tests,
            grant_id=grant.id,
        )
        service = GroundedAnswerService(
            settings=settings(),
            session_provider=async_session_factory_for_tests,
            hybrid_retrieval_service=FakeRetrievalService(
                result_for_hit(retrieval_hit(document, chunk))
            ),
            llm_provider_factory=lambda: llm,
            token_counter=FakeCounter(),
        )

        result = await service.answer_question(
            current_user=grantee,
            session_id=chat.id,
            question="Nghi phep bao nhieu ngay?",
        )

        async with async_session_factory_for_tests() as session:
            messages = list(
                await session.scalars(
                    select(ChatMessage).order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                )
            )
            citation_count = await session.scalar(select(func.count()).select_from(MessageCitation))
            assert result.grounding_status == GroundingStatus.NO_ANSWER
            assert result.assistant_citations == ()
            assert citation_count == 0
            assert len(messages) == 2
            assert "Do not return this generated answer" not in messages[1].content

    run_async(scenario())
