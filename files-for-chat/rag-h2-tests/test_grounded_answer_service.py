from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import replace
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
    LLMProviderTimeoutStandardApplicationError,
    LLMTimeoutApplicationError,
)
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMGenerationResult
from app.models import AuditLog, ChatMessage, ChatMessageRole, ChatSession, User, UserRole
from app.repositories.chat_message_repository import ConversationMemoryMessageRow
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.models import HybridRetrievalHit, HybridRetrievalResult
from app.services.grounded_answer_service import (
    GroundedAnswerService,
    _person_name_sequences_near_terms,
    _rank_hits_for_prompt,
)
from app.web_search.errors import WebSearchError, WebSearchFailureCode
from app.web_search.models import WebSearchResult, WebSearchResults


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
        "chat_history_max_tokens": 200,
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


def memory_row(index: int, role: ChatMessageRole, content: str) -> ConversationMemoryMessageRow:
    return ConversationMemoryMessageRow(
        id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
        role=role,
        content=content,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
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
    def __init__(self, history: tuple[ConversationMemoryMessageRow, ...] = ()) -> None:
        self.history = history
        self.history_calls = 0
        self.memory_calls = 0
        self.memory_call_args: list[dict[str, object]] = []

    async def list_recent_visible_owned_messages(
        self, session: object, *, session_id: UUID, owner_user_id: UUID, limit: int
    ):
        self.history_calls += 1
        return ()

    async def list_owned_messages_for_memory(
        self, session: object, *, session_id: UUID, owner_user_id: UUID
    ):
        self.memory_calls += 1
        self.memory_call_args.append(
            {
                "session": session,
                "session_id": session_id,
                "owner_user_id": owner_user_id,
            }
        )
        return self.history


class FakeRetrievalService:
    def __init__(
        self,
        result: HybridRetrievalResult | Exception | tuple[HybridRetrievalResult, ...],
    ) -> None:
        self.results = result if isinstance(result, tuple) else (result,)
        self.calls = 0
        self.users: list[User] = []
        self.queries: list[str] = []
        self.top_ks: list[int | None] = []

    async def retrieve(self, *, query: str, current_user: User, top_k: int | None = None):
        self.calls += 1
        self.users.append(current_user)
        self.queries.append(query)
        self.top_ks.append(top_k)
        index = min(self.calls - 1, len(self.results) - 1)
        result = self.results[index]
        if isinstance(result, Exception):
            raise result
        return result


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


class SequentialFakeLLMProvider(FakeLLMProvider):
    def __init__(self, *results: LLMGenerationResult | Exception) -> None:
        if not results:
            raise ValueError("at least one result is required")
        super().__init__(results[0])
        self.results = results
        self.message_history: list[object] = []

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.calls += 1
        self.messages = messages
        self.message_history.append(messages)
        result = self.results[min(self.calls - 1, len(self.results) - 1)]
        if isinstance(result, Exception):
            raise result
        return result


class SlowCancellableLLMProvider(FakeLLMProvider):
    def __init__(self) -> None:
        super().__init__(
            LLMGenerationResult(
                content='{"answer":"Grounded answer","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=11,
                completion_tokens=5,
                response_time_ms=123,
            )
        )
        self.started = asyncio.Event()
        self.cancelled = False

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.calls += 1
        self.messages = messages
        self.started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
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
    def __init__(self, *, citations: tuple[object, ...] | None = None) -> None:
        self.calls = 0
        self.citations = (
            citations if citations is not None else (SimpleNamespace(citation_order=1),)
        )
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


class FakeWebSearchService:
    def __init__(self, result: WebSearchResults | Exception) -> None:
        self.result = result
        self.queries: list[str] = []

    async def search(self, *, query: str):
        self.queries.append(query)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def web_result(text: str = "web context") -> WebSearchResult:
    return WebSearchResult(
        title="Microsoft Learn",
        url="https://learn.microsoft.com/en-us/azure/ai-services/",
        snippet=text,
        content=text,
        provider="mock",
        rank=1,
        score=1.0,
    )


def web_results(text: str = "web context") -> WebSearchResults:
    return WebSearchResults(
        query="question",
        provider="mock",
        results=(web_result(text),),
        requested_max_results=1,
    )


def make_service(
    *,
    session_repository: FakeSessionRepository | None = None,
    message_repository: FakeMessageRepository | None = None,
    retrieval: FakeRetrievalService | None = None,
    llm: FakeLLMProvider | None = None,
    counter: FakeCounter | None = None,
    citation_validation: FakeCitationValidationService | None = None,
    citation_repository: FakeCitationRepository | None = None,
    settings_obj: Settings | None = None,
    web_search_service: FakeWebSearchService | None = None,
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
            content='{"answer":"Grounded answer","citations":["SOURCE_1"]}',
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
        settings=settings_obj or settings(),
        session_provider=FakeSessionProvider(),
        hybrid_retrieval_service=resolved_retrieval,
        llm_provider_factory=lambda: resolved_llm,
        token_counter=counter or FakeCounter(),
        session_repository=resolved_session_repository,
        message_repository=resolved_message_repository,
        citation_repository=resolved_citation_repository,
        message_service=message_service,
        citation_validation_service=citation_validation or FakeCitationValidationService(),
        web_search_service=web_search_service,
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
        assert message_repo.memory_calls == 0
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


def test_context_dependent_question_uses_resolved_retrieval_query() -> None:
    async def scenario() -> None:
        message_repo = FakeMessageRepository(
            history=(
                memory_row(1, ChatMessageRole.USER, "Leave policy?"),
                memory_row(2, ChatMessageRole.ASSISTANT, "Employees get 12 annual leave days."),
            )
        )
        service, _, _, retrieval, _, _, _ = make_service(
            message_repository=message_repo,
            retrieval=FakeRetrievalService(retrieval_result(hit())),
        )

        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="If working 5 years then what?",
        )

        assert retrieval.queries == ["Leave policy If working 5 years then what?"]
        assert "12 annual leave days" not in retrieval.queries[0]
        assert retrieval.top_ks == [2]
        assert message_repo.memory_call_args[0]["session_id"] == chat_session().id
        assert message_repo.memory_call_args[0]["owner_user_id"] == user().id

    run_async(scenario())


def test_current_question_hit_does_not_inherit_unrelated_ceo_history() -> None:
    async def scenario() -> None:
        message_repo = FakeMessageRepository(
            history=(
                memory_row(1, ChatMessageRole.USER, "CEO Nova Digital la ai?"),
                memory_row(2, ChatMessageRole.ASSISTANT, "Nguyen Anh Khoa la CEO."),
            )
        )
        service, _, _, retrieval, _, _, _ = make_service(message_repository=message_repo)

        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Nguoi lao dong duoc nghi hang nam bao nhieu ngay?",
        )

        assert retrieval.queries == ["Nguoi lao dong duoc nghi hang nam bao nhieu ngay?"]

    run_async(scenario())


