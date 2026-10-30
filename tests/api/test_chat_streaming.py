from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_grounded_answer_service
from app.core.config import Settings
from app.core.exceptions import RateLimitExceededError
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMGenerationResult
from app.models import (
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    CitationSourceType,
    MessageCitation,
    User,
    UserRole,
)
from app.retrieval.models import HybridRetrievalHit, HybridRetrievalResult
from app.services.chat_stream_service import ChatStreamService
from app.services.grounded_answer_service import GroundedAnswerService

pytestmark = [pytest.mark.integration, pytest.mark.streaming_chat_integration]


class FakeCounter:
    def count(self, text: str) -> int:
        return len(text.split())

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(range(self.count(text)))

    def decode(self, tokens: tuple[int, ...]) -> str:
        return " ".join("x" for _ in tokens)


class FakeRetrievalService:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self.result = result
        self.calls = 0
        self.queries: list[str] = []

    async def retrieve(self, *, query: str, current_user: User, top_k: int | None = None):
        self.calls += 1
        self.queries.append(query)
        return self.result


class FakeLLMProvider:
    def __init__(self, result: LLMGenerationResult | Exception) -> None:
        self.result = result
        self.calls = 0
        self.closed = False
        self.messages = None

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.calls += 1
        self.messages = messages
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def aclose(self) -> None:
        self.closed = True


class FakeCitationValidationService:
    def __init__(
        self,
        *,
        citations: tuple[object, ...] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.citations = citations
        self.error = error

    async def validate_and_map(self, *, answer: str, source_registry, current_user: User):  # noqa: ANN001
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            answer=answer.replace("[SOURCE_1]", "[1]"),
            citations=self.citations,
        )


class FakeCitationRepository:
    def __init__(self) -> None:
        self.calls = 0

    async def create_many(self, session: object, *, assistant_message: ChatMessage, citations):  # noqa: ANN001
        self.calls += 1
        return tuple(citations)


class ConnectedRequest:
    async def is_disconnected(self) -> bool:
        await asyncio.sleep(0)
        return False


class DisconnectingRequest:
    async def is_disconnected(self) -> bool:
        await asyncio.sleep(0)
        return True


class SlowAnswerService:
    def __init__(self) -> None:
        self.cancelled = False
        self.settings = make_settings(llm_stream_heartbeat_seconds=0.01)

    async def answer_question(self, **kwargs: object):
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.cancelled = True
            raise


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


async def create_chat_message_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    chat_session: ChatSession,
    role: ChatMessageRole,
    content: str,
    seconds: int,
) -> ChatMessage:
    async with session_factory() as session:
        message = ChatMessage(
            session_id=chat_session.id,
            role=role,
            content=content,
            created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds),
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message


def create_message(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    chat_session: ChatSession,
    role: ChatMessageRole,
    content: str,
    seconds: int,
) -> ChatMessage:
    return run_async(
        create_chat_message_record(
            session_factory,
            chat_session=chat_session,
            role=role,
            content=content,
            seconds=seconds,
        )
    )


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
        "llm_stream_heartbeat_seconds": 15.0,
        "llm_stream_max_duration_seconds": 120.0,
        "chat_context_max_tokens": 1000,
        "chat_retrieval_top_k": 2,
        "chat_history_max_messages": 2,
        "chat_history_max_tokens": 200,
        "citation_max_sources_per_answer": 2,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


# Context and answer agree, so the real claim validation keeps the ANSWERED path.
GROUNDED_CONTEXT = "Nhân viên được nghỉ 12 ngày phép năm."
GROUNDED_ANSWER_JSON = '{"answer":"Nhân viên được nghỉ 12 ngày phép năm.","citations":["SOURCE_1"]}'
GROUNDED_ANSWER_DISPLAY = "Nhân viên được nghỉ 12 ngày phép năm. [1]"


def hit(text: str = GROUNDED_CONTEXT) -> HybridRetrievalHit:
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


def llm_answer(
    content: str = GROUNDED_ANSWER_JSON,
) -> LLMGenerationResult:
    return LLMGenerationResult(
        content=content,
        model="fake-model",
        finish_reason="stop",
        prompt_tokens=4,
        completion_tokens=2,
        response_time_ms=99,
        provider="openai_compatible",
    )


