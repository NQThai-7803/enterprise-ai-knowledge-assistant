"""No answer state crosses users or outlives a revoked grant (cache audit, 2026-11-22).

One GroundedAnswerService instance serves every request, as ``app.state`` does in production,
with the default answer mode, real permission-filtered retrieval and the real validators. The
fake LLM answers only from the sources in the prompt it receives, like a real model: any cache
between the question and the answer (answer, retrieval, embedding) would show up here as the
first asker's answer reaching the second. The reranker is left out; it only reorders hits that
retrieval has already filtered by permission.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_grounded_answer_service
from app.core.config import Settings
from app.embeddings.models import EmbeddingBatch
from app.llm.models import LLMGenerationResult
from app.models import ChatMessage, ChatSession, DocumentAccessScope, MessageCitation, UserRole
from app.retrieval.hybrid_service import HybridRetrievalService
from app.retrieval.keyword_service import KeywordRetrievalService
from app.retrieval.semantic_service import SemanticRetrievalService
from app.services.grounded_answer_service import GroundedAnswerService
from tests.api.conftest import auth_headers
from tests.api.test_chat_messages import create_session
from tests.integration.retrieval_helpers import (
    FakeQueryEmbeddingProvider,
    JitOffSessionProvider,
    create_chunk,
    create_department,
    create_document,
    create_permission,
    create_user,
)
from tests.integration.test_grounded_answer_persistence import FakeCounter

pytestmark = pytest.mark.integration

QUESTION = "Ngân sách năm 2027 của dự án Orion là bao nhiêu?"
SECRET_VALUE = "7.400 triệu đồng"
SECRET_TEXT = f"Ngân sách năm 2027 của dự án Orion là {SECRET_VALUE}."
SECRET_TITLE = "Orion restricted budget"
PUBLIC_TEXT = "Dự án Orion do phòng Kế hoạch điều phối trong năm 2027."
_SOURCE_1 = re.compile(r"--- SOURCE_1 START ---\n.*?Content:\n(.*?)\n--- SOURCE_1 END ---", re.S)
ENDPOINTS = ("messages", "messages/stream")


class PassageEmbeddingProvider(FakeQueryEmbeddingProvider):
    """Claim relevance (s2) embeds the cited sentence; one shared vector keeps it relevant."""

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingBatch:
        vectors = tuple(self.embed_query(text) for text in texts)
        return EmbeddingBatch(
            vectors=vectors,
            count=len(vectors),
            dimensions=384,
            normalized=True,
            model_name="fake-model",
        )


class SourceEchoLLM:
    """Restates SOURCE_1 of the prompt it is given, with its marker."""

    def __init__(self, sentinel: str) -> None:
        self.sentinel = sentinel
        self.prompts: list[str] = []

    async def generate(self, *, messages, temperature: float, max_output_tokens: int):  # noqa: ANN001
        self.prompts.append("\n".join(message.content for message in messages))
        match = _SOURCE_1.search(messages[-1].content)
        return LLMGenerationResult(
            content=f"{match.group(1).strip()} [SOURCE_1]" if match else self.sentinel,
            model="fake",
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=5,
            response_time_ms=1,
        )


def install_shared_service(
    api_client: TestClient, session_factory: async_sessionmaker[AsyncSession]
) -> SourceEchoLLM:
    settings = Settings(
        _env_file=None,
        llm_enabled=True,
        llm_base_url="http://localhost:11434/v1",
        llm_model="fake-model",
        llm_retry_backoff_seconds=0.0,
    )
    session_provider = JitOffSessionProvider(session_factory)
    retrieval = HybridRetrievalService(
        settings=settings,
        semantic_retrieval_service=SemanticRetrievalService(
            settings=settings,
            embedding_provider=PassageEmbeddingProvider(),
            session_provider=session_provider,
        ),
        keyword_retrieval_service=KeywordRetrievalService(
            settings=settings, session_provider=session_provider
        ),
    )
    llm = SourceEchoLLM(settings.llm_no_answer_sentinel)
    service = GroundedAnswerService(
        settings=settings,
        session_provider=session_factory,
        hybrid_retrieval_service=retrieval,
        llm_provider_factory=lambda: llm,
        token_counter=FakeCounter(),
    )
    api_client.app.dependency_overrides[get_grounded_answer_service] = lambda: service
    return llm


async def seed(session_factory: async_sessionmaker[AsyncSession], key: str):  # noqa: ANN201
    """A Manager's PRIVATE document holds the answer; an ORGANIZATION one only mentions it."""
    async with session_factory() as session:
        department = await create_department(session, f"{key}-dept")
        manager = await create_user(
            session, f"{key}-manager", role=UserRole.MANAGER, department_id=department.id
        )
        staff = await create_user(
            session, f"{key}-staff", role=UserRole.STAFF, department_id=department.id
        )
        secret = await create_document(
            session, f"{key}-secret", uploader=manager, title=SECRET_TITLE
        )
        public = await create_document(
            session,
            f"{key}-public",
            uploader=manager,
            access_scope=DocumentAccessScope.ORGANIZATION,
        )
        await create_chunk(session, f"{key}-secret", document=secret, text=SECRET_TEXT)
        await create_chunk(
            session, f"{key}-public", document=public, text=PUBLIC_TEXT, similarity=0.9
        )
    return manager, staff, secret


