from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.embeddings.factory import create_embedding_provider
from app.models import DocumentAccessScope, DocumentChunk, DocumentStatus, UserRole
from app.retrieval.semantic_repository import search_permitted_chunks
from tests.integration.retrieval_helpers import (
    create_department,
    create_document,
    create_user,
    disable_postgres_jit,
    run_async,
    stable_uuid,
)

pytestmark = [pytest.mark.integration, pytest.mark.semantic_retrieval_model_integration]

QUERY = "NhÃ¢n viÃªn Ä‘Æ°á»£c nghá»‰ phÃ©p bao nhiÃªu ngÃ y?"
RELATED = "NhÃ¢n viÃªn chÃ­nh thá»©c Ä‘Æ°á»£c hÆ°á»Ÿng 12 ngÃ y nghá»‰ phÃ©p cÃ³ lÆ°Æ¡ng má»—i nÄƒm."
UNRELATED = "Há»‡ thá»‘ng sao lÆ°u cÆ¡ sá»Ÿ dá»¯ liá»‡u vÃ o lÃºc 02 giá» sÃ¡ng."
HIDDEN = "TÃ i liá»‡u máº­t cá»§a phÃ²ng khÃ¡c nÃ³i vá» 12 ngÃ y nghá»‰ phÃ©p."


def checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def provider():
    return create_embedding_provider(Settings())


async def create_real_chunk(
    session: AsyncSession,
    *,
    key: str,
    document_id,
    text: str,
    embedding: Sequence[float],
) -> DocumentChunk:
    chunk = DocumentChunk(
        id=stable_uuid(f"real-chunk:{key}"),
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


async def build_real_fixture(session: AsyncSession):  # noqa: ANN201
    department_a = await create_department(session, "real-a")
    department_b = await create_department(session, "real-b")
    admin = await create_user(session, "real-admin", role=UserRole.ADMIN)
    staff_a = await create_user(session, "real-staff-a", department_id=department_a.id)
    embedding_provider = provider()
    passage_batch = embedding_provider.embed_passages([RELATED, UNRELATED, HIDDEN])
    query_vector = embedding_provider.embed_query(QUERY).values

    related_doc = await create_document(
        session,
        "real-related",
        uploader=admin,
        title="Chinh sach nghi phep",
        access_scope=DocumentAccessScope.ORGANIZATION,
        status=DocumentStatus.READY,
    )
    unrelated_doc = await create_document(
        session,
        "real-unrelated",
        uploader=admin,
        title="Sao luu co so du lieu",
        access_scope=DocumentAccessScope.ORGANIZATION,
        status=DocumentStatus.READY,
    )
    hidden_doc = await create_document(
        session,
        "real-hidden",
        uploader=admin,
        title="Tai lieu phong B",
        access_scope=DocumentAccessScope.DEPARTMENT,
        department_id=department_b.id,
        status=DocumentStatus.READY,
    )
    related_chunk = await create_real_chunk(
        session,
        key="related",
        document_id=related_doc.id,
        text=RELATED,
        embedding=passage_batch.vectors[0].values,
    )
    unrelated_chunk = await create_real_chunk(
        session,
        key="unrelated",
        document_id=unrelated_doc.id,
        text=UNRELATED,
        embedding=passage_batch.vectors[1].values,
    )
    hidden_chunk = await create_real_chunk(
        session,
        key="hidden",
        document_id=hidden_doc.id,
        text=HIDDEN,
        embedding=passage_batch.vectors[2].values,
    )
    return {
        "staff_a": staff_a,
        "query_vector": query_vector,
        "related_doc": related_doc,
        "unrelated_doc": unrelated_doc,
        "hidden_doc": hidden_doc,
        "related_chunk": related_chunk,
        "unrelated_chunk": unrelated_chunk,
        "hidden_chunk": hidden_chunk,
    }


def test_real_semantic_retrieval_returns_related_chunk_first(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_real_fixture(session)
            await disable_postgres_jit(session)
            rows = await search_permitted_chunks(
                session,
                query_vector=data["query_vector"],
                current_user=data["staff_a"],
                top_k=2,
                min_relevance_score=0.0,
            )

            assert rows[0].chunk_id == data["related_chunk"].id
            assert rows[0].document_id == data["related_doc"].id
            assert rows[1].chunk_id == data["unrelated_chunk"].id

    run_async(scenario())


def test_real_semantic_retrieval_returns_finite_score(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_real_fixture(session)
            await disable_postgres_jit(session)
            rows = await search_permitted_chunks(
                session,
                query_vector=data["query_vector"],
                current_user=data["staff_a"],
                top_k=2,
                min_relevance_score=0.0,
            )

            assert all(0.0 <= row.relevance_score <= 1.0 for row in rows)

    run_async(scenario())


def test_real_semantic_retrieval_respects_threshold(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_real_fixture(session)
            await disable_postgres_jit(session)
            rows = await search_permitted_chunks(
                session,
                query_vector=data["query_vector"],
                current_user=data["staff_a"],
                top_k=2,
                min_relevance_score=1.0,
            )

            assert rows == ()

    run_async(scenario())


def test_real_semantic_retrieval_respects_permissions(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_real_fixture(session)
            await disable_postgres_jit(session)
            rows = await search_permitted_chunks(
                session,
                query_vector=data["query_vector"],
                current_user=data["staff_a"],
                top_k=3,
                min_relevance_score=0.0,
            )

            assert data["hidden_doc"].id not in [row.document_id for row in rows]
            assert data["hidden_chunk"].text not in [row.text for row in rows]

    run_async(scenario())


def test_real_semantic_retrieval_does_not_return_vectors(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            data = await build_real_fixture(session)
            await disable_postgres_jit(session)
            rows = await search_permitted_chunks(
                session,
                query_vector=data["query_vector"],
                current_user=data["staff_a"],
                top_k=2,
                min_relevance_score=0.0,
            )

            assert rows
            assert not hasattr(rows[0], "embedding")
            assert "0.12345" not in repr(rows[0])

    run_async(scenario())