def default_citation() -> SimpleNamespace:
    return SimpleNamespace(
        document_id=uuid.UUID("00000000-0000-0000-0000-000000000901"),
        document_title="Quy che nhan su",
        chunk_id=uuid.UUID("00000000-0000-0000-0000-000000000902"),
        page_number=14,
        excerpt="Nhan vien chinh thuc duoc huong 12 ngay nghi phep.",
        relevance_score=0.87,
        citation_order=1,
    )


def install_service(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    retrieval: FakeRetrievalService | None = None,
    llm: FakeLLMProvider | None = None,
    settings: Settings | None = None,
    citations: tuple[object, ...] | None = None,
    citation_error: Exception | None = None,
    citation_repository: FakeCitationRepository | None = None,
) -> tuple[FakeRetrievalService, FakeLLMProvider]:
    resolved_retrieval = retrieval or FakeRetrievalService(retrieval_result(hit()))
    resolved_llm = llm or FakeLLMProvider(llm_answer())
    service = GroundedAnswerService(
        settings=settings or make_settings(),
        session_provider=session_factory,
        hybrid_retrieval_service=resolved_retrieval,
        llm_provider_factory=lambda: resolved_llm,
        token_counter=FakeCounter(),
        citation_repository=citation_repository or FakeCitationRepository(),
        citation_validation_service=FakeCitationValidationService(
            citations=citations if citations is not None else (default_citation(),),
            error=citation_error,
        ),
    )
    api_client.app.dependency_overrides[get_grounded_answer_service] = lambda: service
    return resolved_retrieval, resolved_llm


def post_stream(
    api_client: TestClient,
    make_auth_headers: Callable[[User], dict[str, str]],
    user: User,
    chat: ChatSession,
    payload: dict[str, object] | None = None,
):
    headers = make_auth_headers(user)
    headers["Accept"] = "text/event-stream"
    return api_client.post(
        f"/api/v1/chat/sessions/{chat.id}/messages/stream",
        headers=headers,
        json=payload or {"content": "Nhan vien duoc nghi phep bao nhieu ngay?"},
    )


