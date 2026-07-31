from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_grounded_answer_service
from app.core.config import Settings
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMGenerationResult
from app.models import ChatMessage, ChatSession, User, UserRole
from app.retrieval.models import HybridRetrievalHit, HybridRetrievalResult
from app.services.grounded_answer_service import GroundedAnswerService

pytestmark = pytest.mark.integration
CONFIDENTIAL_MARKER = "CONFIDENTIAL_GROUNDED_CHAT_MARKER"


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def create_chat_session_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner: User,
) -> ChatSession:
    async with session_factory() as session:
        now = datetime.now(UTC)
        chat = ChatSession(user_id=owner.id, title="Chat", created_at=now, updated_at=now)
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
        return chat


def create_session(
    session_factory: async_sessionmaker[AsyncSession], *, owner: User
) -> ChatSession:
    return run_async(create_chat_session_record(session_factory, owner=owner))


async def count_messages(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    chat_session: ChatSession,
) -> int:
    async with session_factory() as session:
        return (
            await session.scalar(
                select(func.count())
                .select_from(ChatMessage)
                .where(ChatMessage.session_id == chat_session.id)
            )
            or 0
        )


def make_settings(**overrides: object) -> Settings:
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


def hit(text: str = "authorized context") -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=uuid.UUID("00000000-0000-0000-0000-000000000101"),
        document_id=uuid.UUID("00000000-0000-0000-0000-000000000201"),
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
    def count(self, text: str) -> int:
        return len(text.split())

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens) -> str:  # noqa: ANN001
        return " ".join("x" for _ in tokens)


class FakeRetrievalService:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self.result = result
        self.calls = 0

    async def retrieve(self, *, query: str, current_user: User, top_k: int | None = None):
        self.calls += 1
        return self.result


class FakeLLMProvider:
    def __init__(self, result: LLMGenerationResult | Exception) -> None:
        self.result = result
        self.calls = 0

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeCitationValidationService:
    def __init__(self, *, citations: tuple[object, ...] = ()) -> None:
        self.citations = citations

    async def validate_and_map(self, *, answer: str, source_registry, current_user: User):  # noqa: ANN001
        return SimpleNamespace(
            answer=answer.replace("[SOURCE_1]", "[1]"),
            citations=self.citations,
        )


class FakeCitationRepository:
    async def create_many(self, session: object, *, assistant_message: ChatMessage, citations):  # noqa: ANN001
        return tuple(citations)


def llm_answer(content: str = "Grounded answer [SOURCE_1]") -> LLMGenerationResult:
    return LLMGenerationResult(
        content=content,
        model="fake",
        finish_reason="stop",
        prompt_tokens=4,
        completion_tokens=2,
        response_time_ms=99,
    )


def install_service(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    retrieval: FakeRetrievalService | None = None,
    llm: FakeLLMProvider | None = None,
    settings: Settings | None = None,
    citations: tuple[object, ...] = (),
) -> tuple[FakeRetrievalService, FakeLLMProvider]:
    resolved_retrieval = retrieval or FakeRetrievalService(retrieval_result(hit()))
    resolved_llm = llm or FakeLLMProvider(llm_answer())
    service = GroundedAnswerService(
        settings=settings or make_settings(),
        session_provider=session_factory,
        hybrid_retrieval_service=resolved_retrieval,
        llm_provider_factory=lambda: resolved_llm,
        token_counter=FakeCounter(),
        citation_repository=FakeCitationRepository(),
        citation_validation_service=FakeCitationValidationService(citations=citations),
    )
    api_client.app.dependency_overrides[get_grounded_answer_service] = lambda: service
    return resolved_retrieval, resolved_llm


def post_question(
    api_client: TestClient,
    make_auth_headers: Callable[[User], dict[str, str]],
    user: User,
    chat: ChatSession,
    payload: dict[str, object] | None = None,
):
    return api_client.post(
        f"/api/v1/chat/sessions/{chat.id}/messages",
        headers=make_auth_headers(user),
        json=payload or {"content": "Nhân viên được nghỉ phép bao nhiêu ngày?"},
    )