def test_entity_follow_up_prompt_uses_new_role_without_assistant_answer() -> None:
    async def scenario() -> None:
        message_repo = FakeMessageRepository(
            history=(
                memory_row(1, ChatMessageRole.USER, "CEO Nova Digital la ai?"),
                memory_row(2, ChatMessageRole.ASSISTANT, "Nguyen Anh Khoa [1]"),
            )
        )
        service, _, _, retrieval, llm, _, _ = make_service(
            message_repository=message_repo,
            retrieval=FakeRetrievalService(
                retrieval_result(hit("CTO source evidence for Nova Digital"))
            ),
        )

        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Con CTO thi sao?",
        )

        assert retrieval.queries == ["CTO Nova Digital la ai?"]
        user_prompt = llm.messages[1].content
        assert "CTO Nova Digital la ai?" in user_prompt
        assert "CEO Nova Digital" not in user_prompt
        assert "Nguyen Anh Khoa" not in user_prompt

    run_async(scenario())


def test_policy_follow_up_uses_resolved_five_year_grounding_question() -> None:
    async def scenario() -> None:
        message_repo = FakeMessageRepository(
            history=(
                memory_row(1, ChatMessageRole.USER, "Nghi hang nam bao nhieu ngay?"),
                memory_row(2, ChatMessageRole.ASSISTANT, "12 ngay [1]"),
            )
        )
        service, _, _, retrieval, llm, _, _ = make_service(
            message_repository=message_repo,
            retrieval=FakeRetrievalService(retrieval_result(hit("5-year source evidence"))),
        )

        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Con sau 5 nam thi sao?",
        )

        query = retrieval.queries[0]
        assert "Nghi hang nam" in query
        assert "5 nam" in query
        assert "12 ngay" not in query
        assert "bao nhieu" not in query
        user_prompt = llm.messages[1].content
        assert query in user_prompt
        assert "12 ngay" not in user_prompt

    run_async(scenario())


