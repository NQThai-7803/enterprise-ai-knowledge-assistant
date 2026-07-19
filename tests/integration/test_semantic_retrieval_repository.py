from __future__ import annotations

import inspect
from math import nan

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import DocumentAccessScope, DocumentStatus, UserRole
from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.semantic_repository import search_permitted_chunks
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
    row_document_ids,
    run_async,
    search_rows,
)

pytestmark = pytest.mark.integration
HIDDEN_MARKER = "UNAUTHORIZED_RETRIEVAL_MARKER"


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "retrieval_top_k": 2,
        "retrieval_max_top_k": 5,
        "min_relevance_score": 0.0,
        "retrieval_max_query_characters": 4000,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def make_service(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    **settings_overrides: object,
) -> SemanticRetrievalService:
    return SemanticRetrievalService(
        settings=make_settings(**settings_overrides),
        embedding_provider=FakeQueryEmbeddingProvider(),
        session_provider=JitOffSessionProvider(async_session_factory_for_tests),
    )


def test_retrieval_includes_only_ready_documents(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "ready-only-admin", role=UserRole.ADMIN)
            ready = await create_document(session, "ready-only-ready", uploader=admin)
            uploaded = await create_document(
                session, "ready-only-uploaded", uploader=admin, status=DocumentStatus.UPLOADED
            )
            await create_chunk(session, "ready-only-ready", document=ready)
            await create_chunk(session, "ready-only-uploaded", document=uploaded)

            rows = await search_rows(session, user=admin)

            assert row_document_ids(rows) == [ready.id]

    run_async(scenario())


def test_uploaded_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_status_exclusion_case(async_session_factory_for_tests, DocumentStatus.UPLOADED, "uploaded")


def test_processing_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_status_exclusion_case(
        async_session_factory_for_tests, DocumentStatus.PROCESSING, "processing"
    )


def test_failed_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_status_exclusion_case(async_session_factory_for_tests, DocumentStatus.FAILED, "failed")


def test_archived_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_status_exclusion_case(async_session_factory_for_tests, DocumentStatus.ARCHIVED, "archived")


def _run_status_exclusion_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    status: DocumentStatus,
    key: str,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, f"status-{key}-admin", role=UserRole.ADMIN)
            document = await create_document(
                session, f"status-{key}-doc", uploader=admin, status=status
            )
            await create_chunk(session, f"status-{key}-doc", document=document)

            rows = await search_rows(session, user=admin)

            assert rows == ()

    run_async(scenario())


def test_soft_deleted_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "deleted-admin", role=UserRole.ADMIN)
            document = await create_document(
                session, "deleted-doc", uploader=admin, title=HIDDEN_MARKER, is_deleted=True
            )
            await create_chunk(session, "deleted-doc", document=document, text=HIDDEN_MARKER)

            rows = await search_rows(session, user=admin)

            assert rows == ()
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_soft_deleted_document_with_direct_grant_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "deleted-grant-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "deleted-grant-staff")
            document = await create_document(
                session, "deleted-grant-doc", uploader=admin, is_deleted=True
            )
            await create_chunk(session, "deleted-grant-doc", document=document)
            await create_permission(
                session, "deleted-grant", document=document, creator=admin, user_id=staff.id
            )

            rows = await search_rows(session, user=staff)

            assert rows == ()

    run_async(scenario())


def test_ready_document_without_chunks_returns_no_hits(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "empty-ready-admin", role=UserRole.ADMIN)
            await create_document(session, "empty-ready-doc", uploader=admin)

            rows = await search_rows(session, user=admin)

            assert rows == ()

    run_async(scenario())


def test_retrieval_limits_results_to_top_k(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "limit-admin", role=UserRole.ADMIN)
            for index, similarity in enumerate((0.99, 0.98, 0.97)):
                document = await create_document(session, f"limit-doc-{index}", uploader=admin)
                await create_chunk(
                    session, f"limit-doc-{index}", document=document, similarity=similarity
                )

            rows = await search_rows(session, user=admin, top_k=2)

            assert len(rows) == 2

    run_async(scenario())


