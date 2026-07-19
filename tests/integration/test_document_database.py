from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    Department,
    Document,
    DocumentAccessScope,
    DocumentPermission,
    DocumentPermissionLevel,
    DocumentStatus,
    User,
    UserRole,
)

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def checksum(value: str | None = None) -> str:
    if value is not None:
        return value
    return f"{uuid.uuid4().hex}{uuid.uuid4().hex}"


async def _create_user(session: AsyncSession) -> User:
    user = User(
        email=f"document-user-{uuid.uuid4()}@example.com",
        full_name="Document User",
        hashed_password="not-used-by-document-tests",
        role=UserRole.STAFF,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_department(session: AsyncSession) -> Department:
    department = Department(
        name=f"Document Department {uuid.uuid4()}",
        code=f"DOC-{uuid.uuid4().hex[:8]}",
    )
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def _create_document(
    session: AsyncSession,
    *,
    uploader: User,
    access_scope: DocumentAccessScope | None = None,
    department_id: uuid.UUID | None = None,
    storage_key: str | None = None,
    file_size: int = 1024,
    checksum_sha256: str | None = None,
) -> Document:
    document = Document(
        title="Document title",
        description="Document description",
        original_filename="source.pdf",
        storage_key=storage_key or f"documents/2026/07/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=file_size,
        checksum_sha256=checksum(checksum_sha256),
        uploaded_by=uploader.id,
        department_id=department_id,
    )
    if access_scope is not None:
        document.access_scope = access_scope
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def _expect_integrity_error(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


def test_create_private_document_without_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = await _create_document(
                session,
                uploader=uploader,
                access_scope=DocumentAccessScope.PRIVATE,
            )

            assert document.department_id is None
            assert document.access_scope == DocumentAccessScope.PRIVATE

    run_async(scenario())


def test_create_organization_document_without_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = await _create_document(
                session,
                uploader=uploader,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )

            assert document.department_id is None
            assert document.access_scope == DocumentAccessScope.ORGANIZATION

    run_async(scenario())


def test_create_department_document_with_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            department = await _create_department(session)
            document = await _create_document(
                session,
                uploader=uploader,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )

            assert document.department_id == department.id
            assert document.access_scope == DocumentAccessScope.DEPARTMENT

    run_async(scenario())


def test_department_document_without_department_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = Document(
                title="Invalid department document",
                original_filename="source.pdf",
                storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum_sha256=checksum(),
                access_scope=DocumentAccessScope.DEPARTMENT,
                uploaded_by=uploader.id,
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_private_document_with_department_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            department = await _create_department(session)
            document = Document(
                title="Invalid private document",
                original_filename="source.pdf",
                storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum_sha256=checksum(),
                access_scope=DocumentAccessScope.PRIVATE,
                department_id=department.id,
                uploaded_by=uploader.id,
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_organization_document_with_department_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            department = await _create_department(session)
            document = Document(
                title="Invalid organization document",
                original_filename="source.pdf",
                storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum_sha256=checksum(),
                access_scope=DocumentAccessScope.ORGANIZATION,
                department_id=department.id,
                uploaded_by=uploader.id,
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_document_file_size_must_be_positive(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = Document(
                title="Invalid size document",
                original_filename="source.pdf",
                storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
                mime_type="application/pdf",
                file_size=0,
                checksum_sha256=checksum(),
                uploaded_by=uploader.id,
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_document_checksum_must_have_valid_length(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = Document(
                title="Invalid checksum document",
                original_filename="source.pdf",
                storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum_sha256="a" * 63,
                uploaded_by=uploader.id,
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_document_checksum_must_be_lowercase_hex(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = Document(
                title="Invalid checksum document",
                original_filename="source.pdf",
                storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum_sha256="A" * 64,
                uploaded_by=uploader.id,
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_document_storage_key_must_be_unique(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            storage_key = f"documents/2026/07/{uuid.uuid4()}.pdf"
            await _create_document(session, uploader=uploader, storage_key=storage_key)
            document = Document(
                title="Duplicate storage document",
                original_filename="source.pdf",
                storage_key=storage_key,
                mime_type="application/pdf",
                file_size=2048,
                checksum_sha256=checksum(),
                uploaded_by=uploader.id,
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_document_defaults_to_uploaded(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = await _create_document(session, uploader=uploader)

            assert document.status == DocumentStatus.UPLOADED

    run_async(scenario())


def test_document_defaults_to_private(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = await _create_document(session, uploader=uploader)

            assert document.access_scope == DocumentAccessScope.PRIVATE

    run_async(scenario())


def test_document_defaults_to_not_deleted(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = await _create_document(session, uploader=uploader)

            assert document.is_deleted is False

    run_async(scenario())


def test_document_requires_uploader(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            document = Document(
                title="Missing uploader document",
                original_filename="source.pdf",
                storage_key=f"documents/2026/07/{uuid.uuid4()}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum_sha256=checksum(),
            )
            session.add(document)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_create_user_document_permission(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            grantee = await _create_user(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(
                document_id=document.id,
                user_id=grantee.id,
                permission=DocumentPermissionLevel.EDIT,
                created_by=uploader.id,
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            assert permission.user_id == grantee.id
            assert permission.department_id is None
            assert permission.permission == DocumentPermissionLevel.EDIT

    run_async(scenario())


def test_create_department_document_permission(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            department = await _create_department(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(
                document_id=document.id,
                department_id=department.id,
                permission=DocumentPermissionLevel.MANAGE,
                created_by=uploader.id,
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            assert permission.user_id is None
            assert permission.department_id == department.id
            assert permission.permission == DocumentPermissionLevel.MANAGE

    run_async(scenario())


def test_permission_defaults_to_view(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            grantee = await _create_user(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(
                document_id=document.id,
                user_id=grantee.id,
                created_by=uploader.id,
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)

            assert permission.permission == DocumentPermissionLevel.VIEW

    run_async(scenario())


def test_permission_rejects_missing_user_and_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(document_id=document.id, created_by=uploader.id)
            session.add(permission)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_permission_rejects_both_user_and_department(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            grantee = await _create_user(session)
            department = await _create_department(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(
                document_id=document.id,
                user_id=grantee.id,
                department_id=department.id,
                created_by=uploader.id,
            )
            session.add(permission)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_duplicate_user_permission_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            grantee = await _create_user(session)
            document = await _create_document(session, uploader=uploader)
            session.add(
                DocumentPermission(
                    document_id=document.id,
                    user_id=grantee.id,
                    permission=DocumentPermissionLevel.VIEW,
                    created_by=uploader.id,
                )
            )
            await session.commit()
            session.add(
                DocumentPermission(
                    document_id=document.id,
                    user_id=grantee.id,
                    permission=DocumentPermissionLevel.EDIT,
                    created_by=uploader.id,
                )
            )
            await _expect_integrity_error(session)

    run_async(scenario())


def test_duplicate_department_permission_is_rejected(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            department = await _create_department(session)
            document = await _create_document(session, uploader=uploader)
            session.add(
                DocumentPermission(
                    document_id=document.id,
                    department_id=department.id,
                    permission=DocumentPermissionLevel.VIEW,
                    created_by=uploader.id,
                )
            )
            await session.commit()
            session.add(
                DocumentPermission(
                    document_id=document.id,
                    department_id=department.id,
                    permission=DocumentPermissionLevel.MANAGE,
                    created_by=uploader.id,
                )
            )
            await _expect_integrity_error(session)

    run_async(scenario())


def test_permission_requires_creator(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            grantee = await _create_user(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(document_id=document.id, user_id=grantee.id)
            session.add(permission)
            await _expect_integrity_error(session)

    run_async(scenario())


def test_delete_document_cascades_permissions(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            grantee = await _create_user(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(
                document_id=document.id,
                user_id=grantee.id,
                created_by=uploader.id,
            )
            session.add(permission)
            await session.commit()
            permission_id = permission.id

            await session.delete(document)
            await session.commit()

            saved_permission = await session.scalar(
                select(DocumentPermission).where(DocumentPermission.id == permission_id)
            )
            assert saved_permission is None

    run_async(scenario())


def test_delete_department_cascades_department_grants(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            department = await _create_department(session)
            document = await _create_document(session, uploader=uploader)
            permission = DocumentPermission(
                document_id=document.id,
                department_id=department.id,
                created_by=uploader.id,
            )
            session.add(permission)
            await session.commit()
            permission_id = permission.id
            document_id = document.id

            await session.delete(department)
            await session.commit()

            saved_permission = await session.scalar(
                select(DocumentPermission).where(DocumentPermission.id == permission_id)
            )
            saved_document = await session.get(Document, document_id)
            assert saved_permission is None
            assert saved_document is not None

    run_async(scenario())


def test_department_with_scoped_document_cannot_be_deleted(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            uploader = await _create_user(session)
            department = await _create_department(session)
            document = await _create_document(
                session,
                uploader=uploader,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )

            document_id = document.id
            department_id = department.id

            await session.delete(department)
            await _expect_integrity_error(session)

            saved_document = await session.get(Document, document_id)
            saved_department = await session.get(Department, department_id)
            assert saved_document is not None
            assert saved_department is not None

    run_async(scenario())