def test_empty_conversation_memory_uses_current_question_for_retrieval() -> None:
    async def scenario() -> None:
        service, _, _, retrieval, _, _, _ = make_service()

        await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Current question"
        )

        assert retrieval.queries == ["Current question"]

    run_async(scenario())


def test_llm_prompt_excludes_assistant_history_and_contains_retrieved_context() -> None:
    async def scenario() -> None:
        message_repo = FakeMessageRepository(
            history=(
                memory_row(1, ChatMessageRole.USER, "Working policy?"),
                memory_row(2, ChatMessageRole.ASSISTANT, "08:00-17:00 schedule."),
            )
        )
        service, _, _, retrieval, llm, _, _ = make_service(message_repository=message_repo)

        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Does it apply on Saturday?",
        )

        assert retrieval.queries == ["Working policy - Does it apply on Saturday?"]
        assert [message.role for message in llm.messages[:2]] == ["system", "user"]
        user_prompt = llm.messages[1].content
        assert "<conversation_history>\n</conversation_history>" in user_prompt
        assert "--- CONVERSATION MESSAGE" not in user_prompt
        assert "08:00-17:00 schedule." not in user_prompt
        assert "<retrieved_context>" in user_prompt
        assert "allowed context" in user_prompt
        assert "Working policy - Does it apply on Saturday?" in user_prompt
        assert "Working policy" not in llm.messages[0].content

    run_async(scenario())


def test_follow_up_after_no_answer_does_not_hallucinate_without_retrieved_context() -> None:
    async def scenario() -> None:
        message_repo = FakeMessageRepository(
            history=(
                memory_row(1, ChatMessageRole.USER, "Who is the CEO?"),
                memory_row(2, ChatMessageRole.ASSISTANT, "No answer available."),
            )
        )
        service, _, _, retrieval, llm, _, _ = make_service(
            message_repository=message_repo,
            retrieval=FakeRetrievalService(retrieval_result()),
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Does he appear in another document?",
        )

        assert retrieval.queries == ["Does the CEO appear in another document?"]
        assert llm.calls == 0
        assert result.grounding_status == GroundingStatus.NO_ANSWER

    run_async(scenario())


def test_reason_question_without_causal_evidence_returns_no_answer_before_llm() -> None:
    async def scenario() -> None:
        llm = FakeLLMProvider(
            LLMGenerationResult(
                content='{"answer":"Unsupported reason","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            )
        )
        service, _, _, retrieval, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(retrieval_result(hit("Nguyen is listed as CEO."))),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Why was Nguyen chosen as CEO?",
        )

        assert retrieval.calls == 1
        assert resolved_llm.calls == 0
        assert result.grounding_status == GroundingStatus.NO_ANSWER

    run_async(scenario())


def test_person_role_candidate_prefers_previous_record_name() -> None:
    text = (
        "Alice Minh Nguyen - accountable for company results and operations\n"
        "Chief Executive Officer (CEO)\n"
        "Bob Thu Tran - accountable for technology platforms\n"
        "Chief Technology Officer (CTO)\n"
    )

    assert _person_name_sequences_near_terms(text, ("CEO",)) == ("Alice Minh Nguyen",)
    assert _person_name_sequences_near_terms(text, ("CTO",)) == ("Bob Thu Tran",)


def test_person_role_extraction_ignores_committee_name_false_positive() -> None:
    text = "Hoi dong Kien truc Cong nghe\nCTO chu tri va phe duyet nguyen tac kien truc cong nghe."

    assert _person_name_sequences_near_terms(text, ("CTO",)) == ()


def test_prompt_reranking_keeps_numeric_condition_hit_first() -> None:
    topic_only_hit = replace(
        hit(
            "Nguoi lao dong lam viec trong dieu kien binh thuong duoc nghi hang nam "
            "va cac quy dinh ve ngay nghi hang nam thay doi theo chinh sach."
        ),
        chunk_id=UUID("00000000-0000-0000-0000-000000000111"),
        chunk_index=4,
    )
    conditioned_hit = replace(
        hit(
            "Cu du 05 nam lam viec cho cung mot nguoi su dung lao dong thi so ngay "
            "nghi hang nam duoc tang them 01 ngay."
        ),
        chunk_id=UUID("00000000-0000-0000-0000-000000000112"),
        chunk_index=5,
    )

    ranked = _rank_hits_for_prompt(
        (topic_only_hit, conditioned_hit),
        question="Nghi hang nam sau 5 nam thay doi nhu the nao?",
    )

    assert ranked[0].chunk_index == 5


