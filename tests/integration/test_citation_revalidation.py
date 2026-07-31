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
from app.repositories.citation_source_repository import get_permitted_ready_chunks_by_ids
from tests.integration.retrieval_helpers import (
    create_chunk,
    create_department,
    create_document,
    create_permission,
    create_user,
)

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def test_citation_revalidation_accepts_current_permission(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "citation-owner", role=UserRole.STAFF)
            grantee = await create_user(session, "citation-grantee", role=UserRole.STAFF)
            document = await create_document(session, "citation-private", uploader=owner)
            chunk = await create_chunk(session, "citation-private", document=document)
            await create_permission(
                session,
                "citation-direct",
                document=document,
                creator=owner,
                user_id=grantee.id,
                permission=DocumentPermissionLevel.VIEW,
            )

            rows = await get_permitted_ready_chunks_by_ids(
                session,
                chunk_ids=(chunk.id,),
                current_user=grantee,
            )

            assert [row.chunk_id for row in rows] == [chunk.id]

    run_async(scenario())


def test_citation_revalidation_rejects_revoked_user_grant(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(session, "citation-revoked-owner", role=UserRole.STAFF)
            grantee = await create_user(session, "citation-revoked-grantee", role=UserRole.STAFF)
            document = await create_document(session, "citation-revoked", uploader=owner)
            chunk = await create_chunk(session, "citation-revoked", document=document)
            grant = await create_permission(
                session,
                "citation-revoked",
                document=document,
                creator=owner,
                user_id=grantee.id,
            )
            await session.execute(
                delete(DocumentPermission).where(DocumentPermission.id == grant.id)
            )
            await session.commit()

            rows = await get_permitted_ready_chunks_by_ids(
                session,
                chunk_ids=(chunk.id,),
                current_user=grantee,
            )

            assert rows == ()

    run_async(scenario())


def test_citation_revalidation_rejects_other_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            dept_a = await create_department(session, "citation-dept-a")
            dept_b = await create_department(session, "citation-dept-b")
            staff_a = await create_user(
                session,
                "citation-staff-a",
                role=UserRole.STAFF,
                department_id=dept_a.id,
            )
            staff_b = await create_user(
                session,
                "citation-staff-b",
                role=UserRole.STAFF,
                department_id=dept_b.id,
            )
            document = await create_document(
                session,
                "citation-dept-doc",
                uploader=staff_b,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=dept_b.id,
            )
            chunk = await create_chunk(session, "citation-dept-doc", document=document)

            rows = await get_permitted_ready_chunks_by_ids(
                session,
                chunk_ids=(chunk.id,),
                current_user=staff_a,
            )

            assert rows == ()

    run_async(scenario())


@pytest.mark.parametrize(
    ("status", "is_deleted"),
    [
        (DocumentStatus.UPLOADED, False),
        (DocumentStatus.PROCESSING, False),
        (DocumentStatus.FAILED, False),
        (DocumentStatus.ARCHIVED, False),
        (DocumentStatus.READY, True),
    ],
)
def test_citation_revalidation_rejects_non_ready_or_deleted_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    status: DocumentStatus,
    is_deleted: bool,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            owner = await create_user(
                session,
                f"citation-state-{status}-{is_deleted}",
                role=UserRole.STAFF,
            )
            document = await create_document(
                session,
                f"citation-state-{status}-{is_deleted}",
                uploader=owner,
                access_scope=DocumentAccessScope.ORGANIZATION,
                status=status,
                is_deleted=is_deleted,
            )
            chunk = await create_chunk(
                session,
                f"citation-state-{status}-{is_deleted}",
                document=document,
            )

            rows = await get_permitted_ready_chunks_by_ids(
                session,
                chunk_ids=(chunk.id,),
                current_user=owner,
            )

            assert rows == ()

    run_async(scenario())