def ask(api_client: TestClient, user, chat: ChatSession, endpoint: str) -> str:  # noqa: ANN001
    response = api_client.post(
        f"/api/v1/chat/sessions/{chat.id}/{endpoint}",
        headers=auth_headers(user),
        json={"content": QUESTION},
    )
    assert response.status_code == (200 if endpoint.endswith("stream") else 201), response.text
    return response.text


def assert_secret_absent(body: str, prompts: Sequence[str], secret_id: object) -> None:
    for marker in (SECRET_VALUE, SECRET_TITLE, str(secret_id)):
        assert marker not in body
    assert all(SECRET_VALUE not in prompt for prompt in prompts)


def stored_secret_citations(
    session_factory: async_sessionmaker[AsyncSession], user, secret_id: object
) -> int:  # noqa: ANN001
    async def count() -> int:
        async with session_factory() as session:
            statement = (
                select(func.count())
                .select_from(MessageCitation)
                .join(ChatMessage, ChatMessage.id == MessageCitation.message_id)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(ChatSession.user_id == user.id, MessageCitation.document_id == secret_id)
            )
            return await session.scalar(statement) or 0

    return asyncio.run(count())


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_staff_asking_a_managers_question_gets_nothing_from_the_managers_document(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    endpoint: str,
) -> None:
    manager, staff, secret = asyncio.run(seed(async_session_factory_for_tests, "isolation"))
    llm = install_shared_service(api_client, async_session_factory_for_tests)

    manager_chat = create_session(async_session_factory_for_tests, owner=manager)
    manager_body = ask(api_client, manager, manager_chat, endpoint)
    # The Manager is answered from the document, so a shared cache would have it to hand out.
    assert SECRET_VALUE in manager_body
    assert str(secret.id) in manager_body

    staff_chat = create_session(async_session_factory_for_tests, owner=staff)
    for _ in range(2):  # the repeat is what a question-keyed cache would serve
        seen = len(llm.prompts)
        staff_body = ask(api_client, staff, staff_chat, endpoint)
        assert_secret_absent(staff_body, llm.prompts[seen:], secret.id)
    assert stored_secret_citations(async_session_factory_for_tests, staff, secret.id) == 0


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_revoked_grant_stops_answers_from_the_document(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    endpoint: str,
) -> None:
    manager, staff, secret = asyncio.run(seed(async_session_factory_for_tests, "revoke"))

    async def grant_staff():  # noqa: ANN202 - only an Admin revokes a grant
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "revoke-admin", role=UserRole.ADMIN)
            grant = await create_permission(
                session, "revoke-grant", document=secret, creator=manager, user_id=staff.id
            )
            return admin, grant

    admin, grant = asyncio.run(grant_staff())
    llm = install_shared_service(api_client, async_session_factory_for_tests)
    first_chat = create_session(async_session_factory_for_tests, owner=staff)

    granted_body = ask(api_client, staff, first_chat, endpoint)
    assert SECRET_VALUE in granted_body
    cited_while_granted = stored_secret_citations(async_session_factory_for_tests, staff, secret.id)
    assert cited_while_granted == 1

    revoked = api_client.delete(
        f"/api/v1/documents/{secret.id}/permissions/{grant.id}", headers=auth_headers(admin)
    )
    assert revoked.status_code == 204, revoked.text

    # The same session (follow-up memory) and a new one.
    for chat in (first_chat, create_session(async_session_factory_for_tests, owner=staff)):
        seen = len(llm.prompts)
        body = ask(api_client, staff, chat, endpoint)
        assert_secret_absent(body, llm.prompts[seen:], secret.id)
    assert (
        stored_secret_citations(async_session_factory_for_tests, staff, secret.id)
        == cited_while_granted
    )
