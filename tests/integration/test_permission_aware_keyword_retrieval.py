from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    DocumentAccessScope,
    DocumentPermission,
    DocumentPermissionLevel,
    DocumentStatus,
    UserRole,
)
from app.retrieval.keyword_repository import KeywordRetrievalRow, search_permitted_chunks_by_keyword
from tests.integration.retrieval_helpers import (
    assert_marker_absent,
    create_chunk,
    create_department,
    create_document,
    create_permission,
    create_user,
    disable_postgres_jit,
    row_chunk_ids,
    row_document_ids,
)

pytestmark = pytest.mark.integration
HIDDEN_MARKER = "UNAUTHORIZED_KEYWORD_PERMISSION_MARKER"
QUERY = "permissionkeyword"


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def keyword_rows(
    session: AsyncSession,
    *,
    user,
    query: str = QUERY,
    top_k: int = 20,
) -> tuple[KeywordRetrievalRow, ...]:
    await disable_postgres_jit(session)
    return await search_permitted_chunks_by_keyword(
        session,
        query=query,
        current_user=user,
        top_k=top_k,
        min_keyword_rank=0.0,
    )


def test_keyword_admin_sees_all_ready_non_deleted(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept_a = await create_department(session, "keyword-admin-a")
            dept_b = await create_department(session, "keyword-admin-b")
            admin = await create_user(session, "keyword-admin", role=UserRole.ADMIN)
            docs = [
                await create_document(
                    session,
                    "keyword-admin-org",
                    uploader=admin,
                    access_scope=DocumentAccessScope.ORGANIZATION,
                ),
                await create_document(
                    session,
                    "keyword-admin-dept-a",
                    uploader=admin,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=dept_a.id,
                ),
                await create_document(
                    session,
                    "keyword-admin-dept-b",
                    uploader=admin,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=dept_b.id,
                ),
                await create_document(session, "keyword-admin-private", uploader=admin),
            ]
            deleted = await create_document(
                session,
                "keyword-admin-deleted",
                uploader=admin,
                title=HIDDEN_MARKER,
                is_deleted=True,
            )
            for index, document in enumerate([*docs, deleted]):
                await create_chunk(
                    session,
                    f"keyword-admin-{index}",
                    document=document,
                    text=f"{QUERY} chunk {index}",
                )

            rows = await keyword_rows(session, user=admin)

            assert set(row_document_ids(rows)) == {document.id for document in docs}
            assert_marker_absent(rows, HIDDEN_MARKER)

    run_async(scenario())


def test_keyword_staff_sees_organization(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-org-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-org-staff")
            document = await create_document(
                session,
                "keyword-org-doc",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            await create_chunk(session, "keyword-org-doc", document=document, text=QUERY)

            rows = await keyword_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_keyword_staff_sees_same_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept = await create_department(session, "keyword-same-dept")
            admin = await create_user(session, "keyword-same-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-same-staff", department_id=dept.id)
            document = await create_document(
                session,
                "keyword-same-doc",
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=dept.id,
            )
            await create_chunk(session, "keyword-same-doc", document=document, text=QUERY)

            rows = await keyword_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_keyword_staff_does_not_see_other_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept_a = await create_department(session, "keyword-other-a")
            dept_b = await create_department(session, "keyword-other-b")
            admin = await create_user(session, "keyword-other-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-other-staff", department_id=dept_a.id)
            hidden = await create_document(
                session,
                "keyword-other-hidden",
                uploader=admin,
                title=HIDDEN_MARKER,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=dept_b.id,
            )
            await create_chunk(
                session,
                "keyword-other-hidden",
                document=hidden,
                text=f"{HIDDEN_MARKER} {QUERY}",
            )

            rows = await keyword_rows(session, user=staff)

            assert rows == ()
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_keyword_uploader_sees_own_private_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await create_user(session, "keyword-uploader")
            document = await create_document(session, "keyword-uploader-doc", uploader=uploader)
            await create_chunk(session, "keyword-uploader-doc", document=document, text=QUERY)

            rows = await keyword_rows(session, user=uploader)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_keyword_direct_user_grant_allows_access(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-user-grant-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-user-grant-staff")
            document = await create_document(session, "keyword-user-grant-doc", uploader=admin)
            await create_chunk(session, "keyword-user-grant-doc", document=document, text=QUERY)
            await create_permission(
                session,
                "keyword-user-grant",
                document=document,
                creator=admin,
                user_id=staff.id,
            )

            rows = await keyword_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_keyword_direct_department_grant_allows_access(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept = await create_department(session, "keyword-dept-grant")
            admin = await create_user(session, "keyword-dept-grant-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-dept-grant-staff", department_id=dept.id)
            document = await create_document(session, "keyword-dept-grant-doc", uploader=admin)
            await create_chunk(session, "keyword-dept-grant-doc", document=document, text=QUERY)
            await create_permission(
                session,
                "keyword-dept-grant",
                document=document,
                creator=admin,
                department_id=dept.id,
            )

            rows = await keyword_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_keyword_removed_grant_removes_access(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-revoke-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-revoke-staff")
            document = await create_document(session, "keyword-revoke-doc", uploader=admin)
            await create_chunk(session, "keyword-revoke-doc", document=document, text=QUERY)
            grant = await create_permission(
                session,
                "keyword-revoke-grant",
                document=document,
                creator=admin,
                user_id=staff.id,
            )

            assert row_document_ids(await keyword_rows(session, user=staff)) == [document.id]
            await session.execute(
                delete(DocumentPermission).where(DocumentPermission.id == grant.id)
            )
            await session.commit()

            assert await keyword_rows(session, user=staff) == ()

    run_async(scenario())


def test_keyword_multiple_access_paths_do_not_duplicate_chunk(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept = await create_department(session, "keyword-dedup")
            admin = await create_user(session, "keyword-dedup-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-dedup-staff", department_id=dept.id)
            document = await create_document(
                session,
                "keyword-dedup-doc",
                uploader=staff,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            await create_chunk(session, "keyword-dedup-doc", document=document, text=QUERY)
            await create_permission(
                session,
                "keyword-dedup-user-grant",
                document=document,
                creator=admin,
                user_id=staff.id,
            )
            await create_permission(
                session,
                "keyword-dedup-dept-grant",
                document=document,
                creator=admin,
                department_id=dept.id,
            )

            rows = await keyword_rows(session, user=staff)

            assert len(row_chunk_ids(rows)) == 1
            assert len(set(row_chunk_ids(rows))) == 1

    run_async(scenario())


def test_keyword_soft_deleted_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-deleted-admin", role=UserRole.ADMIN)
            document = await create_document(
                session,
                "keyword-deleted-doc",
                uploader=admin,
                title=HIDDEN_MARKER,
                is_deleted=True,
            )
            await create_chunk(
                session,
                "keyword-deleted-doc",
                document=document,
                text=f"{HIDDEN_MARKER} {QUERY}",
            )

            rows = await keyword_rows(session, user=admin)

            assert rows == ()
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_keyword_archived_document_is_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_non_ready_case(async_session_factory_for_tests, DocumentStatus.ARCHIVED, "archived")


def test_keyword_non_ready_documents_are_excluded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    for status in (DocumentStatus.UPLOADED, DocumentStatus.PROCESSING, DocumentStatus.FAILED):
        _run_non_ready_case(async_session_factory_for_tests, status, status.value.lower())


def _run_non_ready_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    status: DocumentStatus,
    key: str,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, f"keyword-status-{key}-admin", role=UserRole.ADMIN)
            document = await create_document(
                session,
                f"keyword-status-{key}-doc",
                uploader=admin,
                status=status,
            )
            await create_chunk(session, f"keyword-status-{key}-doc", document=document, text=QUERY)

            rows = await keyword_rows(session, user=admin)

            assert rows == ()

    run_async(scenario())


def test_keyword_top_k_permission_filter_runs_before_limit(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept_a = await create_department(session, "keyword-topk-a")
            dept_b = await create_department(session, "keyword-topk-b")
            admin = await create_user(session, "keyword-topk-admin", role=UserRole.ADMIN)
            staff_a = await create_user(session, "keyword-topk-staff-a", department_id=dept_a.id)
            for index in range(10):
                hidden = await create_document(
                    session,
                    f"keyword-topk-hidden-{index}",
                    uploader=admin,
                    title=f"{HIDDEN_MARKER}-{index}",
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=dept_b.id,
                )
                await create_chunk(
                    session,
                    f"keyword-topk-hidden-{index}",
                    document=hidden,
                    text=f"invoice invoice invoice {QUERY} {HIDDEN_MARKER}-{index}",
                )
            allowed = await create_document(
                session,
                "keyword-topk-allowed",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            await create_chunk(
                session, "keyword-topk-allowed", document=allowed, text=f"invoice {QUERY}"
            )

            rows = await keyword_rows(session, user=staff_a, query="invoice", top_k=1)

            assert row_document_ids(rows) == [allowed.id]
            assert_marker_absent(rows, HIDDEN_MARKER)

    run_async(scenario())


def test_keyword_direct_edit_and_manage_grants_allow_access(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-level-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "keyword-level-staff")
            for permission in (DocumentPermissionLevel.EDIT, DocumentPermissionLevel.MANAGE):
                key = permission.value.lower()
                document = await create_document(session, f"keyword-level-{key}", uploader=admin)
                await create_chunk(session, f"keyword-level-{key}", document=document, text=QUERY)
                await create_permission(
                    session,
                    f"keyword-level-{key}",
                    document=document,
                    creator=admin,
                    user_id=staff.id,
                    permission=permission,
                )

            rows = await keyword_rows(session, user=staff)

            assert len(rows) == 2

    run_async(scenario())
