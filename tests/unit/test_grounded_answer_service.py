from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from app.chat.models import GroundingStatus
from app.core.config import Settings
from app.core.exceptions import (
    ChatRetrievalFailedError,
    ChatSessionNotFoundError,
    CitationValidationFailedApplicationError,
    LLMProviderTimeoutStandardApplicationError,
    LLMTimeoutApplicationError,
)
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMGenerationResult
from app.models import AuditLog, ChatMessage, ChatMessageRole, ChatSession, User, UserRole
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.models import HybridRetrievalHit, HybridRetrievalResult
from app.services.grounded_answer_service import GroundedAnswerService


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "llm_enabled": True,
        "llm_base_url": "http://localhost:11434/v1",
        "llm_model": "fake-model",
        "llm_retry_backoff_seconds": 0.0,
        "chat_context_max_tokens": 1000,
        "chat_retrieval_top_k": 2,
        "chat_history_max_messages": 2,
        "citation_max_sources_per_answer": 2,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def user() -> User:
    return User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="chat@example.com",
        full_name="Chat User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )


def chat_session() -> ChatSession:
    return ChatSession(
        id=UUID("00000000-0000-0000-0000-000000000010"),
        user_id=user().id,
        title="Session",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def hit(text: str = "allowed context") -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        document_id=UUID("00000000-0000-0000-0000-000000000201"),
        document_title="Document",
        chunk_index=0,
        text=text,
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=2,
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
        requested_top_k=2,
        semantic_candidate_count=len(hits),
        keyword_candidate_count=0,
        fused_candidate_count=len(hits),
        rrf_k=60,
        semantic_weight=1.0,
        keyword_weight=1.0,
    )


class FakeCounter:
    def __init__(self, *, huge: bool = False) -> None:
        self.huge = huge

    def count(self, text: str) -> int:
        if self.huge and ("CONTEXT ITEM" in text or "SOURCE_" in text):
            return 10_000
        return len(text.split())

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens) -> str:  # noqa: ANN001
        return " ".join("x" for _ in tokens)


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeSessionProvider:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self):  # noqa: ANN204
        provider = self

        class Context:
            async def __aenter__(self) -> FakeSession:
                session = FakeSession()
                provider.sessions.append(session)
                return session

            async def __aexit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
                return None

        return Context()


class FakeSessionRepository:
    def __init__(self, *, owned: bool = True, owned_for_update: bool = True) -> None:
        self.session = chat_session()
        self.owned = owned
        self.owned_for_update = owned_for_update
        self.get_calls = 0
        self.lock_calls = 0
        self.touched_at: datetime | None = None

    async def get_owned_by_id(self, session: object, *, session_id: UUID, owner_user_id: UUID):
        self.get_calls += 1
        return self.session if self.owned else None

    async def get_owned_by_id_for_update(
        self, session: object, *, session_id: UUID, owner_user_id: UUID
    ):
        self.lock_calls += 1
        return self.session if self.owned_for_update else None

    async def touch_updated_at(self, chat_session: ChatSession, *, updated_at: datetime) -> None:
        self.touched_at = updated_at
        chat_session.updated_at = updated_at


class FakeMessageRepository:
    def __init__(self) -> None:
        self.history_calls = 0

    async def list_recent_visible_owned_messages(
        self, session: object, *, session_id: UUID, owner_user_id: UUID, limit: int
    ):
        self.history_calls += 1
        return ()


class FakeRetrievalService:
    def __init__(self, result: HybridRetrievalResult | Exception) -> None:
        self.result = result
        self.calls = 0
        self.users: list[User] = []

    async def retrieve(self, *, query: str, current_user: User, top_k: int | None = None):
        self.calls += 1
        self.users.append(current_user)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeLLMProvider:
    def __init__(self, result: LLMGenerationResult | Exception) -> None:
        self.result = result
        self.calls = 0
        self.messages = None

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.calls += 1
        self.messages = messages
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeMessageService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def append_message(self, session: object, *, chat_session: ChatSession, **kwargs):
        self.calls.append(kwargs)
        return ChatMessage(
            id=UUID(f"00000000-0000-0000-0000-{len(self.calls):012d}"),
            session_id=chat_session.id,
            role=kwargs["role"],
            content=kwargs["content"],
            retrieval_query=kwargs["retrieval_query"],
            response_time_ms=kwargs["response_time_ms"],
            prompt_tokens=kwargs["prompt_tokens"],
            completion_tokens=kwargs["completion_tokens"],
            created_at=kwargs["created_at"],
        )


