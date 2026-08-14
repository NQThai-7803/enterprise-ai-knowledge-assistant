from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.chat.models import GroundingStatus
from app.core.config import Settings
from app.llm.models import LLMGenerationResult
from app.models import ChatMessage, ChatMessageRole, ChatSession, User, UserRole
from app.retrieval.models import HybridRetrievalHit, HybridRetrievalResult
from app.services.grounded_answer_service import GroundedAnswerService
from tests.integration.retrieval_helpers import create_user

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
    def __init__(
        self,
        result: HybridRetrievalResult | tuple[HybridRetrievalResult, ...],
    ) -> None:
        self.results = result if isinstance(result, tuple) else (result,)
        self.queries: list[str] = []

    async def retrieve(self, *, query: str, current_user: User, top_k: int | None = None):
        self.queries.append(query)
        index = min(len(self.queries) - 1, len(self.results) - 1)
        return self.results[index]


class FakeLLMProvider:
    def __init__(self, result: LLMGenerationResult) -> None:
        self.result = result
        self.calls = 0
        self.messages = ()

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.calls += 1
        self.messages = messages
        return self.result


class FakeCitationValidationService:
    async def validate_and_map(self, *, answer: str, source_registry, current_user: User):  # noqa: ANN001
        return SimpleNamespace(
            answer=answer.replace("[SOURCE_1]", "[1]"),
            citations=(SimpleNamespace(citation_order=1),),
        )


class FakeCitationRepository:
    async def create_many(self, session: object, *, assistant_message: ChatMessage, citations):  # noqa: ANN001
        return tuple(citations)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        llm_enabled=True,
        llm_base_url="http://localhost:11434/v1",
        llm_model="fake-model",
        llm_retry_backoff_seconds=0.0,
        chat_context_max_tokens=1000,
        chat_retrieval_top_k=3,
        chat_history_max_messages=10,
        chat_history_max_tokens=400,
        citation_max_sources_per_answer=3,
    )


def hit(text: str = "authorized retrieved context") -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        document_id=UUID("00000000-0000-0000-0000-000000000201"),
        document_title="Policy",
        chunk_index=0,
        text=text,
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=4,
        hybrid_score=1.0,
        semantic_score=0.9,
        semantic_rank=1,
        keyword_score=None,
        keyword_rank=None,
        matched_by=("semantic",),
    )


def retrieval_result(*hits: HybridRetrievalHit) -> HybridRetrievalResult:
    return HybridRetrievalResult(
        hits=hits,
        hit_count=len(hits),
        requested_top_k=3,
        semantic_candidate_count=len(hits),
        keyword_candidate_count=0,
        fused_candidate_count=len(hits),
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )


def llm_answer(
    content: str = '{"answer":"Grounded answer","citations":["SOURCE_1"]}',
) -> LLMGenerationResult:
    return LLMGenerationResult(
        content=content,
        model="fake-model",
        finish_reason="stop",
        prompt_tokens=10,
        completion_tokens=4,
        response_time_ms=42,
    )


async def create_chat_session(session: AsyncSession, owner: User) -> ChatSession:
    now = datetime.now(UTC)
    chat = ChatSession(user_id=owner.id, title="Memory", created_at=now, updated_at=now)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def create_message(
    session: AsyncSession,
    *,
    chat: ChatSession,
    role: ChatMessageRole,
    content: str,
    seconds: int,
) -> ChatMessage:
    message = ChatMessage(
        session_id=chat.id,
        role=role,
        content=content,
        created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds),
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


def make_service(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    retrieval: FakeRetrievalService,
    llm: FakeLLMProvider,
) -> GroundedAnswerService:
    return GroundedAnswerService(
        settings=settings(),
        session_provider=session_factory,
        hybrid_retrieval_service=retrieval,
        llm_provider_factory=lambda: llm,
        token_counter=FakeCounter(),
        citation_repository=FakeCitationRepository(),
        citation_validation_service=FakeCitationValidationService(),
    )


@pytest.mark.parametrize(
    ("prior_user", "prior_assistant", "follow_up", "expected_query"),
    [
        (
            "Leave policy?",
            "Employees get 12 annual leave days.",
            "If working 5 years then what?",
            "Leave policy If working 5 years then what?",
        ),
        (
            "Working policy?",
            "08:00-17:00 working hours.",
            "Does it apply on Saturday?",
            "Working policy - Does it apply on Saturday?",
        ),
    ],
)
def test_follow_up_questions_use_resolved_user_history_query(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    prior_user: str,
    prior_assistant: str,
    follow_up: str,
    expected_query: str,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "memory-owner", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
            await create_message(
                session,
                chat=chat,
                role=ChatMessageRole.USER,
                content=prior_user,
                seconds=1,
            )
            await create_message(
                session,
                chat=chat,
                role=ChatMessageRole.ASSISTANT,
                content=prior_assistant,
                seconds=2,
            )
        retrieval = FakeRetrievalService(retrieval_result(hit()))
        llm = FakeLLMProvider(llm_answer())
        service = make_service(async_session_factory_for_tests, retrieval=retrieval, llm=llm)

        result = await service.answer_question(
            current_user=owner,
            session_id=chat.id,
            question=follow_up,
        )

        assert result.grounding_status == GroundingStatus.ANSWERED
        assert llm.calls == 1
        assert retrieval.queries == [expected_query]
        assert "<conversation_history>\n</conversation_history>" in llm.messages[1].content
        assert prior_assistant not in llm.messages[1].content
        assert expected_query in llm.messages[1].content

    run_async(scenario())


@pytest.mark.parametrize(
    ("prior_user", "follow_up", "expected_query"),
    [
        (
            "Who is the CEO?",
            "Does he appear in another document?",
            ("Who is the CEO?", "Does he appear"),
        ),
        (
            "Travel Approval?",
            "Are there exceptions?",
            ("Travel Approval?", "exceptions"),
        ),
    ],
)
def test_follow_up_after_no_answer_does_not_hallucinate_without_retrieved_context(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    prior_user: str,
    follow_up: str,
    expected_query: str,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "memory-no-answer-owner", role=UserRole.STAFF)
            chat = await create_chat_session(session, owner)
            await create_message(
                session,
                chat=chat,
                role=ChatMessageRole.USER,
                content=prior_user,
                seconds=1,
            )
            await create_message(
                session,
                chat=chat,
                role=ChatMessageRole.ASSISTANT,
                content="No answer available.",
                seconds=2,
            )
        retrieval = FakeRetrievalService(retrieval_result())
        llm = FakeLLMProvider(
            llm_answer('{"answer":"This must not be used","citations":["SOURCE_1"]}')
        )
        service = make_service(async_session_factory_for_tests, retrieval=retrieval, llm=llm)

        result = await service.answer_question(
            current_user=owner,
            session_id=chat.id,
            question=follow_up,
        )

        assert retrieval.queries == [expected_query]
        assert llm.calls == 0
        assert result.grounding_status == GroundingStatus.NO_ANSWER

    run_async(scenario())
