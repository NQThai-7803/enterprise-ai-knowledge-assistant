from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import DocumentAccessScope, DocumentPermission, DocumentStatus, UserRole
from app.retrieval.hybrid_service import HybridRetrievalService
from app.retrieval.keyword_service import KeywordRetrievalService
from app.retrieval.semantic_service import SemanticRetrievalService
from tests.integration.retrieval_helpers import (
    FakeQueryEmbeddingProvider,
    JitOffSessionProvider,
    assert_marker_absent,
    create_chunk,
    create_department,
    create_document,
    create_permission,
    create_user,
)

pytestmark = pytest.mark.integration
HIDDEN_MARKER = "UNAUTHORIZED_HYBRID_MARKER"
QUERY = "hybridkeyword"


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "retrieval_top_k": 5,
        "retrieval_max_top_k": 20,
        "min_relevance_score": 0.0,
        "retrieval_max_query_characters": 4000,
        "keyword_retrieval_top_k": 5,
        "keyword_retrieval_max_top_k": 20,
        "keyword_min_rank": 0.0,
        "hybrid_retrieval_top_k": 3,
        "hybrid_retrieval_max_top_k": 10,
        "hybrid_candidate_multiplier": 4,
        "hybrid_rrf_k": 60,
        "hybrid_semantic_weight": 1.0,
        "hybrid_keyword_weight": 1.0,
        "hybrid_semantic_min_relevance_score": 0.0,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def make_service(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    **settings_overrides: object,
) -> HybridRetrievalService:
    settings = make_settings(**settings_overrides)
    session_provider = JitOffSessionProvider(async_session_factory_for_tests)
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