def test_prompt_reranking_prefers_distinct_product_name_over_generic_usage_terms() -> None:
    generic_usage_hit = replace(
        hit(
            "Chinh sach lam viec duoc ap dung tu nam 2026 va dung cho cac quy trinh "
            "lam viec noi bo."
        ),
        chunk_id=UUID("00000000-0000-0000-0000-000000000113"),
        chunk_index=1,
    )
    product_hit = replace(
        hit(
            "AtlasSearch\nVai tro: Tro ly tim kiem tri thuc noi bo. Mo ta: tra cuu "
            "tai lieu co trich dan va kiem tra phan quyen."
        ),
        chunk_id=UUID("00000000-0000-0000-0000-000000000114"),
        chunk_index=2,
    )

    ranked = _rank_hits_for_prompt(
        (generic_usage_hit, product_hit),
        question="AtlasSearch dung de lam gi?",
    )

    assert ranked[0].chunk_index == 2


def test_prompt_reranking_prefers_requested_role_over_proposed_person_role() -> None:
    proposed_person_role_hit = replace(
        hit("Le Thu Ha - Chief Technology Officer (CTO) of Example Digital."),
        chunk_id=UUID("00000000-0000-0000-0000-000000000115"),
        chunk_index=3,
    )
    requested_role_hit = replace(
        hit("Nguyen Anh Khoa - Chief Executive Officer (CEO) of Example Digital."),
        chunk_id=UUID("00000000-0000-0000-0000-000000000116"),
        chunk_index=4,
    )

    ranked = _rank_hits_for_prompt(
        (proposed_person_role_hit, requested_role_hit),
        question="CEO Example Digital la Le Thu Ha dung khong?",
    )

    assert ranked[0].chunk_index == 4


def test_product_purpose_no_answer_retries_on_distinct_product_evidence() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content="__NO_ANSWER__",
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content=(
                    '{"answer":"AtlasSearch is an internal knowledge search assistant.",'
                    '"citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(
                    hit(
                        "AtlasSearch\nRole: internal knowledge search assistant. "
                        "Description: retrieves governed documents with citations."
                    )
                )
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="AtlasSearch dung de lam gi?",
        )

        assert resolved_llm.calls == 2
        assert result.grounding_status == GroundingStatus.ANSWERED
        assert "AtlasSearch" in result.assistant_message.content

    run_async(scenario())


def test_false_premise_multi_rule_question_retries_and_corrects() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content="__NO_ANSWER__",
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content=(
                    '{"answer":"No. The source states 12 days for the base condition, '
                    "14 days for protected or hazardous categories, and 16 days for the "
                    'special category.","citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(
                    hit(
                        "Annual leave rules: 12 days for the base condition; 14 days for "
                        "protected or hazardous categories; 16 days for the special category."
                    )
                )
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Does every employee receive 12 annual leave days?",
        )

        assert resolved_llm.calls == 2
        assert result.grounding_status == GroundingStatus.ANSWERED
        assert result.assistant_message.content.startswith("No.")

    run_async(scenario())


def test_yes_no_answer_without_polarity_retries() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content=(
                    '{"answer":"CEO Nova Digital la Nguyen Anh Khoa","citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content=(
                    '{"answer":"Khong, CEO Nova Digital la Nguyen Anh Khoa",'
                    '"citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, _, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(
                    hit("CEO Nova Digital la Nguyen Anh Khoa. CTO Nova Digital la Le Thu Ha.")
                )
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="CEO Nova Digital la Le Thu Ha dung khong?",
        )

        assert llm.calls == 2
        assert result.assistant_message.content.startswith("Khong")
        assert "Nguyen Anh Khoa" in result.assistant_message.content

    run_async(scenario())


def test_open_person_negative_polarity_answer_retries() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content=('{"answer":"Khong Nguyen Anh Khoa la CEO","citations":["SOURCE_1"]}'),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content=('{"answer":"CEO la Nguyen Anh Khoa.","citations":["SOURCE_1"]}'),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, _, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(hit("Nguyen Anh Khoa - Tong Giam doc (CEO) of Example Digital."))
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="CEO Example Digital la ai?",
        )

        assert llm.calls == 2
        assert result.grounding_status == GroundingStatus.ANSWERED
        assert result.assistant_message.content.startswith("CEO la Nguyen Anh Khoa")

    run_async(scenario())


