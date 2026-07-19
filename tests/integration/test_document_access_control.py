from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Coroutine
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import (
    BusinessValidationError,
    DepartmentHasDocumentsError,
    DocumentFileUnavailableError,
    DocumentPermissionAlreadyExistsError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
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
from app.schemas.document import DocumentPermissionCreate, DocumentPermissionUpdate, DocumentUpdate
from app.services.audit_service import AuditContext
from app.services.department_service import DepartmentService
from app.services.document_permission_service import DocumentPermissionService
from app.services.document_service import DocumentService, DocumentUploadLimits
from app.storage.local import LocalFileStorage

pytestmark = pytest.mark.integration
PDF_BYTES = b"%PDF-1.7\naccess control pdf bytes"


class CountingStorage(LocalFileStorage):
    def __init__(self, root_path: Path) -> None:
        super().__init__(root_path)
        self.open_called = False
        self.iter_chunks_called = False

    async def open(self, storage_key: str) -> bytes:
        self.open_called = True
        return await super().open(storage_key)

    async def iter_chunks(self, storage_key: str, chunk_size: int) -> AsyncIterator[bytes]:
        self.iter_chunks_called = True
        async for chunk in super().iter_chunks(storage_key, chunk_size):
            yield chunk


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def one_chunk(content: bytes) -> AsyncIterator[bytes]:
    yield content


async def create_department(session: AsyncSession) -> Department:
    department = Department(name=f"Department {uuid.uuid4()}", code=f"D{uuid.uuid4().hex[:8]}")
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def create_user(
    session: AsyncSession,
    *,
    role: UserRole,
    department_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        email=f"document-{uuid.uuid4()}@example.com",
        full_name="Document User",
        hashed_password="not-used",
        role=role,
        department_id=department_id,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_document(
    session: AsyncSession,
    *,
    uploader: User,
    title: str = "Accessible Policy",
    description: str | None = "Searchable policy description",
    access_scope: DocumentAccessScope = DocumentAccessScope.PRIVATE,
    department_id: uuid.UUID | None = None,
    storage_key: str | None = None,
    is_deleted: bool = False,
    error_message: str | None = None,
) -> Document:
    document = Document(
        title=title,
        description=description,
        original_filename="policy.pdf",
        storage_key=storage_key or f"documents/2026/07/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=len(PDF_BYTES),
        checksum_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
        status=DocumentStatus.UPLOADED,
        access_scope=access_scope,
        department_id=department_id,
        uploaded_by=uploader.id,
        error_message=error_message,
        is_deleted=is_deleted,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def create_permission(
    session: AsyncSession,
    *,
    document: Document,
    creator: User,
    user_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    permission: DocumentPermissionLevel = DocumentPermissionLevel.VIEW,
) -> DocumentPermission:
    grant = DocumentPermission(
        document_id=document.id,
        user_id=user_id,
        department_id=department_id,
        permission=permission,
        created_by=creator.id,
    )
    session.add(grant)
    await session.commit()
    await session.refresh(grant)
    return grant


async def document_ids_for_user(
    session: AsyncSession,
    user: User,
    **kwargs: object,
) -> set[uuid.UUID]:
    documents, meta = await DocumentService(session).list_documents(
        current_user=user,
        page=1,
        page_size=20,
        search=kwargs.get("search"),
        status=kwargs.get("status"),
        access_scope=kwargs.get("access_scope"),
        department_id=kwargs.get("department_id"),
        sort_by="created_at",
        sort_order="desc",
    )
    assert meta.total == len(documents)
    return {document.id for document in documents}


def test_admin_list_sees_all_non_deleted_documents(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            documents = [
                await create_document(session, uploader=admin),
                await create_document(
                    session,
                    uploader=admin,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=department.id,
                ),
                await create_document(
                    session, uploader=admin, access_scope=DocumentAccessScope.ORGANIZATION
                ),
            ]
            deleted = await create_document(session, uploader=admin, is_deleted=True)

            visible_ids = await document_ids_for_user(session, admin)

            assert visible_ids == {document.id for document in documents}
            assert deleted.id not in visible_ids

    run_async(scenario())


def test_staff_visibility_rules_and_grants(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department_a = await create_department(session)
            department_b = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            staff_a = await create_user(session, role=UserRole.STAFF, department_id=department_a.id)
            staff_b = await create_user(session, role=UserRole.STAFF, department_id=department_b.id)
            org_doc = await create_document(
                session, uploader=admin, access_scope=DocumentAccessScope.ORGANIZATION
            )
            department_a_doc = await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department_a.id,
            )
            department_b_doc = await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department_b.id,
            )
            private_doc = await create_document(session, uploader=admin)
            user_grant_doc = await create_document(session, uploader=admin)
            department_grant_doc = await create_document(session, uploader=admin)
            deleted_doc = await create_document(session, uploader=admin, is_deleted=True)
            await create_permission(
                session,
                document=user_grant_doc,
                creator=admin,
                user_id=staff_a.id,
            )
            await create_permission(
                session,
                document=department_grant_doc,
                creator=admin,
                department_id=department_a.id,
            )

            staff_a_ids = await document_ids_for_user(session, staff_a)
            staff_b_ids = await document_ids_for_user(session, staff_b)

            assert org_doc.id in staff_a_ids
            assert department_a_doc.id in staff_a_ids
            assert user_grant_doc.id in staff_a_ids
            assert department_grant_doc.id in staff_a_ids
            assert department_b_doc.id not in staff_a_ids
            assert private_doc.id not in staff_a_ids
            assert deleted_doc.id not in staff_a_ids
            assert department_b_doc.id in staff_b_ids
            assert department_a_doc.id not in staff_b_ids

    run_async(scenario())


def test_uploader_sees_private_document_and_filters_do_not_leak(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department_a = await create_department(session)
            department_b = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            uploader = await create_user(
                session,
                role=UserRole.STAFF,
                department_id=department_a.id,
            )
            own_private = await create_document(session, uploader=uploader, title="Visible Budget")
            hidden = await create_document(
                session,
                uploader=admin,
                title="Hidden Budget",
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department_b.id,
            )

            visible_ids = await document_ids_for_user(session, uploader, search="Budget")

            assert own_private.id in visible_ids
            assert hidden.id not in visible_ids

    run_async(scenario())


def test_detail_status_and_deleted_authorization(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            staff = await create_user(session, role=UserRole.STAFF)
            visible = await create_document(
                session, uploader=admin, access_scope=DocumentAccessScope.ORGANIZATION
            )
            private = await create_document(session, uploader=admin)
            deleted = await create_document(session, uploader=admin, is_deleted=True)
            status_doc = await create_document(
                session,
                uploader=staff,
                error_message="Sanitized worker error",
            )

            detail = await DocumentService(session).get_document_detail(
                document_id=visible.id, current_user=staff
            )
            status_doc_result = await DocumentService(session).get_document_status(
                document_id=status_doc.id, current_user=staff
            )

            assert detail.id == visible.id
            assert status_doc_result.error_message == "Sanitized worker error"
            with pytest.raises(ResourceNotFoundError):
                await DocumentService(session).get_document_detail(
                    document_id=private.id, current_user=staff
                )
            with pytest.raises(ResourceNotFoundError):
                await DocumentService(session).get_document_status(
                    document_id=deleted.id, current_user=admin
                )

    run_async(scenario())


def test_download_streaming_and_authorization(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            storage = CountingStorage(tmp_path)
            admin = await create_user(session, role=UserRole.ADMIN)
            staff = await create_user(session, role=UserRole.STAFF)
            storage_key = f"documents/2026/07/{uuid.uuid4()}.pdf"
            await storage.save(storage_key, one_chunk(PDF_BYTES))
            document = await create_document(session, uploader=staff, storage_key=storage_key)
            private = await create_document(session, uploader=admin)

            download = await DocumentService(
                session,
                storage=storage,
                upload_limits=DocumentUploadLimits(1024, 7),
            ).get_document_download(document_id=document.id, current_user=staff)
            downloaded = b""
            async for chunk in download.chunks:
                downloaded += chunk

            assert downloaded == PDF_BYTES
            assert download.filename == "policy.pdf"
            assert storage.iter_chunks_called
            assert not storage.open_called
            with pytest.raises(ResourceNotFoundError):
                await DocumentService(
                    session,
                    storage=storage,
                    upload_limits=DocumentUploadLimits(1024, 7),
                ).get_document_download(document_id=private.id, current_user=staff)

    run_async(scenario())


def test_download_missing_file_returns_document_file_unavailable(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            storage = CountingStorage(tmp_path)
            uploader = await create_user(session, role=UserRole.STAFF)
            document = await create_document(session, uploader=uploader)

            with pytest.raises(DocumentFileUnavailableError):
                await DocumentService(
                    session,
                    storage=storage,
                    upload_limits=DocumentUploadLimits(1024, 7),
                ).get_document_download(document_id=document.id, current_user=uploader)

    run_async(scenario())


def test_update_authorization_and_scope_rules(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department_a = await create_department(session)
            department_b = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            manager = await create_user(
                session, role=UserRole.MANAGER, department_id=department_a.id
            )
            staff = await create_user(session, role=UserRole.STAFF)
            same_department = await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department_a.id,
            )
            other_department = await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department_b.id,
            )
            organization = await create_document(
                session, uploader=admin, access_scope=DocumentAccessScope.ORGANIZATION
            )
            same_department_id = same_department.id
            other_department_id = other_department.id
            organization_id = organization.id
            department_b_id = department_b.id

            updated = await DocumentService(session).update_document(
                document_id=same_department_id,
                payload=DocumentUpdate(title="Updated Title"),
                current_user=manager,
            )
            org_updated = await DocumentService(session).update_document(
                document_id=same_department_id,
                payload=DocumentUpdate(access_scope=DocumentAccessScope.ORGANIZATION),
                current_user=admin,
            )

            assert updated.title == "Updated Title"
            assert org_updated.department_id is None
            assert org_updated.access_scope == DocumentAccessScope.ORGANIZATION
            with pytest.raises(ResourceNotFoundError):
                await DocumentService(session).update_document(
                    document_id=other_department_id,
                    payload=DocumentUpdate(title="Nope"),
                    current_user=manager,
                )
            await session.refresh(staff)
            with pytest.raises(PermissionDeniedError):
                await DocumentService(session).update_document(
                    document_id=organization_id,
                    payload=DocumentUpdate(title="Nope"),
                    current_user=staff,
                )
            await session.refresh(manager)
            with pytest.raises(PermissionDeniedError):
                await DocumentService(session).update_document(
                    document_id=organization_id,
                    payload=DocumentUpdate(access_scope=DocumentAccessScope.ORGANIZATION),
                    current_user=manager,
                )
            await session.refresh(manager)
            with pytest.raises(PermissionDeniedError):
                await DocumentService(session).update_document(
                    document_id=organization_id,
                    payload=DocumentUpdate(
                        access_scope=DocumentAccessScope.DEPARTMENT,
                        department_id=department_b_id,
                    ),
                    current_user=manager,
                )

    run_async(scenario())


def test_update_scope_validation_and_storage_metadata_immutable(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            document = await create_document(session, uploader=admin)
            document_id = document.id
            department_id = department.id
            original_storage_key = document.storage_key
            original_checksum = document.checksum_sha256

            with pytest.raises(BusinessValidationError):
                await DocumentService(session).update_document(
                    document_id=document_id,
                    payload=DocumentUpdate(access_scope=DocumentAccessScope.DEPARTMENT),
                    current_user=admin,
                )
            await session.refresh(admin)
            with pytest.raises(BusinessValidationError):
                await DocumentService(session).update_document(
                    document_id=document_id,
                    payload=DocumentUpdate(department_id=department_id),
                    current_user=admin,
                )
            await session.refresh(admin)
            updated = await DocumentService(session).update_document(
                document_id=document_id,
                payload=DocumentUpdate(description=None),
                current_user=admin,
            )

            assert updated.description is None
            assert updated.storage_key == original_storage_key
            assert updated.checksum_sha256 == original_checksum

    run_async(scenario())


def test_soft_delete_hides_document_but_keeps_row_file_and_grants(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            storage = CountingStorage(tmp_path)
            admin = await create_user(session, role=UserRole.ADMIN)
            staff = await create_user(session, role=UserRole.STAFF)
            storage_key = f"documents/2026/07/{uuid.uuid4()}.pdf"
            await storage.save(storage_key, one_chunk(PDF_BYTES))
            document = await create_document(session, uploader=admin, storage_key=storage_key)
            await create_permission(session, document=document, creator=admin, user_id=staff.id)

            await DocumentService(session).soft_delete_document(
                document_id=document.id,
                current_user=admin,
            )
            await DocumentService(session).soft_delete_document(
                document_id=document.id,
                current_user=admin,
            )

            row = await session.get(Document, document.id)
            assert row is not None
            assert row.is_deleted is True
            assert await storage.exists(storage_key)
            assert document.id not in await document_ids_for_user(session, admin)
            assert document.id not in await document_ids_for_user(session, staff)
            with pytest.raises(ResourceNotFoundError):
                await DocumentService(
                    session,
                    storage=storage,
                    upload_limits=DocumentUploadLimits(1024, 7),
                ).get_document_download(document_id=document.id, current_user=staff)

    run_async(scenario())


def test_manager_can_delete_same_department_but_staff_cannot_delete(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            manager = await create_user(session, role=UserRole.MANAGER, department_id=department.id)
            staff = await create_user(session, role=UserRole.STAFF, department_id=department.id)
            manager_doc = await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )
            staff_doc = await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )

            await DocumentService(session).soft_delete_document(
                document_id=manager_doc.id,
                current_user=manager,
            )

            assert (await session.get(Document, manager_doc.id)).is_deleted is True
            with pytest.raises(PermissionDeniedError):
                await DocumentService(session).soft_delete_document(
                    document_id=staff_doc.id,
                    current_user=staff,
                )

    run_async(scenario())


def test_permission_crud_and_immediate_effect(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            staff = await create_user(session, role=UserRole.STAFF)
            document = await create_document(session, uploader=admin)
            service = DocumentPermissionService(session)

            assert document.id not in await document_ids_for_user(session, staff)
            created = await service.create_permission(
                document_id=document.id,
                payload=DocumentPermissionCreate(
                    user_id=staff.id,
                    permission=DocumentPermissionLevel.VIEW,
                ),
                current_user=admin,
            )
            assert document.id in await document_ids_for_user(session, staff)
            listed = await service.list_permissions(document_id=document.id)
            assert [permission.id for permission in listed] == [created.id]

            updated = await service.update_permission(
                document_id=document.id,
                permission_id=created.id,
                payload=DocumentPermissionUpdate(permission=DocumentPermissionLevel.MANAGE),
            )
            assert updated.permission == DocumentPermissionLevel.MANAGE

            await service.delete_permission(document_id=document.id, permission_id=created.id)
            assert document.id not in await document_ids_for_user(session, staff)

    run_async(scenario())


def test_department_grant_and_removed_grant_does_not_remove_scope_access(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            staff = await create_user(session, role=UserRole.STAFF, department_id=department.id)
            private_doc = await create_document(session, uploader=admin)
            scoped_doc = await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )
            service = DocumentPermissionService(session)
            grant = await service.create_permission(
                document_id=private_doc.id,
                payload=DocumentPermissionCreate(
                    department_id=department.id,
                    permission=DocumentPermissionLevel.VIEW,
                ),
                current_user=admin,
            )

            assert private_doc.id in await document_ids_for_user(session, staff)
            await service.delete_permission(document_id=private_doc.id, permission_id=grant.id)
            visible_ids = await document_ids_for_user(session, staff)

            assert private_doc.id not in visible_ids
            assert scoped_doc.id in visible_ids

    run_async(scenario())


def test_permission_create_validation_and_duplicates(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            active_staff = await create_user(session, role=UserRole.STAFF)
            inactive_staff = await create_user(session, role=UserRole.STAFF, is_active=False)
            document = await create_document(session, uploader=admin)
            document_id = document.id
            inactive_staff_id = inactive_staff.id
            service = DocumentPermissionService(session)
            payload = DocumentPermissionCreate(
                user_id=active_staff.id,
                permission=DocumentPermissionLevel.VIEW,
            )

            await service.create_permission(
                document_id=document.id,
                payload=payload,
                current_user=admin,
            )
            with pytest.raises(DocumentPermissionAlreadyExistsError):
                await service.create_permission(
                    document_id=document_id,
                    payload=payload,
                    current_user=admin,
                )
            with pytest.raises(ResourceNotFoundError):
                await service.create_permission(
                    document_id=document_id,
                    payload=DocumentPermissionCreate(
                        user_id=inactive_staff_id,
                        permission=DocumentPermissionLevel.VIEW,
                    ),
                    current_user=admin,
                )
            with pytest.raises(ResourceNotFoundError):
                await service.create_permission(
                    document_id=document_id,
                    payload=DocumentPermissionCreate(
                        department_id=uuid.uuid4(),
                        permission=DocumentPermissionLevel.VIEW,
                    ),
                    current_user=admin,
                )

    run_async(scenario())


def test_duplicate_department_grant_returns_conflict(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            document = await create_document(session, uploader=admin)
            document_id = document.id
            service = DocumentPermissionService(session)
            payload = DocumentPermissionCreate(
                department_id=department.id,
                permission=DocumentPermissionLevel.VIEW,
            )

            await service.create_permission(
                document_id=document.id,
                payload=payload,
                current_user=admin,
            )
            with pytest.raises(DocumentPermissionAlreadyExistsError):
                await service.create_permission(
                    document_id=document_id,
                    payload=payload,
                    current_user=admin,
                )

    run_async(scenario())


def test_department_with_scoped_document_cannot_be_deleted(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)
            await create_document(
                session,
                uploader=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )

            with pytest.raises(DepartmentHasDocumentsError):
                await DepartmentService(session).delete_department(
                    department_id=department.id,
                    current_user=admin,
                    audit_context=AuditContext(),
                )

    run_async(scenario())
