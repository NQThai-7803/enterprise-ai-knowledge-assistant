from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import DocumentAccessScope, DocumentPermissionLevel, UserRole
from tests.integration.retrieval_helpers import (
    assert_marker_absent,
    create_chunk,
    create_department,
    create_document,
    create_permission,
    create_user,
    row_chunk_ids,
    row_document_ids,
    run_async,
    search_rows,
)

pytestmark = pytest.mark.integration
HIDDEN_MARKER = "UNAUTHORIZED_RETRIEVAL_MARKER"


def test_admin_retrieves_all_ready_non_deleted_documents(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session, "admin-all-a")
            admin = await create_user(session, "admin-all", role=UserRole.ADMIN)
            org_doc = await create_document(
                session, "admin-org", uploader=admin, access_scope=DocumentAccessScope.ORGANIZATION
            )
            dept_doc = await create_document(
                session,
                "admin-dept",
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )
            private_doc = await create_document(session, "admin-private", uploader=admin)
            deleted_doc = await create_document(
                session, "admin-deleted", uploader=admin, title=HIDDEN_MARKER, is_deleted=True
            )
            for document in (org_doc, dept_doc, private_doc, deleted_doc):
                await create_chunk(
                    session, f"chunk-{document.id}", document=document, text=document.title
                )

            rows = await search_rows(session, user=admin)

            assert set(row_document_ids(rows)) == {org_doc.id, dept_doc.id, private_doc.id}
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_staff_retrieves_organization_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "org-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "org-staff")
            document = await create_document(
                session,
                "org-visible",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            private = await create_document(
                session, "org-hidden", uploader=admin, title=HIDDEN_MARKER
            )
            await create_chunk(session, "org-visible", document=document)
            await create_chunk(session, "org-hidden", document=private, text=HIDDEN_MARKER)

            rows = await search_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_staff_retrieves_same_department_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session, "same-dept")
            admin = await create_user(session, "same-dept-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "same-dept-staff", department_id=department.id)
            document = await create_document(
                session,
                "same-dept-doc",
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )
            await create_chunk(session, "same-dept-doc", document=document)

            rows = await search_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_staff_does_not_retrieve_other_department_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department_a = await create_department(session, "other-a")
            department_b = await create_department(session, "other-b")
            admin = await create_user(session, "other-admin", role=UserRole.ADMIN)
            staff_a = await create_user(session, "other-staff-a", department_id=department_a.id)
            hidden = await create_document(
                session,
                "other-hidden",
                uploader=admin,
                title=HIDDEN_MARKER,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department_b.id,
            )
            await create_chunk(session, "other-hidden", document=hidden, text=HIDDEN_MARKER)

            rows = await search_rows(session, user=staff_a)

            assert rows == ()
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_staff_retrieves_private_document_with_direct_user_grant(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "user-grant-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "user-grant-staff")
            document = await create_document(session, "user-grant-doc", uploader=admin)
            await create_chunk(session, "user-grant-doc", document=document)
            await create_permission(
                session, "user-grant", document=document, creator=admin, user_id=staff.id
            )

            rows = await search_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_staff_retrieves_document_with_direct_department_grant(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session, "dept-grant")
            admin = await create_user(session, "dept-grant-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "dept-grant-staff", department_id=department.id)
            document = await create_document(session, "dept-grant-doc", uploader=admin)
            await create_chunk(session, "dept-grant-doc", document=document)
            await create_permission(
                session,
                "dept-grant",
                document=document,
                creator=admin,
                department_id=department.id,
            )

            rows = await search_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_uploader_retrieves_own_private_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            staff = await create_user(session, "own-uploader")
            document = await create_document(session, "own-private", uploader=staff)
            await create_chunk(session, "own-private", document=document)

            rows = await search_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_private_document_is_hidden_without_access(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "private-hidden-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "private-hidden-staff")
            document = await create_document(
                session, "private-hidden", uploader=admin, title=HIDDEN_MARKER
            )
            await create_chunk(session, "private-hidden", document=document, text=HIDDEN_MARKER)

            rows = await search_rows(session, user=staff)

            assert rows == ()
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())


def test_user_without_department_does_not_receive_department_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session, "no-dept-target")
            admin = await create_user(session, "no-dept-admin", role=UserRole.ADMIN)
            user = await create_user(session, "no-dept-user")
            document = await create_document(
                session,
                "no-dept-doc",
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )
            await create_chunk(session, "no-dept-doc", document=document)

            rows = await search_rows(session, user=user)

            assert rows == ()

    run_async(scenario())


def test_direct_view_grant_allows_retrieval(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_direct_grant_case(async_session_factory_for_tests, DocumentPermissionLevel.VIEW, "view")


def test_direct_edit_grant_allows_retrieval(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_direct_grant_case(async_session_factory_for_tests, DocumentPermissionLevel.EDIT, "edit")


def test_direct_manage_grant_allows_retrieval(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_direct_grant_case(
        async_session_factory_for_tests, DocumentPermissionLevel.MANAGE, "manage"
    )


def _run_direct_grant_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    permission: DocumentPermissionLevel,
    key: str,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, f"direct-{key}-admin", role=UserRole.ADMIN)
            staff = await create_user(session, f"direct-{key}-staff")
            document = await create_document(session, f"direct-{key}-doc", uploader=admin)
            await create_chunk(session, f"direct-{key}-doc", document=document)
            await create_permission(
                session,
                f"direct-{key}",
                document=document,
                creator=admin,
                user_id=staff.id,
                permission=permission,
            )

            rows = await search_rows(session, user=staff)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_removed_grant_removes_retrieval_access_immediately(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "remove-grant-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "remove-grant-staff")
            document = await create_document(session, "remove-grant-doc", uploader=admin)
            await create_chunk(session, "remove-grant-doc", document=document)
            grant = await create_permission(
                session, "remove-grant", document=document, creator=admin, user_id=staff.id
            )

            assert row_document_ids(await search_rows(session, user=staff)) == [document.id]
            await session.delete(grant)
            await session.commit()
            rows = await search_rows(session, user=staff)

            assert rows == ()

    run_async(scenario())


def test_multiple_access_paths_do_not_duplicate_chunk(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session, "dedupe")
            admin = await create_user(session, "dedupe-admin", role=UserRole.ADMIN)
            staff = await create_user(session, "dedupe-staff", department_id=department.id)
            document = await create_document(
                session,
                "dedupe-doc",
                uploader=staff,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            chunk = await create_chunk(session, "dedupe-doc", document=document)
            await create_permission(
                session, "dedupe-user", document=document, creator=admin, user_id=staff.id
            )
            await create_permission(
                session,
                "dedupe-dept",
                document=document,
                creator=admin,
                department_id=department.id,
            )

            rows = await search_rows(session, user=staff)

            assert row_chunk_ids(rows).count(chunk.id) == 1
            assert row_document_ids(rows) == [document.id]

    run_async(scenario())