def test_absent_named_entity_role_question_skips_llm() -> None:
    async def scenario() -> None:
        llm = FakeLLMProvider(
            LLMGenerationResult(
                content='{"answer":"CEO la Nguyen Anh Khoa.","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            )
        )
        service, _, _, retrieval, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(hit("Nguyen Anh Khoa - Tong Giam doc (CEO) cua Nova Digital."))
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="CEO Apple la ai?",
        )

        assert retrieval.calls == 1
        assert resolved_llm.calls == 0
        assert result.grounding_status == GroundingStatus.NO_ANSWER

    run_async(scenario())


def test_incomplete_person_answer_retries_without_auto_selecting_source() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content=(
                    '{"answer":"The CTO is Technology Strategy Office.","citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content='{"answer":"The CTO is Le Thu Ha.","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(
                    hit("The CTO of Nova Digital is Le Thu Ha and manages technology.")
                )
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="CTO Nova Digital la ai?",
        )

        assert resolved_llm.calls == 2
        assert "Le Thu Ha" in result.assistant_message.content
        assert result.grounding_status == GroundingStatus.ANSWERED

    run_async(scenario())


def test_numeric_answer_missing_source_unit_retries() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content='{"answer":"The standard work week is 40.","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content='{"answer":"The standard work week is 40 hours.","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(hit("The standard work week is 40 hours."))
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="How many hours is the standard work week?",
        )

        assert resolved_llm.calls == 2
        assert "40 hours" in result.assistant_message.content
        assert result.grounding_status == GroundingStatus.ANSWERED

    run_async(scenario())


def test_negated_qualifier_quantity_answer_is_not_retried() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content=(
                    '{"answer":"Nguoi lao dong lam cong viec nang nhoc, doc hai, nguy '
                    'hiem nhung khong thuoc loai dac biet thi duoc nghi 14 ngay.",'
                    '"citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content="__NO_ANSWER__",
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        source_text = (
            "12 ngay Cong viec trong dieu kien binh thuong. "
            "Nguoi chua thanh nien hoac cong viec nang nhoc, doc hai, nguy hiem "
            "theo danh muc phap luat: 14 ngay. "
            "16 ngay Cong viec dac biet nang nhoc, doc hai, nguy hiem."
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(retrieval_result(hit(source_text))),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question=(
                "Nguoi lao dong lam cong viec nang nhoc, doc hai, nguy hiem nhung "
                "khong thuoc loai dac biet thi duoc nghi hang nam bao nhieu ngay?"
            ),
        )

        assert resolved_llm.calls == 1
        assert result.grounding_status == GroundingStatus.ANSWERED
        assert "14 ngay" in result.assistant_message.content

    run_async(scenario())


def test_weekly_limit_quantity_answer_is_not_retried_for_daily_numbers() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content='{"answer":"48 gio/tuan","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content="__NO_ANSWER__",
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        source_text = (
            "Gio lam viec binh thuong khong vuot gioi han phap luat: "
            "thong thuong khong qua 08 gio/ngay va 48 gio/tuan; "
            "truong hop bo tri theo tuan co the khong qua 10 gio/ngay "
            "nhung van khong qua 48 gio/tuan."
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(retrieval_result(hit(source_text))),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Phap luat cho phep toi da bao nhieu gio trong mot tuan?",
        )

        assert resolved_llm.calls == 1
        assert result.grounding_status == GroundingStatus.ANSWERED
        assert "48 gio/tuan" in result.assistant_message.content

    run_async(scenario())


def test_quantity_answer_missing_source_number_retries() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content=('{"answer":"Employees receive 1 day.","citations":["SOURCE_1"]}'),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content=(
                    '{"answer":"Employees receive 12 days of annual leave.",'
                    '"citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(
                    hit("Employees in normal conditions receive 12 days. Seniority adds 1 day.")
                )
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="How many annual leave days do employees receive?",
        )

        assert resolved_llm.calls == 2
        assert "12 days" in result.assistant_message.content
        assert result.grounding_status == GroundingStatus.ANSWERED

    run_async(scenario())


