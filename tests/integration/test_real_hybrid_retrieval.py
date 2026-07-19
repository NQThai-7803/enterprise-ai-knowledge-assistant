from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.embeddings.factory import create_embedding_provider
from app.models import DocumentAccessScope, DocumentChunk, DocumentStatus, UserRole
from app.retrieval.hybrid_service import HybridRetrievalService
from app.retrieval.keyword_service import KeywordRetrievalService
from app.retrieval.semantic_service import SemanticRetrievalService
from tests.integration.retrieval_helpers import (
    JitOffSessionProvider,
    create_department,
    create_document,
    create_user,
    run_async,
    stable_uuid,
)

pytestmark = [pytest.mark.integration, pytest.mark.hybrid_retrieval_model_integration]

QUERY = "Chính sách IT-09 quy định thay đổi mật khẩu bao lâu một lần?"
POLICY = "Chính sách POLICY-IT-09 yêu cầu người dùng thay đổi mật khẩu sau mỗi 90 ngày."
SEMANTIC_ONLY = "Tài khoản phải cập nhật thông tin xác thực định kỳ để bảo đảm an toàn."
UNRELATED = "Nhân viên được hưởng 12 ngày nghỉ phép mỗi năm."
HIDDEN = "Chính sách POLICY-IT-09 nội bộ của phòng khác có dữ liệu không được phép xem."


def checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        retrieval_top_k=6,
        retrieval_max_top_k=10,
        min_relevance_score=0.0,
        keyword_retrieval_top_k=6,
        keyword_retrieval_max_top_k=10,
        hybrid_retrieval_top_k=3,
        hybrid_retrieval_max_top_k=5,
        hybrid_candidate_multiplier=2,
        hybrid_semantic_min_relevance_score=0.0,
    )


async def create_real_chunk(
    session: AsyncSession,
    *,
    key: str,
    document_id,
    text: str,
    embedding: Sequence[float],
) -> DocumentChunk:
    chunk = DocumentChunk(
        id=stable_uuid(f"real-hybrid-chunk:{key}"),
        document_id=document_id,
        chunk_index=0,
        text=text,
        token_count=max(1, len(text.split())),
        character_count=len(text),
        page_numbers=[1],
        start_page=1,
        end_page=1,
        overlap_token_count=0,
        content_sha256=checksum(text),
        embedding=list(embedding),
        embedding_provider="sentence_transformers",
        embedding_model="intfloat/multilingual-e5-small",
        embedding_dimensions=384,
    )
    session.add(chunk)
    await session.commit()
    await session.refresh(chunk)
    return chunk


async def build_fixture(session: AsyncSession):  # noqa: ANN201
    department_a = await create_department(session, "real-hybrid-a")
    department_b = await create_department(session, "real-hybrid-b")
    admin = await create_user(session, "real-hybrid-admin", role=UserRole.ADMIN)
    staff_a = await create_user(session, "real-hybrid-staff-a", department_id=department_a.id)
    embedding_provider = create_embedding_provider(make_settings())
    passage_batch = embedding_provider.embed_passages([POLICY, SEMANTIC_ONLY, UNRELATED, HIDDEN])

    policy_doc = await create_document(
        session,
        "real-hybrid-policy",
        uploader=admin,
        title="POLICY-IT-09",
        access_scope=DocumentAccessScope.ORGANIZATION,
        status=DocumentStatus.READY,
    )
    semantic_doc = await create_document(
        session,
        "real-hybrid-semantic",
        uploader=admin,
        title="Xac thuc dinh ky",
        access_scope=DocumentAccessScope.ORGANIZATION,
        status=DocumentStatus.READY,
    )
    unrelated_doc = await create_document(
        session,
        "real-hybrid-unrelated",
        uploader=admin,
        title="Nghi phep",
        access_scope=DocumentAccessScope.ORGANIZATION,
        status=DocumentStatus.READY,
    )
    hidden_doc = await create_document(
        session,
        "real-hybrid-hidden",
        uploader=admin,
        title="Tai lieu phong B",
        access_scope=DocumentAccessScope.DEPARTMENT,
        department_id=department_b.id,
        status=DocumentStatus.READY,
    )
    policy_chunk = await create_real_chunk(
        session,
        key="policy",
        document_id=policy_doc.id,
        text=POLICY,
        embedding=passage_batch.vectors[0].values,
    )
    semantic_chunk = await create_real_chunk(
        session,
        key="semantic",
        document_id=semantic_doc.id,
        text=SEMANTIC_ONLY,
        embedding=passage_batch.vectors[1].values,
    )
    unrelated_chunk = await create_real_chunk(
        session,
        key="unrelated",
        document_id=unrelated_doc.id,
        text=UNRELATED,
        embedding=passage_batch.vectors[2].values,
    )
    hidden_chunk = await create_real_chunk(
        session,
        key="hidden",
        document_id=hidden_doc.id,
        text=HIDDEN,
        embedding=passage_batch.vectors[3].values,
    )
    return {
        "admin": admin,
        "staff_a": staff_a,
        "policy_chunk": policy_chunk,
        "semantic_chunk": semantic_chunk,
        "unrelated_chunk": unrelated_chunk,
        "hidden_chunk": hidden_chunk,
        "hidden_doc": hidden_doc,
    }


def make_service(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> HybridRetrievalService:
    settings = make_settings()
    session_provider = JitOffSessionProvider(async_session_factory_for_tests)
    embedding_provider = create_embedding_provider(settings)
    semantic = SemanticRetrievalService(
        settings=settings,
        embedding_provider=embedding_provider,
        session_provider=session_provider,
    )
    keyword = KeywordRetrievalService(settings=settings, session_provider=session_provider)
    return HybridRetrievalService(
        settings=settings,
        semantic_retrieval_service=semantic,
        keyword_retrieval_service=keyword,
    )


def test_real_hybrid_retrieval_returns_policy_chunk_first(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_fixture(session)
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=data["staff_a"])

        assert result.hits[0].chunk_id == data["policy_chunk"].id
        assert result.hits[0].matched_by == ("semantic", "keyword")

    run_async(scenario())


def test_real_hybrid_result_contains_semantic_and_keyword_scores(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_fixture(session)
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=data["staff_a"])
        first = result.hits[0]

        assert first.semantic_score is not None
        assert first.semantic_rank is not None
        assert first.keyword_score is not None
        assert first.keyword_rank is not None
        assert first.hybrid_score > 0.0

    run_async(scenario())


def test_real_hybrid_result_does_not_return_vectors(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_fixture(session)
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=data["staff_a"])

        assert result.hits
        assert not hasattr(result.hits[0], "embedding")
        assert "0.12345" not in repr(result.hits[0])

    run_async(scenario())


def test_real_hybrid_respects_permissions(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_fixture(session)
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=data["staff_a"])

        assert data["hidden_doc"].id not in [hit.document_id for hit in result.hits]
        assert HIDDEN not in [hit.text for hit in result.hits]

    run_async(scenario())


def test_real_hybrid_is_stable_for_same_query(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_fixture(session)
        service = make_service(async_session_factory_for_tests)

        first = await service.retrieve(query=QUERY, current_user=data["staff_a"])
        second = await service.retrieve(query=QUERY, current_user=data["staff_a"])

        assert [hit.chunk_id for hit in first.hits] == [hit.chunk_id for hit in second.hits]

    run_async(scenario())