def test_top_k_is_applied_after_permission_filter(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_permission_before_top_k_case(async_session_factory_for_tests, "topk-after-filter")


def test_unauthorized_nearest_chunks_do_not_consume_top_k(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_permission_before_top_k_case(async_session_factory_for_tests, "topk-unauthorized")


def _run_permission_before_top_k_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession], key: str
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department_a = await create_department(session, f"{key}-a")
            department_b = await create_department(session, f"{key}-b")
            admin = await create_user(session, f"{key}-admin", role=UserRole.ADMIN)
            staff_a = await create_user(session, f"{key}-staff-a", department_id=department_a.id)
            for index in range(10):
                hidden = await create_document(
                    session,
                    f"{key}-hidden-{index}",
                    uploader=admin,
                    title=f"{HIDDEN_MARKER}-{index}",
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=department_b.id,
                )
                await create_chunk(
                    session,
                    f"{key}-hidden-{index}",
                    document=hidden,
                    text=f"{HIDDEN_MARKER}-{index}",
                    similarity=0.99,
                )
            allowed = await create_document(
                session,
                f"{key}-allowed",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            await create_chunk(session, f"{key}-allowed", document=allowed, similarity=0.2)

            rows = await search_rows(session, user=staff_a, top_k=1)

            assert row_document_ids(rows) == [allowed.id]
            assert_marker_absent(rows, HIDDEN_MARKER)

    run_async(scenario())


def test_default_top_k_is_used(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "default-topk-admin", role=UserRole.ADMIN)
            for index in range(3):
                document = await create_document(session, f"default-topk-{index}", uploader=admin)
                await create_chunk(session, f"default-topk-{index}", document=document)
        result = await make_service(async_session_factory_for_tests).retrieve(
            query="top k", current_user=admin
        )

        assert result.hit_count == 2
        assert result.requested_top_k == 2

    run_async(scenario())


def test_custom_top_k_is_used(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "custom-topk-admin", role=UserRole.ADMIN)
            for index in range(2):
                document = await create_document(session, f"custom-topk-{index}", uploader=admin)
                await create_chunk(session, f"custom-topk-{index}", document=document)
        result = await make_service(async_session_factory_for_tests).retrieve(
            query="top k", current_user=admin, top_k=1
        )

        assert result.hit_count == 1
        assert result.requested_top_k == 1

    run_async(scenario())


def test_top_k_one_returns_nearest_permitted_chunk(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "topk-one-admin", role=UserRole.ADMIN)
            near = await create_document(session, "topk-one-near", uploader=admin)
            far = await create_document(session, "topk-one-far", uploader=admin)
            await create_chunk(session, "topk-one-far", document=far, similarity=0.2)
            await create_chunk(session, "topk-one-near", document=near, similarity=0.9)

            rows = await search_rows(session, user=admin, top_k=1)

            assert row_document_ids(rows) == [near.id]

    run_async(scenario())


def test_top_k_above_maximum_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        admin = await _create_service_user(async_session_factory_for_tests, "topk-reject")
        service = make_service(async_session_factory_for_tests)

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(query="top k", current_user=admin, top_k=6)

        assert exc_info.value.code == RetrievalFailureCode.INVALID_RETRIEVAL_TOP_K

    run_async(scenario())


def test_results_below_threshold_are_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_threshold_count_case(async_session_factory_for_tests, 0.49, 0.5, 0, "below")


def test_result_equal_to_threshold_is_included(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_threshold_count_case(async_session_factory_for_tests, 0.5, 0.5, 1, "equal")


def test_threshold_is_applied_in_sql() -> None:
    source = inspect.getsource(search_permitted_chunks)

    assert "cosine_distance <= max_cosine_distance" in source
    assert ".limit(top_k)" in source


def test_high_threshold_returns_empty_result(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_threshold_count_case(async_session_factory_for_tests, 0.9, 1.0, 0, "high")


def test_low_valid_threshold_returns_more_results(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "low-threshold-admin", role=UserRole.ADMIN)
            low = await create_document(session, "low-threshold-low", uploader=admin)
            high = await create_document(session, "low-threshold-high", uploader=admin)
            await create_chunk(session, "low-threshold-low", document=low, similarity=0.2)
            await create_chunk(session, "low-threshold-high", document=high, similarity=0.8)

            low_threshold_rows = await search_rows(session, user=admin, threshold=0.1)
            higher_threshold_rows = await search_rows(session, user=admin, threshold=0.5)

            assert len(low_threshold_rows) == 2
            assert len(higher_threshold_rows) == 1

    run_async(scenario())


def _run_threshold_count_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    similarity: float,
    threshold: float,
    expected_count: int,
    key: str,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, f"threshold-{key}-admin", role=UserRole.ADMIN)
            document = await create_document(session, f"threshold-{key}-doc", uploader=admin)
            await create_chunk(
                session, f"threshold-{key}-doc", document=document, similarity=similarity
            )

            rows = await search_rows(session, user=admin, threshold=threshold)

            assert len(rows) == expected_count

    run_async(scenario())


def test_invalid_negative_threshold_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_invalid_threshold_case(async_session_factory_for_tests, -0.1)


def test_threshold_above_one_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_invalid_threshold_case(async_session_factory_for_tests, 1.1)


def test_nan_threshold_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_invalid_threshold_case(async_session_factory_for_tests, nan)


def _run_invalid_threshold_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession], threshold: float
) -> None:
    async def scenario() -> None:
        admin = await _create_service_user(
            async_session_factory_for_tests, f"threshold-{threshold}"
        )
        service = make_service(async_session_factory_for_tests)

        with pytest.raises(RetrievalError) as exc_info:
            await service.retrieve(
                query="threshold", current_user=admin, min_relevance_score=threshold
            )

        assert exc_info.value.code == RetrievalFailureCode.INVALID_RELEVANCE_THRESHOLD

    run_async(scenario())


def test_results_ordered_by_cosine_distance(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "order-distance-admin", role=UserRole.ADMIN)
            docs = []
            for key, similarity in (("low", 0.7), ("high", 0.9), ("mid", 0.8)):
                document = await create_document(session, f"order-distance-{key}", uploader=admin)
                await create_chunk(
                    session, f"order-distance-{key}", document=document, similarity=similarity
                )
                docs.append((key, document))

            rows = await search_rows(session, user=admin)

            assert row_document_ids(rows) == [docs[1][1].id, docs[2][1].id, docs[0][1].id]

    run_async(scenario())


def test_most_similar_permitted_chunk_is_first(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department_a = await create_department(session, "permitted-first-a")
            department_b = await create_department(session, "permitted-first-b")
            admin = await create_user(session, "permitted-first-admin", role=UserRole.ADMIN)
            staff = await create_user(
                session, "permitted-first-staff", department_id=department_a.id
            )
            hidden = await create_document(
                session,
                "permitted-first-hidden",
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department_b.id,
            )
            allowed_near = await create_document(
                session,
                "permitted-first-near",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            allowed_far = await create_document(
                session,
                "permitted-first-far",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            await create_chunk(session, "permitted-first-hidden", document=hidden, similarity=1.0)
            await create_chunk(
                session, "permitted-first-near", document=allowed_near, similarity=0.8
            )
            await create_chunk(session, "permitted-first-far", document=allowed_far, similarity=0.4)

            rows = await search_rows(session, user=staff)

            assert row_document_ids(rows)[0] == allowed_near.id

    run_async(scenario())


def test_equal_distance_results_use_stable_tie_break(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "stable-tie-admin", role=UserRole.ADMIN)
            for key in ("b", "a", "c"):
                document = await create_document(session, f"stable-tie-{key}", uploader=admin)
                await create_chunk(session, f"stable-tie-{key}", document=document, similarity=0.5)

            rows = await search_rows(session, user=admin)
            ids = row_document_ids(rows)

            assert ids == sorted(ids)

    run_async(scenario())


def test_same_query_produces_stable_order(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "stable-query-admin", role=UserRole.ADMIN)
            for index in range(3):
                document = await create_document(session, f"stable-query-{index}", uploader=admin)
                await create_chunk(
                    session, f"stable-query-{index}", document=document, similarity=0.5
                )

            first = row_document_ids(await search_rows(session, user=admin))
            second = row_document_ids(await search_rows(session, user=admin))

            assert first == second

    run_async(scenario())


def test_retrieval_does_not_reorder_page_metadata(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "page-order-admin", role=UserRole.ADMIN)
            document = await create_document(session, "page-order-doc", uploader=admin)
            await create_chunk(session, "page-order-doc", document=document, page_numbers=(3, 1, 2))

            rows = await search_rows(session, user=admin)

            assert rows[0].page_numbers == (3, 1, 2)

    run_async(scenario())


def test_query_is_parameterized(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "' OR 1=1 --", "parameterized")


def test_sql_like_query_does_not_bypass_permissions(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "' OR 1=1 --", "sql-like")


def test_query_with_quotes_does_not_break_sql(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "what's the policy?", "quotes")


def test_query_with_vietnamese_text_is_supported(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "Chinh sach nghi phep", "vietnamese")


def test_query_with_emoji_does_not_crash(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "leave policy ðŸ™‚", "emoji")


def test_query_text_is_not_logged(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "query-log-admin", role=UserRole.ADMIN)
            document = await create_document(session, "query-log-doc", uploader=admin)
            await create_chunk(session, "query-log-doc", document=document)
        service = make_service(async_session_factory_for_tests)

        await service.retrieve(query="Sensitive query text", current_user=admin)

        assert "Sensitive query text" not in caplog.text

    run_async(scenario())


def _run_query_safety_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession], query: str, key: str
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session, f"query-{key}")
            admin = await create_user(session, f"query-{key}-admin", role=UserRole.ADMIN)
            staff = await create_user(session, f"query-{key}-staff")
            allowed = await create_document(
                session,
                f"query-{key}-allowed",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            hidden = await create_document(
                session,
                f"query-{key}-hidden",
                uploader=admin,
                title=HIDDEN_MARKER,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )
            await create_chunk(session, f"query-{key}-allowed", document=allowed)
            await create_chunk(session, f"query-{key}-hidden", document=hidden, text=HIDDEN_MARKER)
        service = make_service(async_session_factory_for_tests)

        result = await service.retrieve(query=query, current_user=staff)

        assert [hit.document_id for hit in result.hits] == [allowed.id]
        assert HIDDEN_MARKER not in repr(result)
        assert all(HIDDEN_MARKER not in hit.text for hit in result.hits)

    run_async(scenario())


async def _create_service_user(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession], key: str
):
    async with async_session_factory_for_tests() as session:
        return await create_user(session, f"service-{key}", role=UserRole.ADMIN)