def test_change_answer_missing_source_amount_retries() -> None:
    async def scenario() -> None:
        llm = SequentialFakeLLMProvider(
            LLMGenerationResult(
                content=(
                    '{"answer":"Annual leave changes under the stated condition.",'
                    '"citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
            LLMGenerationResult(
                content=(
                    '{"answer":"After 5 years, annual leave increases by 1 day.",'
                    '"citations":["SOURCE_1"]}'
                ),
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            ),
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            retrieval=FakeRetrievalService(
                retrieval_result(hit("After 5 years, annual leave increases by 1 day."))
            ),
            llm=llm,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="How does annual leave change after 5 years?",
        )

        assert resolved_llm.calls == 2
        assert "1 day" in result.assistant_message.content
        assert result.grounding_status == GroundingStatus.ANSWERED

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
            "citation_count": 1,
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
                content=f'{{"answer":"{marker}","citations":["SOURCE_1"]}}',
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
                content='{"answer":"Provider-independent answer","citations":["SOURCE_1"]}',
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


def test_answered_result_without_citations_returns_no_answer_safely() -> None:
    async def scenario() -> None:
        service, _, _, _, _, message_service, _ = make_service(
            citation_validation=FakeCitationValidationService(citations=())
        )

        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        assert result.grounding_status == GroundingStatus.NO_ANSWER
        assert result.assistant_message.content.strip()
        assert "Grounded answer" not in result.assistant_message.content
        assert [call["role"] for call in message_service.calls] == [
            ChatMessageRole.USER,
            ChatMessageRole.ASSISTANT,
        ]

    run_async(scenario())


@pytest.mark.parametrize(
    "content",
    [
        '{"answer":"Grounded answer"}',
        '{"answer":"","citations":["SOURCE_1"]}',
        '{"answer":"[SOURCE_1]","citations":["SOURCE_1"]}',
        '{"answer":"Grounded answer","citations":[]}',
        '{"answer":"<complete answer>","citations":["SOURCE_1"]}',
    ],
)
def test_invalid_structured_llm_output_returns_no_answer_safely(content: str) -> None:
    async def scenario() -> None:
        service, _, _, _, _, message_service, _ = make_service(
            llm=FakeLLMProvider(
                LLMGenerationResult(
                    content=content,
                    model="fake",
                    finish_reason="stop",
                    prompt_tokens=1,
                    completion_tokens=1,
                    response_time_ms=1,
                )
            )
        )

        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        assert result.grounding_status == GroundingStatus.NO_ANSWER
        assert result.assistant_message.content.strip()
        assert content not in result.assistant_message.content
        assert [call["role"] for call in message_service.calls] == [
            ChatMessageRole.USER,
            ChatMessageRole.ASSISTANT,
        ]

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
                    content='{"answer":"Invented citation","citations":["SOURCE_999"]}',
                    model="fake",
                    finish_reason="stop",
                    prompt_tokens=1,
                    completion_tokens=1,
                    response_time_ms=1,
                )
            ),
            citation_validation=RejectingCitationValidationService(),
        )

        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

        assert result.grounding_status == GroundingStatus.NO_ANSWER
        assert "Invented citation" not in result.assistant_message.content
        assert [call["role"] for call in message_service.calls] == [
            ChatMessageRole.USER,
            ChatMessageRole.ASSISTANT,
        ]

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


def test_internal_only_does_not_call_web_search() -> None:
    async def scenario() -> None:
        web_search = FakeWebSearchService(web_results())
        service, _, _, _, _, _, _ = make_service(
            settings_obj=settings(
                web_search_enabled=True,
                web_search_mode="internal_only",
                web_search_provider="mock",
            ),
            web_search_service=web_search,
        )

        await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="latest policy"
        )

        assert web_search.queries == []

    run_async(scenario())


def test_hybrid_current_question_merges_internal_and_web_context() -> None:
    async def scenario() -> None:
        web_search = FakeWebSearchService(web_results("web docs context"))
        service, _, _, retrieval, llm, _, _ = make_service(
            settings_obj=settings(
                web_search_enabled=True,
                web_search_mode="hybrid",
                web_search_provider="mock",
            ),
            web_search_service=web_search,
        )

        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="latest Azure AI update",
        )

        assert retrieval.calls == 1
        assert web_search.queries == ["latest Azure AI update"]
        user_prompt = llm.messages[1].content
        assert "Document title: Document" in user_prompt
        assert "Source type: WEB" in user_prompt
        assert "web docs context" in user_prompt
        assert "https://learn.microsoft.com" not in user_prompt

    run_async(scenario())