class FakeCitationValidationService:
    def __init__(self, *, citations: tuple[object, ...] = ()) -> None:
        self.calls = 0
        self.citations = citations
        self.answers: list[str] = []

    async def validate_and_map(self, *, answer: str, source_registry, current_user: User):  # noqa: ANN001
        self.calls += 1
        self.answers.append(answer)
        return SimpleNamespace(
            answer=answer.replace("[SOURCE_1]", "[1]"),
            citations=self.citations,
        )


class FakeCitationRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    async def create_many(self, session: object, *, assistant_message: ChatMessage, citations):  # noqa: ANN001
        self.calls.append(tuple(citations))
        return tuple(citations)


def make_service(
    *,
    session_repository: FakeSessionRepository | None = None,
    message_repository: FakeMessageRepository | None = None,
    retrieval: FakeRetrievalService | None = None,
    llm: FakeLLMProvider | None = None,
    counter: FakeCounter | None = None,
    citation_validation: FakeCitationValidationService | None = None,
    citation_repository: FakeCitationRepository | None = None,
) -> tuple[
    GroundedAnswerService,
    FakeSessionRepository,
    FakeMessageRepository,
    FakeRetrievalService,
    FakeLLMProvider,
    FakeMessageService,
    FakeCitationRepository,
]:
    resolved_retrieval = retrieval or FakeRetrievalService(retrieval_result(hit()))
    resolved_llm = llm or FakeLLMProvider(
        LLMGenerationResult(
            content="Grounded answer [SOURCE_1]",
            model="fake",
            finish_reason="stop",
            prompt_tokens=11,
            completion_tokens=5,
            response_time_ms=123,
        )
    )
    message_service = FakeMessageService()
    resolved_session_repository = session_repository or FakeSessionRepository()
    resolved_message_repository = message_repository or FakeMessageRepository()
    resolved_citation_repository = citation_repository or FakeCitationRepository()
    service = GroundedAnswerService(
        settings=settings(),
        session_provider=FakeSessionProvider(),
        hybrid_retrieval_service=resolved_retrieval,
        llm_provider_factory=lambda: resolved_llm,
        token_counter=counter or FakeCounter(),
        session_repository=resolved_session_repository,
        message_repository=resolved_message_repository,
        citation_repository=resolved_citation_repository,
        message_service=message_service,
        citation_validation_service=citation_validation or FakeCitationValidationService(),
    )
    return (
        service,
        resolved_session_repository,
        resolved_message_repository,
        resolved_retrieval,
        resolved_llm,
        message_service,
        resolved_citation_repository,
    )


def test_service_checks_ownership_before_retrieval() -> None:
    async def scenario() -> None:
        service, _, message_repo, retrieval, llm, message_service, _ = make_service(
            session_repository=FakeSessionRepository(owned=False)
        )
        with pytest.raises(ChatSessionNotFoundError):
            await service.answer_question(
                current_user=user(), session_id=chat_session().id, question="Question"
            )
        assert message_repo.history_calls == 0
        assert retrieval.calls == 0
        assert llm.calls == 0
        assert message_service.calls == []

    run_async(scenario())


def test_service_calls_hybrid_retrieval_once_and_uses_current_user() -> None:
    async def scenario() -> None:
        service, _, _, retrieval, _, _, _ = make_service()
        await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )
        assert retrieval.calls == 1
        assert [retrieved_user.id for retrieved_user in retrieval.users] == [user().id]

    run_async(scenario())


def test_no_hits_skips_llm_and_returns_fixed_no_answer() -> None:
    async def scenario() -> None:
        service, _, _, retrieval, llm, _, _ = make_service(
            retrieval=FakeRetrievalService(retrieval_result())
        )
        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )
        assert retrieval.calls == 1
        assert llm.calls == 0
        assert result.grounding_status == GroundingStatus.NO_ANSWER
        assert result.assistant_message.content.strip()
        assert result.assistant_message.content != "__NO_ANSWER__"

    run_async(scenario())


def test_no_context_budget_skips_llm() -> None:
    async def scenario() -> None:
        service, _, _, _, llm, _, _ = make_service(counter=FakeCounter(huge=True))
        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )
        assert llm.calls == 0
        assert result.grounding_status == GroundingStatus.NO_ANSWER

    run_async(scenario())


def test_context_calls_llm_once_and_answered_status() -> None:
    async def scenario() -> None:
        service, _, _, _, llm, _, _ = make_service()
        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )
        assert llm.calls == 1
        assert result.grounding_status == GroundingStatus.ANSWERED
        assert result.assistant_message.content == "Grounded answer [1]"

    run_async(scenario())


