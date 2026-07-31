from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.chat.models import GroundingStatus
from app.core.config import Settings
from app.core.exceptions import LLMTimeoutApplicationError
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMGenerationResult
from app.models import (
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    DocumentAccessScope,
    User,
    UserRole,
)
from app.retrieval.hybrid_service import HybridRetrievalService
from app.retrieval.keyword_service import KeywordRetrievalService
from app.retrieval.semantic_service import SemanticRetrievalService
from app.services.grounded_answer_service import GroundedAnswerService
from tests.integration.retrieval_helpers import (
    FakeQueryEmbeddingProvider,
    JitOffSessionProvider,
    create_chunk,
    create_department,
    create_document,
    create_user,
)

pytestmark = pytest.mark.integration
CONFIDENTIAL_MARKER = "CONFIDENTIAL_GROUNDED_CHAT_MARKER"


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "llm_enabled": True,
        "llm_base_url": "http://localhost:11434/v1",
        "llm_model": "fake-model",
        "llm_retry_backoff_seconds": 0.0,
        "chat_context_max_tokens": 1000,
        "chat_retrieval_top_k": 3,
        "chat_history_max_messages": 5,
        "citation_max_sources_per_answer": 3,
        "hybrid_retrieval_top_k": 3,
        "hybrid_retrieval_max_top_k": 10,
        "hybrid_candidate_multiplier": 4,
        "hybrid_semantic_min_relevance_score": 0.0,
        "keyword_min_rank": 0.0,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


class FakeCounter:
    def count(self, text: str) -> int:
        return len(text.split())

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens) -> str:  # noqa: ANN001
        return " ".join("x" for _ in tokens)


class FakeRetrievalService:
    def __init__(self, result) -> None:  # noqa: ANN001
        self.result = result
        self.calls = 0

    async def retrieve(self, *, query: str, current_user: User, top_k: int | None = None):
        self.calls += 1
        return self.result


class FakeLLMProvider:
    def __init__(self, result: LLMGenerationResult | Exception) -> None:
        self.result = result
        self.calls = 0
        self.messages = ()

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.calls += 1
        self.messages = messages
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeCitationValidationService:
    async def validate_and_map(self, *, answer: str, source_registry, current_user: User):  # noqa: ANN001
        return SimpleNamespace(answer=answer.replace("[SOURCE_1]", "[1]"), citations=())


class FakeCitationRepository:
    async def create_many(self, session: object, *, assistant_message: ChatMessage, citations):  # noqa: ANN001
        return tuple(citations)


async def create_chat_session(session: AsyncSession, owner: User) -> ChatSession:
    now = datetime.now(UTC)
    chat = ChatSession(user_id=owner.id, title="Grounded", created_at=now, updated_at=now)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def list_messages(session: AsyncSession, chat: ChatSession) -> list[ChatMessage]:
    rows = await session.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == chat.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    return list(rows)


def llm_answer(content: str = "Grounded answer [SOURCE_1]") -> LLMGenerationResult:
    return LLMGenerationResult(
        content=content,
        model="fake",
        finish_reason="stop",
        prompt_tokens=12,
        completion_tokens=6,
        response_time_ms=321,
    )


def make_fake_hybrid_result():
    from tests.unit.test_grounded_answer_service import hit, retrieval_result

    return retrieval_result(hit("authorized context text"))


def make_service(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    retrieval_result=None,  # noqa: ANN001
    llm_result: LLMGenerationResult | Exception | None = None,
    settings: Settings | None = None,
) -> tuple[GroundedAnswerService, FakeRetrievalService, FakeLLMProvider]:
    retrieval = FakeRetrievalService(retrieval_result or make_fake_hybrid_result())
    llm = FakeLLMProvider(llm_result or llm_answer())
    service = GroundedAnswerService(
        settings=settings or make_settings(),
        session_provider=session_factory,
        hybrid_retrieval_service=retrieval,
        llm_provider_factory=lambda: llm,
        token_counter=FakeCounter(),
        citation_repository=FakeCitationRepository(),
        citation_validation_service=FakeCitationValidationService(),
    )
    return service, retrieval, llm