def test_web_only_skips_internal_retrieval_and_uses_web_context() -> None:
    async def scenario() -> None:
        web_search = FakeWebSearchService(web_results("web-only context"))
        retrieval = FakeRetrievalService(
            RetrievalError(RetrievalFailureCode.HYBRID_RETRIEVAL_FAILED)
        )
        llm = FakeLLMProvider(
            LLMGenerationResult(
                content='{"answer":"Web answer","citations":["SOURCE_1"]}',
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            )
        )
        service, _, _, _, resolved_llm, _, _ = make_service(
            settings_obj=settings(
                web_search_enabled=True,
                web_search_mode="web_only",
                web_search_provider="mock",
            ),
            retrieval=retrieval,
            llm=llm,
            web_search_service=web_search,
        )

        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Search web"
        )

        assert retrieval.calls == 0
        assert web_search.queries == ["Search web"]
        assert "Source type: WEB" in resolved_llm.messages[1].content
        assert "Document title: Document" not in resolved_llm.messages[1].content
        assert result.grounding_status == GroundingStatus.ANSWERED

    run_async(scenario())


def test_hybrid_web_search_failure_falls_back_to_internal_context() -> None:
    async def scenario() -> None:
        web_search = FakeWebSearchService(
            WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_TIMEOUT)
        )
        service, _, _, _, llm, _, _ = make_service(
            settings_obj=settings(
                web_search_enabled=True,
                web_search_mode="hybrid",
                web_search_provider="mock",
            ),
            web_search_service=web_search,
        )

        result = await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="latest policy update",
        )

        assert web_search.queries == ["latest policy update"]
        assert "Document title: Document" in llm.messages[1].content
        assert "Source type: WEB" not in llm.messages[1].content
        assert result.grounding_status == GroundingStatus.ANSWERED

    run_async(scenario())


def test_web_only_provider_failure_returns_no_answer_without_llm() -> None:
    async def scenario() -> None:
        web_search = FakeWebSearchService(
            WebSearchError(WebSearchFailureCode.WEB_SEARCH_PROVIDER_UNAVAILABLE)
        )
        service, _, _, retrieval, llm, _, _ = make_service(
            settings_obj=settings(
                web_search_enabled=True,
                web_search_mode="web_only",
                web_search_provider="mock",
            ),
            web_search_service=web_search,
        )

        result = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Search web"
        )

        assert retrieval.calls == 0
        assert llm.calls == 0
        assert result.grounding_status == GroundingStatus.NO_ANSWER

    run_async(scenario())


def test_web_search_query_uses_current_question_not_conversation_memory() -> None:
    async def scenario() -> None:
        message_repo = FakeMessageRepository(
            history=(
                memory_row(1, ChatMessageRole.USER, "CONFIDENTIAL_HISTORY"),
                memory_row(2, ChatMessageRole.ASSISTANT, "CONFIDENTIAL_ANSWER"),
            )
        )
        web_search = FakeWebSearchService(web_results("web context"))
        service, _, _, retrieval, _, _, _ = make_service(
            message_repository=message_repo,
            retrieval=FakeRetrievalService(retrieval_result()),
            settings_obj=settings(
                web_search_enabled=True,
                web_search_mode="hybrid",
                web_search_provider="mock",
            ),
            web_search_service=web_search,
        )

        await service.answer_question(
            current_user=user(),
            session_id=chat_session().id,
            question="Current web question",
        )

        assert retrieval.queries[0] == "Current web question"
        assert web_search.queries == ["Current web question"]

    run_async(scenario())


def test_answer_question_cancellation_reaches_provider_and_persists_nothing() -> None:
    async def scenario() -> None:
        slow_provider = SlowCancellableLLMProvider()
        service, _, _, _, _, message_service, citation_repository = make_service(llm=slow_provider)
        task = asyncio.create_task(
            service.answer_question(
                current_user=user(),
                session_id=chat_session().id,
                question="Question",
            )
        )
        await asyncio.wait_for(slow_provider.started.wait(), timeout=1.0)

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert slow_provider.cancelled is True
        assert message_service.calls == []
        assert citation_repository.calls == []

    run_async(scenario())