def test_llm_sentinel_returns_no_answer_status() -> None:
    async def scenario() -> None:
        llm = FakeLLMProvider(
            LLMGenerationResult(
                content="__NO_ANSWER__",
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            )
        )
        service, _, _, _, _, _, _ = make_service(llm=llm)
        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )
        assert result.grounding_status == GroundingStatus.NO_ANSWER
        assert result.assistant_message.content != "__NO_ANSWER__"

    run_async(scenario())


def test_service_does_not_return_context_chunks_or_embeddings() -> None:
    async def scenario() -> None:
        service, _, _, _, _, _, _ = make_service()
        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )
        assert not hasattr(result, "context")
        assert not hasattr(result, "embedding")

    run_async(scenario())


def test_llm_failure_persists_no_messages() -> None:
    async def scenario() -> None:
        service, _, _, _, _, message_service, _ = make_service(
            llm=FakeLLMProvider(LLMError(LLMFailureCode.LLM_TIMEOUT))
        )
        with pytest.raises(LLMTimeoutApplicationError):
            await service.answer_question(
                current_user=user(), session_id=chat_session().id, question="Question"
            )
        assert message_service.calls == []

    run_async(scenario())


def test_retrieval_failure_persists_no_messages() -> None:
    async def scenario() -> None:
        service, _, _, _, _, message_service, _ = make_service(
            retrieval=FakeRetrievalService(
                RetrievalError(RetrievalFailureCode.HYBRID_RETRIEVAL_FAILED)
            )
        )
        with pytest.raises(ChatRetrievalFailedError):
            await service.answer_question(
                current_user=user(), session_id=chat_session().id, question="Question"
            )
        assert message_service.calls == []

    run_async(scenario())


def test_success_persists_user_and_assistant_atomically_with_metrics() -> None:
    async def scenario() -> None:
        service, session_repo, _, _, _, message_service, _ = make_service()
        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="  Question  "
        )
        assert [call["role"] for call in message_service.calls] == [
            ChatMessageRole.USER,
            ChatMessageRole.ASSISTANT,
        ]
        user_call, assistant_call = message_service.calls
        assert user_call["content"] == "Question"
        assert user_call["retrieval_query"] is None
        assert user_call["prompt_tokens"] is None
        assert assistant_call["retrieval_query"] == "Question"
        assert assistant_call["response_time_ms"] == 123
        assert assistant_call["prompt_tokens"] == 11
        assert assistant_call["completion_tokens"] == 5
        assert user_call["created_at"] < assistant_call["created_at"]
        assert session_repo.touched_at == assistant_call["created_at"]
        assert result.retrieved_chunk_count == 1

    run_async(scenario())


def audit_logs_from(service: GroundedAnswerService) -> list[AuditLog]:
    return [
        item for item in service.session_provider.sessions[-1].added if isinstance(item, AuditLog)
    ]


def test_answered_chat_creates_safe_audit() -> None:
    async def scenario() -> None:
        service, _, _, _, _, _, _ = make_service()
        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="CONFIDENTIAL_AUDIT_QUESTION",
        )

        audit_logs = audit_logs_from(service)
        assert [audit_log.action for audit_log in audit_logs] == [
            "CHAT_QUESTION_SUBMITTED",
            "CHAT_ANSWER_GENERATED",
        ]
        assert all(audit_log.outcome == "SUCCESS" for audit_log in audit_logs)
        assert all(audit_log.user_id == user().id for audit_log in audit_logs)
        assert audit_logs[0].metadata_json == {"grounding_status": "ANSWERED"}
        assert audit_logs[1].metadata_json == {
            "grounding_status": "ANSWERED",
            "citation_count": 0,
        }

    run_async(scenario())


def test_no_answer_chat_creates_safe_audit() -> None:
    async def scenario() -> None:
        service, _, _, _, _, _, _ = make_service(retrieval=FakeRetrievalService(retrieval_result()))
        await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        audit_logs = audit_logs_from(service)
        assert [audit_log.action for audit_log in audit_logs] == [
            "CHAT_QUESTION_SUBMITTED",
            "CHAT_NO_ANSWER_GENERATED",
        ]
        assert audit_logs[0].metadata_json == {"grounding_status": "NO_ANSWER"}
        assert audit_logs[1].metadata_json == {
            "grounding_status": "NO_ANSWER",
            "citation_count": 0,
        }

    run_async(scenario())