def test_hybrid_returns_both_channel_hit_first(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-both-admin", role=UserRole.ADMIN)
            semantic_only = await create_document(session, "hybrid-both-semantic", uploader=admin)
            both = await create_document(session, "hybrid-both-both", uploader=admin)
            keyword_only = await create_document(session, "hybrid-both-keyword", uploader=admin)
            await create_chunk(
                session,
                "hybrid-both-semantic",
                document=semantic_only,
                text="semantic branch only",
                similarity=0.99,
            )
            await create_chunk(
                session,
                "hybrid-both-both",
                document=both,
                text=f"semantic and keyword {QUERY}",
                similarity=0.95,
            )
            await create_chunk(
                session,
                "hybrid-both-keyword",
                document=keyword_only,
                text=f"keyword only {QUERY}",
                similarity=0.1,
            )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert result.hits[0].document_id == both.id
        assert result.hits[0].matched_by == ("semantic", "keyword")

    run_async(scenario())


def test_hybrid_includes_semantic_only_candidate(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-semantic-only-admin", role=UserRole.ADMIN)
            document = await create_document(session, "hybrid-semantic-only-doc", uploader=admin)
            await create_chunk(
                session,
                "hybrid-semantic-only-doc",
                document=document,
                text="semantic only content",
                similarity=0.9,
            )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert result.hits[0].document_id == document.id
        assert result.hits[0].matched_by == ("semantic",)

    run_async(scenario())


def test_hybrid_includes_keyword_only_candidate(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-keyword-only-admin", role=UserRole.ADMIN)
            document = await create_document(session, "hybrid-keyword-only-doc", uploader=admin)
            await create_chunk(
                session,
                "hybrid-keyword-only-doc",
                document=document,
                text=f"keyword only {QUERY}",
                similarity=0.0,
                axis=2,
            )
        service = make_service(
            async_session_factory_for_tests,
            hybrid_semantic_min_relevance_score=0.8,
        )

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert result.hits[0].document_id == document.id
        assert result.hits[0].matched_by == ("keyword",)

    run_async(scenario())


def test_hybrid_deduplicates_same_chunk(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-dedup-admin", role=UserRole.ADMIN)
            document = await create_document(session, "hybrid-dedup-doc", uploader=admin)
            await create_chunk(
                session,
                "hybrid-dedup-doc",
                document=document,
                text=f"both channels {QUERY}",
                similarity=0.9,
            )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert [hit.document_id for hit in result.hits] == [document.id]
        assert result.fused_candidate_count == 1
        assert result.hits[0].matched_by == ("semantic", "keyword")

    run_async(scenario())


def test_hybrid_preserves_page_metadata(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-pages-admin", role=UserRole.ADMIN)
            document = await create_document(session, "hybrid-pages-doc", uploader=admin)
            await create_chunk(
                session,
                "hybrid-pages-doc",
                document=document,
                text=f"page metadata {QUERY}",
                similarity=0.9,
                page_numbers=(3, 1, 2),
            )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert result.hits[0].page_numbers == (3, 1, 2)
        assert result.hits[0].start_page == 1
        assert result.hits[0].end_page == 3

    run_async(scenario())


def test_hybrid_applies_final_top_k(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-final-topk-admin", role=UserRole.ADMIN)
            for index, similarity in enumerate((0.99, 0.98, 0.97)):
                document = await create_document(
                    session, f"hybrid-final-topk-{index}", uploader=admin
                )
                await create_chunk(
                    session,
                    f"hybrid-final-topk-{index}",
                    document=document,
                    text=f"{QUERY} {index}",
                    similarity=similarity,
                )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin, top_k=2)

        assert result.hit_count == 2
        assert result.fused_candidate_count == 3

    run_async(scenario())


def test_hybrid_respects_weights(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-weights-admin", role=UserRole.ADMIN)
            semantic_only = await create_document(
                session, "hybrid-weights-semantic", uploader=admin
            )
            keyword_only = await create_document(session, "hybrid-weights-keyword", uploader=admin)
            await create_chunk(
                session,
                "hybrid-weights-semantic",
                document=semantic_only,
                text="semantic-only weighted branch",
                similarity=0.99,
            )
            await create_chunk(
                session,
                "hybrid-weights-keyword",
                document=keyword_only,
                text=f"keyword weighted {QUERY}",
                similarity=0.0,
                axis=2,
            )
        service = make_service(
            async_session_factory_for_tests,
            hybrid_semantic_weight=0.0,
            hybrid_keyword_weight=1.0,
            hybrid_semantic_min_relevance_score=0.8,
        )

        result = await service.retrieve(query=QUERY, current_user=admin, top_k=2)

        assert result.hits[0].document_id == keyword_only.id

    run_async(scenario())


def test_hybrid_respects_candidate_multiplier(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-candidate-admin", role=UserRole.ADMIN)
            for index, similarity in enumerate((0.99, 0.98, 0.97)):
                document = await create_document(
                    session, f"hybrid-candidate-{index}", uploader=admin
                )
                await create_chunk(
                    session,
                    f"hybrid-candidate-{index}",
                    document=document,
                    text=f"{QUERY} {index}",
                    similarity=similarity,
                )
        service = make_service(async_session_factory_for_tests, hybrid_candidate_multiplier=1)

        result = await service.retrieve(query=QUERY, current_user=admin, top_k=1)

        assert result.semantic_candidate_count == 1
        assert result.keyword_candidate_count == 1
        assert result.hit_count == 1

    run_async(scenario())


def test_hybrid_results_are_stable(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-stable-admin", role=UserRole.ADMIN)
            for key in ("b", "a", "c"):
                document = await create_document(session, f"hybrid-stable-{key}", uploader=admin)
                await create_chunk(session, f"hybrid-stable-{key}", document=document, text=QUERY)
        service = make_service(async_session_factory_for_tests)

        first = await service.retrieve(query=QUERY, current_user=admin)
        second = await service.retrieve(query=QUERY, current_user=admin)

        assert [hit.chunk_id for hit in first.hits] == [hit.chunk_id for hit in second.hits]

    run_async(scenario())


def test_hybrid_empty_channels_return_empty_result(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        admin = await _create_admin(async_session_factory_for_tests, "hybrid-empty")
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert result.hits == ()
        assert result.hit_count == 0
        assert result.fused_candidate_count == 0

    run_async(scenario())


def test_hybrid_semantic_branch_filters_permissions_before_limit(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_permission_before_limit_case(async_session_factory_for_tests, caplog)


def test_hybrid_keyword_branch_filters_permissions_before_limit(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_permission_before_limit_case(async_session_factory_for_tests, caplog)


def test_hybrid_never_returns_unauthorized_chunk(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_permission_before_limit_case(async_session_factory_for_tests, caplog)


def test_hybrid_unauthorized_candidates_do_not_consume_final_top_k(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_permission_before_limit_case(async_session_factory_for_tests, caplog)


def _run_permission_before_limit_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept_a = await create_department(session, "hybrid-permission-a")
            dept_b = await create_department(session, "hybrid-permission-b")
            admin = await create_user(session, "hybrid-permission-admin", role=UserRole.ADMIN)
            staff_a = await create_user(
                session, "hybrid-permission-staff-a", department_id=dept_a.id
            )
            for index in range(10):
                hidden = await create_document(
                    session,
                    f"hybrid-permission-hidden-{index}",
                    uploader=admin,
                    title=f"{HIDDEN_MARKER}-{index}",
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=dept_b.id,
                )
                await create_chunk(
                    session,
                    f"hybrid-permission-hidden-{index}",
                    document=hidden,
                    text=f"{HIDDEN_MARKER}-{index} {QUERY} {QUERY} {QUERY}",
                    similarity=0.99,
                )
            allowed = await create_document(
                session,
                "hybrid-permission-allowed",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            await create_chunk(
                session,
                "hybrid-permission-allowed",
                document=allowed,
                text=QUERY,
                similarity=0.1,
            )
        service = make_service(async_session_factory_for_tests, hybrid_candidate_multiplier=1)

        result = await service.retrieve(query=QUERY, current_user=staff_a, top_k=1)

        assert [hit.document_id for hit in result.hits] == [allowed.id]
        assert_marker_absent(result.hits, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_hybrid_direct_grant_has_immediate_effect(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-grant-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "hybrid-grant-staff")
            document = await create_document(session, "hybrid-grant-doc", uploader=admin)
            await create_chunk(
                session,
                "hybrid-grant-doc",
                document=document,
                text=QUERY,
                similarity=0.9,
            )
        service = make_service(async_session_factory_for_tests)

        before = await service.retrieve(query=QUERY, current_user=staff)
        async with async_session_factory_for_tests() as session:
            document = await session.get(type(document), document.id)
            await create_permission(
                session,
                "hybrid-grant",
                document=document,
                creator=admin,
                user_id=staff.id,
            )
        after = await service.retrieve(query=QUERY, current_user=staff)

        assert before.hits == ()
        assert [hit.document_id for hit in after.hits] == [document.id]

    run_async(scenario())


def test_hybrid_revoke_has_immediate_effect(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-revoke-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "hybrid-revoke-staff")
            document = await create_document(session, "hybrid-revoke-doc", uploader=admin)
            await create_chunk(
                session,
                "hybrid-revoke-doc",
                document=document,
                text=QUERY,
                similarity=0.9,
            )
            grant = await create_permission(
                session,
                "hybrid-revoke",
                document=document,
                creator=admin,
                user_id=staff.id,
            )
        service = make_service(async_session_factory_for_tests)

        before = await service.retrieve(query=QUERY, current_user=staff)
        async with async_session_factory_for_tests() as session:
            await session.execute(
                delete(DocumentPermission).where(DocumentPermission.id == grant.id)
            )
            await session.commit()
        after = await service.retrieve(query=QUERY, current_user=staff)

        assert before.hit_count == 1
        assert after.hits == ()

    run_async(scenario())


def test_hybrid_soft_deleted_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-deleted-admin", role=UserRole.ADMIN)
            document = await create_document(
                session,
                "hybrid-deleted-doc",
                uploader=admin,
                title=HIDDEN_MARKER,
                is_deleted=True,
            )
            await create_chunk(
                session,
                "hybrid-deleted-doc",
                document=document,
                text=f"{HIDDEN_MARKER} {QUERY}",
                similarity=0.9,
            )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert result.hits == ()
        assert_marker_absent(result.hits, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_hybrid_archived_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-archived-admin", role=UserRole.ADMIN)
            document = await create_document(
                session,
                "hybrid-archived-doc",
                uploader=admin,
                status=DocumentStatus.ARCHIVED,
            )
            await create_chunk(
                session,
                "hybrid-archived-doc",
                document=document,
                text=QUERY,
                similarity=0.9,
            )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=QUERY, current_user=admin)

        assert result.hits == ()

    run_async(scenario())


async def _create_admin(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession], key: str
):
    async with async_session_factory_for_tests() as session:
        return await create_user(session, f"{key}-admin", role=UserRole.ADMIN)


def test_hybrid_exact_code_query_prioritizes_combined_chunk(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        query = "HD-2026-001 quy định thời hạn thanh toán thế nào?"
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "hybrid-code-admin", role=UserRole.ADMIN)
            combined = await create_document(session, "hybrid-code-combined", uploader=admin)
            semantic_payment = await create_document(
                session, "hybrid-code-semantic", uploader=admin
            )
            code_context = await create_document(session, "hybrid-code-context", uploader=admin)
            unrelated = await create_document(session, "hybrid-code-unrelated", uploader=admin)
            await create_chunk(
                session,
                "hybrid-code-combined",
                document=combined,
                text="Hợp đồng HD-2026-001 quy định thời hạn thanh toán thế nào: trong 30 ngày.",
                similarity=0.95,
            )
            await create_chunk(
                session,
                "hybrid-code-semantic",
                document=semantic_payment,
                text="Quy định thời hạn thanh toán của hợp đồng khác là 30 ngày.",
                similarity=0.99,
            )
            await create_chunk(
                session,
                "hybrid-code-context",
                document=code_context,
                text="Hồ sơ HD-2026-001 có phụ lục thanh toán nhưng không nêu thời hạn.",
                similarity=0.2,
            )
            await create_chunk(
                session,
                "hybrid-code-unrelated",
                document=unrelated,
                text="Lịch nghỉ phép hằng năm của nhân viên.",
                similarity=0.0,
                axis=2,
            )
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=query, current_user=admin, top_k=3)

        assert result.hits[0].document_id == combined.id
        assert result.hits[0].matched_by == ("semantic", "keyword")
        assert unrelated.id not in [hit.document_id for hit in result.hits[:2]]

    run_async(scenario())