def parse_sse(text: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for frame in [frame for frame in text.split("\n\n") if frame.strip()]:
        event_name = ""
        data: dict[str, object] | None = None
        for line in frame.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        assert event_name
        assert data is not None
        events.append((event_name, data))
    return events


def test_stream_endpoint_requires_authentication(api_client: TestClient) -> None:
    response = api_client.post(
        f"/api/v1/chat/sessions/{uuid.uuid4()}/messages/stream",
        json={"content": "Q"},
    )

    assert response.status_code == 401


def test_stream_endpoint_returns_event_stream_headers(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(api_client, async_session_factory_for_tests)

    response = post_stream(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert "content-length" not in response.headers


def test_stream_success_persists_assistant_message_once_and_returns_final_payload(
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
        document_title="Quy che nhan su",
        chunk_id=chunk_id,
        page_number=14,
        excerpt="Nhan vien chinh thuc duoc huong 12 ngay nghi phep.",
        relevance_score=0.87,
        citation_order=1,
    )
    install_service(api_client, async_session_factory_for_tests, citations=(citation,))

    response = post_stream(api_client, make_auth_headers, owner, chat)

    events = parse_sse(response.text)
    assert [event for event, _ in events] == [
        "stream.started",
        "message.delta",
        "citations.ready",
        "message.completed",
    ]
    assert events[1][1] == {"sequence": 1, "content": GROUNDED_ANSWER_DISPLAY}
    completed = events[-1][1]
    assert completed["message_id"]
    assert completed["content"] == GROUNDED_ANSWER_DISPLAY
    assert completed["provider"] == "openai_compatible"
    assert completed["model"] == "fake-model"
    assert completed["usage"] == {
        "prompt_tokens": 4,
        "completion_tokens": 2,
        "total_tokens": 6,
    }
    assert completed["citations"] == [
        {
            "document_id": str(document_id),
            "document_title": "Quy che nhan su",
            "chunk_id": str(chunk_id),
            "page_number": 14,
            "excerpt": "Nhan vien chinh thuc duoc huong 12 ngay nghi phep.",
            "relevance_score": 0.87,
            "citation_order": 1,
        }
    ]
    assert run_async(count_messages(async_session_factory_for_tests, chat_session=chat)) == 2


def test_stream_uses_current_session_conversation_memory(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.USER,
        content="Working policy?",
        seconds=1,
    )
    create_message(
        async_session_factory_for_tests,
        chat_session=chat,
        role=ChatMessageRole.ASSISTANT,
        content="08:00-17:00 applies on working days.",
        seconds=2,
    )
    retrieval, llm = install_service(api_client, async_session_factory_for_tests)

    response = post_stream(
        api_client,
        make_auth_headers,
        owner,
        chat,
        {"content": "Does it apply on Saturday?"},
    )

    events = parse_sse(response.text)
    assert events[-1][0] == "message.completed"
    # History resolves the follow-up topic; the prior assistant answer is not evidence.
    assert retrieval.queries == ["Does Working policy apply on Saturday?"]
    assert retrieval.queries[0] in llm.messages[1].content
    assert "08:00-17:00 applies on working days." not in llm.messages[1].content


def test_stream_endpoint_checks_session_ownership(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    retrieval, llm = install_service(api_client, async_session_factory_for_tests)

    response = post_stream(api_client, make_auth_headers, other, chat)

    assert response.status_code == 200
    events = parse_sse(response.text)
    assert [event for event, _ in events] == ["stream.started", "stream.error"]
    assert events[-1][1]["code"] == "CHAT_SESSION_NOT_FOUND"
    assert retrieval.calls == 0
    assert llm.calls == 0
    assert run_async(count_messages(async_session_factory_for_tests, chat_session=chat)) == 0


def test_provider_failure_emits_safe_error_and_persists_no_assistant_message(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    secret = "RAW_SECRET_PROVIDER_BODY"
    install_service(
        api_client,
        async_session_factory_for_tests,
        llm=FakeLLMProvider(LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE, secret)),
    )

    response = post_stream(api_client, make_auth_headers, owner, chat)

    events = parse_sse(response.text)
    assert [event for event, _ in events] == ["stream.started", "stream.error"]
    assert events[-1][1]["code"] == "LLM_PROVIDER_BAD_RESPONSE"
    assert secret not in response.text
    assert run_async(count_messages(async_session_factory_for_tests, chat_session=chat)) == 0


def test_invalid_citation_stream_fails_safe_to_fixed_no_answer(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    from app.citations.errors import CitationFailureCode, CitationValidationError

    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    settings = make_settings()
    citation_repository = FakeCitationRepository()
    install_service(
        api_client,
        async_session_factory_for_tests,
        settings=settings,
        citation_error=CitationValidationError(CitationFailureCode.CITATION_MARKER_UNKNOWN),
        citation_repository=citation_repository,
    )

    response = post_stream(api_client, make_auth_headers, owner, chat)

    events = parse_sse(response.text)
    assert [event for event, _ in events][-1] == "message.completed"
    assert "stream.error" not in [event for event, _ in events]
    completed = events[-1][1]
    assert completed["grounding_status"] == "NO_ANSWER"
    assert completed["citations"] == []
    assert completed["content"] == settings.chat_no_answer_message
    serialized_events = json.dumps([payload for _, payload in events], ensure_ascii=False)
    assert "[SOURCE_" not in serialized_events
    assert GROUNDED_CONTEXT not in serialized_events
    assert citation_repository.calls == 0

    async def persisted() -> tuple[list[ChatMessage], int]:
        async with async_session_factory_for_tests() as session:
            messages = list(
                await session.scalars(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == chat.id)
                    .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                )
            )
            citation_count = await session.scalar(select(func.count()).select_from(MessageCitation))
            return messages, citation_count or 0

    messages, citation_count = run_async(persisted())
    assert [message.role for message in messages] == [
        ChatMessageRole.USER,
        ChatMessageRole.ASSISTANT,
    ]
    assert messages[1].content == settings.chat_no_answer_message
    assert "[SOURCE_" not in messages[1].content
    assert GROUNDED_CONTEXT not in messages[1].content
    assert citation_count == 0


def test_stream_preserves_no_answer_policy(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    retrieval = FakeRetrievalService(retrieval_result())
    _, llm = install_service(api_client, async_session_factory_for_tests, retrieval=retrieval)

    response = post_stream(api_client, make_auth_headers, owner, chat)

    events = parse_sse(response.text)
    assert events[-1][1]["grounding_status"] == "NO_ANSWER"
    assert llm.calls == 0
    assert run_async(count_messages(async_session_factory_for_tests, chat_session=chat)) == 2


def test_stream_endpoint_rate_limited_before_headers(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def reject_chat_rate_limit(request: Request, current_user: User) -> None:
        raise RateLimitExceededError(retry_after_seconds=30)

    import app.api.v1.chat as chat_api

    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(api_client, async_session_factory_for_tests)
    monkeypatch.setattr(chat_api, "enforce_chat_rate_limit", reject_chat_rate_limit)

    response = post_stream(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 429
    assert not response.headers.get("content-type", "").startswith("text/event-stream")


def test_stream_timeout_emits_heartbeat_error_once_and_cancels_task() -> None:
    async def collect() -> tuple[list[tuple[str, dict[str, object]]], bool]:
        service = ChatStreamService(
            settings=make_settings(
                llm_stream_heartbeat_seconds=0.01,
                llm_stream_max_duration_seconds=0.035,
            )
        )
        answer_service = SlowAnswerService()
        frames: list[bytes] = []
        async for frame in service.stream_answer(
            request=ConnectedRequest(),  # type: ignore[arg-type]
            current_user=SimpleNamespace(id=uuid.uuid4()),  # type: ignore[arg-type]
            session_id=uuid.uuid4(),
            question="Q",
            answer_service=answer_service,  # type: ignore[arg-type]
            audit_context=None,
        ):
            frames.append(frame)
        return parse_sse(b"".join(frames).decode("utf-8")), answer_service.cancelled

    events, cancelled = run_async(collect())
    event_names = [event for event, _ in events]

    assert event_names[0] == "stream.started"
    assert "heartbeat" in event_names
    assert "message.delta" not in event_names
    assert "message.completed" not in event_names
    assert event_names[-1] == "stream.error"
    assert sum(1 for event in event_names if event in {"stream.error", "message.completed"}) == 1
    assert events[-1][1]["code"] == "STREAM_TIMEOUT"
    assert cancelled is True


def test_client_disconnect_cancels_provider_work() -> None:

    async def collect() -> tuple[list[bytes], bool]:

        service = ChatStreamService(settings=make_settings(llm_stream_heartbeat_seconds=0.01))

        answer_service = SlowAnswerService()

        events: list[bytes] = []

        async for frame in service.stream_answer(
            request=DisconnectingRequest(),  # type: ignore[arg-type]
            current_user=SimpleNamespace(id=uuid.uuid4()),  # type: ignore[arg-type]
            session_id=uuid.uuid4(),
            question="Q",
            answer_service=answer_service,  # type: ignore[arg-type]
            audit_context=None,
        ):
            events.append(frame)

        return events, answer_service.cancelled

    frames, cancelled = run_async(collect())

    assert len(frames) == 1

    assert "event: stream.started" in frames[0].decode("utf-8")

    assert cancelled is True


def test_existing_non_streaming_chat_endpoint_unchanged(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    install_service(api_client, async_session_factory_for_tests)

    response = api_client.post(
        f"/api/v1/chat/sessions/{chat.id}/messages",
        headers=make_auth_headers(owner),
        json={"content": "Q"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert set(data) == {
        "session_id",
        "user_message",
        "assistant_message",
        "grounding_status",
        "retrieved_chunk_count",
    }
    assert response.headers["content-type"].startswith("application/json")


def test_stream_success_returns_web_citations_ready_event(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    owner = make_user(role=UserRole.STAFF)
    chat = create_session(async_session_factory_for_tests, owner=owner)
    citation = SimpleNamespace(
        source_type=CitationSourceType.WEB,
        document_id=None,
        document_title="Microsoft Learn",
        chunk_id=None,
        page_number=1,
        excerpt="Microsoft Learn describes Azure AI services.",
        relevance_score=None,
        citation_order=1,
        source_url="https://learn.microsoft.com/en-us/azure/ai-services/",
    )
    install_service(api_client, async_session_factory_for_tests, citations=(citation,))

    response = post_stream(api_client, make_auth_headers, owner, chat)

    assert response.status_code == 200
    events = parse_sse(response.text)
    citations_event = [payload for event, payload in events if event == "citations.ready"][0]
    assert citations_event["citations"] == [
        {
            "document_id": None,
            "document_title": "Microsoft Learn",
            "chunk_id": None,
            "page_number": 1,
            "excerpt": "Microsoft Learn describes Azure AI services.",
            "relevance_score": None,
            "citation_order": 1,
            "source_type": "WEB",
            "source_url": "https://learn.microsoft.com/en-us/azure/ai-services/",
        }
    ]