@pytest.mark.parametrize(
    "marker",
    [
        "CONFIDENTIAL_AUDIT_QUESTION",
        "CONFIDENTIAL_AUDIT_ANSWER",
        "CONFIDENTIAL_AUDIT_PROMPT",
        "CONFIDENTIAL_AUDIT_CONTEXT",
        "CONFIDENTIAL_AUDIT_EXCERPT",
    ],
)
def test_chat_audit_has_no_sensitive_content(marker: str) -> None:
    async def scenario() -> None:
        llm = FakeLLMProvider(
            LLMGenerationResult(
                content=f"{marker} [SOURCE_1]",
                model="fake",
                finish_reason="stop",
                prompt_tokens=11,
                completion_tokens=5,
                response_time_ms=123,
            )
        )
        service, _, _, _, _, _, _ = make_service(llm=llm)
        await service.answer_question(
            current_user=user(), session_id=chat_session().id, question=marker
        )

        serialized = str(
            [
                {
                    "action": audit_log.action,
                    "entity_type": audit_log.entity_type,
                    "entity_id": str(audit_log.entity_id),
                    "metadata": audit_log.metadata_json,
                }
                for audit_log in audit_logs_from(service)
            ]
        )
        assert marker not in serialized

    run_async(scenario())


def test_chat_audit_records_grounding_status() -> None:
    async def scenario() -> None:
        service, _, _, _, _, _, _ = make_service()
        await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        assert {row.metadata_json["grounding_status"] for row in audit_logs_from(service)} == {
            "ANSWERED"
        }

    run_async(scenario())


def test_chat_audit_records_citation_count_only() -> None:
    async def scenario() -> None:
        citation_marker = "CONFIDENTIAL_AUDIT_EXCERPT"
        service, _, _, _, _, _, _ = make_service(
            citation_validation=FakeCitationValidationService(
                citations=(SimpleNamespace(excerpt=citation_marker),)
            )
        )
        await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        answer_audit = audit_logs_from(service)[1]
        assert answer_audit.metadata_json == {
            "grounding_status": "ANSWERED",
            "citation_count": 1,
        }
        assert citation_marker not in str(answer_audit.metadata_json)

    run_async(scenario())


def test_grounded_answer_is_provider_independent() -> None:
    async def scenario() -> None:
        llm = FakeLLMProvider(
            LLMGenerationResult(
                content="Provider-independent answer [SOURCE_1]",
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
                provider="gemini",
            )
        )
        service, _, _, _, _, _, _ = make_service(llm=llm)

        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        assert result.grounding_status == GroundingStatus.ANSWERED
        assert result.assistant_message.content == "Provider-independent answer [1]"

    run_async(scenario())


def test_provider_cannot_inject_unselected_citation() -> None:
    async def scenario() -> None:
        from app.citations.errors import CitationFailureCode, CitationValidationError

        class RejectingCitationValidationService:
            async def validate_and_map(self, *, answer: str, source_registry, current_user):  # noqa: ANN001
                raise CitationValidationError(CitationFailureCode.CITATION_MARKER_UNKNOWN)

        service, _, _, _, _, message_service, _ = make_service(
            llm=FakeLLMProvider(
                LLMGenerationResult(
                    content="Invented citation [SOURCE_999]",
                    model="fake",
                    finish_reason="stop",
                    prompt_tokens=1,
                    completion_tokens=1,
                    response_time_ms=1,
                )
            ),
            citation_validation=RejectingCitationValidationService(),
        )

        with pytest.raises(CitationValidationFailedApplicationError):
            await service.answer_question(
                current_user=user(), session_id=chat_session().id, question="Question"
            )
        assert message_service.calls == []

    run_async(scenario())


def test_no_answer_policy_remains_provider_independent() -> None:
    async def scenario() -> None:
        llm = FakeLLMProvider(
            LLMGenerationResult(
                content="__NO_ANSWER__",
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
                provider="anthropic",
            )
        )
        service, _, _, _, _, _, _ = make_service(llm=llm)

        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        assert result.grounding_status == GroundingStatus.NO_ANSWER
        assert result.assistant_message.content != "__NO_ANSWER__"

    run_async(scenario())


def test_provider_error_does_not_create_assistant_message() -> None:
    async def scenario() -> None:
        service, _, _, _, _, message_service, _ = make_service(
            llm=FakeLLMProvider(LLMError(LLMFailureCode.LLM_PROVIDER_TIMEOUT))
        )

        with pytest.raises(LLMProviderTimeoutStandardApplicationError):
            await service.answer_question(
                current_user=user(), session_id=chat_session().id, question="Question"
            )
        assert message_service.calls == []

    run_async(scenario())