def test_owner_submits_question_returns_201(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(api_client, async_session_factory_for_tests)

    response = post_question(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["session_id"] == str(chat.id)
    assert data["grounding_status"] == "ANSWERED"
    assert data["retrieved_chunk_count"] == 1


def test_answered_response_returns_citations(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    document_id = uuid.UUID("00000000-0000-0000-0000-000000000901")
    chunk_id = uuid.UUID("00000000-0000-0000-0000-000000000902")
    citation = SimpleNamespace(
        document_id=document_id,
        document_title="Quy ch? nh?n s?",
        chunk_id=chunk_id,
        page_number=14,
        excerpt="Nh?n vi?n ch?nh th?c ???c h??ng 12 ng?y ngh? ph?p.",
        relevance_score=0.87,
        citation_order=1,
    )
    install_service(api_client, async_session_factory_for_tests, citations=(citation,))

    response = post_question(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["assistant_message"]["content"] == "Grounded answer [1]"
    assert "[SOURCE_1]" not in data["assistant_message"]["content"]
    assert data["user_message"]["citations"] == []
    assert data["assistant_message"]["citations"] == [
        {
            "document_id": str(document_id),
            "document_title": "Quy ch? nh?n s?",
            "chunk_id": str(chunk_id),
            "page_number": 14,
            "excerpt": "Nh?n vi?n ch?nh th?c ???c h??ng 12 ng?y ngh? ph?p.",
            "relevance_score": 0.87,
            "citation_order": 1,
        }
    ]
    serialized = response.text
    assert "storage_key" not in serialized
    assert "permission" not in serialized
    assert "access_scope" not in serialized
    assert "full_chunk" not in serialized


def test_staff_manager_admin_can_submit_to_own_session(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    for role in (UserRole.STAFF, UserRole.MANAGER, UserRole.ADMIN):
        user = make_user(role=role)
        chat = create_session(async_session_factory_for_tests, owner=user)
        install_service(api_client, async_session_factory_for_tests)
        response = post_question(api_client, make_auth_headers, user, chat)
        assert response.status_code == 201


def test_non_owner_and_admin_non_owner_receive_404_without_retrieval_or_llm(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    admin = make_user(role=UserRole.ADMIN)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    retrieval, llm = install_service(api_client, async_session_factory_for_tests)

    response = post_question(api_client, make_auth_headers, other, chat)
    admin_response = post_question(api_client, make_auth_headers, admin, chat)

    assert response.status_code == 404
    assert admin_response.status_code == 404
    assert response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"
    assert admin_response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"
    assert retrieval.calls == 0
    assert llm.calls == 0


def test_missing_session_receives_same_404(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)
    chat = ChatSession(id=uuid.uuid4(), user_id=user.id, is_archived=False)
    install_service(api_client, async_session_factory_for_tests)

    response = post_question(api_client, make_auth_headers, user, chat)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"


def test_unauthenticated_and_inactive_user_rejected(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    inactive = make_user(role=UserRole.STAFF, is_active=False)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(api_client, async_session_factory_for_tests)

    unauthenticated = api_client.post(
        f"/api/v1/chat/sessions/{chat.id}/messages", json={"content": "Q"}
    )
    inactive_response = post_question(api_client, make_auth_headers, inactive, chat)

    assert unauthenticated.status_code == 401
    assert inactive_response.status_code == 403


def test_invalid_question_payloads_are_rejected(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(api_client, async_session_factory_for_tests)

    invalid_payloads = [
        {"content": "   "},
        {"content": "x" * 12001},
        {"content": "Q", "role": "USER"},
        {"content": "Q", "model": "other"},
        {"content": "Q", "temperature": 1.0},
        {"content": "Q", "document_ids": [str(uuid.uuid4())]},
    ]
    for payload in invalid_payloads:
        response = post_question(api_client, make_auth_headers, owner, chat, payload)
        assert response.status_code == 422


def test_answer_response_excludes_out_of_scope_fields(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(api_client, async_session_factory_for_tests)

    response = post_question(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 201
    data = response.json()["data"]
    forbidden = {
        "sources",
        "document_ids",
        "chunk_ids",
        "page_numbers",
        "scores",
        "token_usage",
        "retrieval_query",
        "prompt",
    }
    assert forbidden.isdisjoint(data.keys())
    assert forbidden.isdisjoint(data["assistant_message"].keys())
    assert data["assistant_message"]["citations"] == []
    assert data["user_message"]["role"] == "USER"
    assert data["assistant_message"]["role"] == "ASSISTANT"


def test_empty_retrieval_returns_no_answer_and_does_not_call_llm(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    retrieval = FakeRetrievalService(retrieval_result())
    _, llm = install_service(api_client, async_session_factory_for_tests, retrieval=retrieval)

    response = post_question(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["grounding_status"] == "NO_ANSWER"
    assert llm.calls == 0
    assert run_async(count_messages(async_session_factory_for_tests, chat_session=chat)) == 2


def test_llm_sentinel_is_mapped_to_fixed_message(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(
        api_client,
        async_session_factory_for_tests,
        llm=FakeLLMProvider(llm_answer("__NO_ANSWER__")),
    )

    response = post_question(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["grounding_status"] == "NO_ANSWER"
    assert data["assistant_message"]["content"] != "__NO_ANSWER__"


def test_llm_disabled_returns_503_when_context_exists(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    retrieval = FakeRetrievalService(retrieval_result(hit()))
    service = GroundedAnswerService(
        settings=make_settings(llm_enabled=False),
        session_provider=async_session_factory_for_tests,
        hybrid_retrieval_service=retrieval,
        llm_provider_factory=lambda: (_ for _ in ()).throw(
            LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
        ),
        token_counter=FakeCounter(),
    )
    api_client.app.dependency_overrides[get_grounded_answer_service] = lambda: service

    response = post_question(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_NOT_CONFIGURED"
    assert run_async(count_messages(async_session_factory_for_tests, chat_session=chat)) == 0


def test_provider_errors_are_sanitized_and_persist_no_messages(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    secret = "SECRET_PROVIDER_ERROR_BODY"
    install_service(
        api_client,
        async_session_factory_for_tests,
        llm=FakeLLMProvider(LLMError(LLMFailureCode.LLM_AUTHENTICATION_FAILED, secret)),
    )

    response = post_question(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_AUTHENTICATION_FAILED"
    assert secret not in response.text
    assert run_async(count_messages(async_session_factory_for_tests, chat_session=chat)) == 0