def test_answer_persists_message_pair(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "grounded-persist", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
        service, _, _ = make_service(async_session_factory_for_tests)

        result = await service.answer_question(
            current_user=owner,
            session_id=chat.id,
            question="Question?",
        )

        async with async_session_factory_for_tests() as session:
            messages = await list_messages(session, chat)
            assert [message.role for message in messages] == [
                ChatMessageRole.USER,
                ChatMessageRole.ASSISTANT,
            ]
            assert messages[0].content == "Question?"
            assert messages[0].prompt_tokens is None
            assert messages[1].content == "Grounded answer [1]"
            assert messages[1].retrieval_query == "Question?"
            assert messages[1].response_time_ms == 321
            assert messages[1].prompt_tokens == 12
            assert messages[1].completion_tokens == 6
            assert messages[0].created_at < messages[1].created_at
            refreshed_chat = await session.get(ChatSession, chat.id)
            assert refreshed_chat is not None
            assert refreshed_chat.updated_at == messages[1].created_at
            assert result.grounding_status == GroundingStatus.ANSWERED

    run_async(scenario())


def test_no_answer_persists_message_pair(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        from tests.unit.test_grounded_answer_service import retrieval_result

        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "grounded-no-answer", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
        service, _, llm = make_service(
            async_session_factory_for_tests,
            retrieval_result=retrieval_result(),
        )

        result = await service.answer_question(current_user=owner, session_id=chat.id, question="Q")

        async with async_session_factory_for_tests() as session:
            messages = await list_messages(session, chat)
            assert len(messages) == 2
            assert messages[1].role == ChatMessageRole.ASSISTANT
            assert messages[1].response_time_ms is None
            assert messages[1].prompt_tokens is None
            assert result.grounding_status == GroundingStatus.NO_ANSWER
            assert llm.calls == 0

    run_async(scenario())


def test_llm_failure_rolls_back_both_messages(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "grounded-rollback", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
        service, _, _ = make_service(
            async_session_factory_for_tests,
            llm_result=LLMError(LLMFailureCode.LLM_TIMEOUT),
        )

        with pytest.raises(LLMTimeoutApplicationError):
            await service.answer_question(current_user=owner, session_id=chat.id, question="Q")

        async with async_session_factory_for_tests() as session:
            messages = await list_messages(session, chat)
            assert messages == []

    run_async(scenario())


def test_system_messages_remain_hidden_after_answer(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "grounded-system-hidden", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
            session.add(
                ChatMessage(
                    session_id=chat.id,
                    role=ChatMessageRole.SYSTEM,
                    content=CONFIDENTIAL_MARKER,
                    created_at=datetime.now(UTC),
                )
            )
            await session.commit()
        service, _, llm = make_service(async_session_factory_for_tests)

        await service.answer_question(current_user=owner, session_id=chat.id, question="Q")

        assert all(CONFIDENTIAL_MARKER not in message.content for message in llm.messages)

    run_async(scenario())


def make_real_hybrid_service(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> HybridRetrievalService:
    session_provider = JitOffSessionProvider(session_factory)
    semantic = SemanticRetrievalService(
        settings=settings,
        embedding_provider=FakeQueryEmbeddingProvider(),
        session_provider=session_provider,
    )
    keyword = KeywordRetrievalService(settings=settings, session_provider=session_provider)
    return HybridRetrievalService(
        settings=settings,
        semantic_retrieval_service=semantic,
        keyword_retrieval_service=keyword,
    )


def test_grounded_answer_uses_authorized_chunks_only(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        settings = make_settings(
            chat_retrieval_top_k=2,
            chat_context_max_tokens=1000,
            citation_max_sources_per_answer=2,
        )
        async with async_session_factory_for_tests() as session:
            department_a = await create_department(session, "grounded-a")
            department_b = await create_department(session, "grounded-b")
            staff_a = await create_user(
                session,
                "grounded-staff-a",
                role=UserRole.STAFF,
                department_id=department_a.id,
            )
            uploader_b = await create_user(
                session,
                "grounded-staff-b",
                role=UserRole.STAFF,
                department_id=department_b.id,
            )
            chat = await create_chat_session(session, staff_a)
            allowed_doc = await create_document(
                session,
                "grounded-allowed",
                uploader=staff_a,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            hidden_doc = await create_document(
                session,
                "grounded-hidden",
                uploader=uploader_b,
                department_id=department_b.id,
                access_scope=DocumentAccessScope.DEPARTMENT,
            )
            await create_chunk(
                session,
                "grounded-allowed",
                document=allowed_doc,
                text="groundedkeyword authorized context",
                similarity=0.9,
            )
            await create_chunk(
                session,
                "grounded-hidden",
                document=hidden_doc,
                text=f"groundedkeyword {CONFIDENTIAL_MARKER}",
                similarity=1.0,
            )
        llm = FakeLLMProvider(llm_answer("safe answer [SOURCE_1]"))
        service = GroundedAnswerService(
            settings=settings,
            session_provider=async_session_factory_for_tests,
            hybrid_retrieval_service=make_real_hybrid_service(
                async_session_factory_for_tests,
                settings,
            ),
            llm_provider_factory=lambda: llm,
            token_counter=FakeCounter(),
        )

        await service.answer_question(
            current_user=staff_a,
            session_id=chat.id,
            question="groundedkeyword",
        )

        assert llm.calls == 1
        assert all(CONFIDENTIAL_MARKER not in message.content for message in llm.messages)

    run_async(scenario())
