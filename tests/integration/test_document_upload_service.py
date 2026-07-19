from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterable, Coroutine
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import (
    BusinessValidationError,
    DuplicateDocumentError,
    EmptyFileError,
    FileTooLargeError,
    InternalServerError,
    InvalidFileTypeError,
    PermissionDeniedError,
)
from app.models import Document, DocumentAccessScope, DocumentStatus, User, UserRole
from app.schemas.document import DocumentUploadResponse
from app.services.document_service import DocumentService, DocumentUploadLimits
from app.storage.local import LocalFileStorage, StorageError

pytestmark = pytest.mark.integration

PDF_BYTES = b"%PDF-1.7\nminimal pdf bytes"
OTHER_PDF_BYTES = b"%PDF-1.7\nother pdf bytes"


class FakeUploadFile:
    def __init__(
        self,
        content: bytes = PDF_BYTES,
        *,
        filename: str = "employee-handbook.pdf",
        content_type: str = "application/pdf",
    ) -> None:
        self.content = content
        self.filename = filename
        self.content_type = content_type
        self.offset = 0

    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            size = len(self.content) - self.offset
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class FailingStorage:
    async def save(self, storage_key: str, chunks: AsyncIterable[bytes]) -> None:
        raise StorageError("simulated storage failure")

    async def open(self, storage_key: str) -> bytes:
        raise StorageError("simulated storage failure")

    async def exists(self, storage_key: str) -> bool:
        return False

    async def delete(self, storage_key: str) -> None:
        return None


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def create_department(session: AsyncSession) -> Any:
    from app.models import Department

    department = Department(
        name=f"Upload Department {uuid.uuid4()}",
        code=f"UP-{uuid.uuid4().hex[:8]}",
    )
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def create_user(
    session: AsyncSession,
    *,
    role: UserRole,
    department_id: uuid.UUID | None = None,
) -> User:
    user = User(
        email=f"upload-{uuid.uuid4()}@example.com",
        full_name="Upload User",
        hashed_password="not-used-by-upload-tests",
        role=role,
        department_id=department_id,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def make_service(
    session: AsyncSession, tmp_path: Path, *, max_bytes: int = 1024
) -> DocumentService:
    return DocumentService(
        session,
        storage=LocalFileStorage(tmp_path),
        upload_limits=DocumentUploadLimits(
            max_upload_size_bytes=max_bytes,
            upload_chunk_size_bytes=5,
        ),
    )


async def upload_document(
    session: AsyncSession,
    tmp_path: Path,
    *,
    current_user: User,
    access_scope: DocumentAccessScope = DocumentAccessScope.PRIVATE,
    department_id: uuid.UUID | None = None,
    content: bytes = PDF_BYTES,
    filename: str = "employee-handbook.pdf",
    content_type: str = "application/pdf",
    max_bytes: int = 1024,
) -> Document:
    return await make_service(session, tmp_path, max_bytes=max_bytes).upload_document(
        file=FakeUploadFile(content, filename=filename, content_type=content_type),
        title="Employee Handbook",
        description="  Internal policy  ",
        access_scope=access_scope,
        department_id=department_id,
        current_user=current_user,
    )


async def count_documents(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Document)) or 0


def stored_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


def test_admin_uploads_private_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            document = await upload_document(session, tmp_path, current_user=admin)

            assert document.access_scope == DocumentAccessScope.PRIVATE
            assert document.department_id is None

    run_async(scenario())


def test_admin_uploads_department_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            admin = await create_user(session, role=UserRole.ADMIN)

            document = await upload_document(
                session,
                tmp_path,
                current_user=admin,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )

            assert document.department_id == department.id

    run_async(scenario())


def test_admin_uploads_organization_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            document = await upload_document(
                session,
                tmp_path,
                current_user=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )

            assert document.access_scope == DocumentAccessScope.ORGANIZATION
            assert document.department_id is None

    run_async(scenario())


def test_manager_uploads_private_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            manager = await create_user(
                session,
                role=UserRole.MANAGER,
                department_id=department.id,
            )

            document = await upload_document(session, tmp_path, current_user=manager)

            assert document.access_scope == DocumentAccessScope.PRIVATE

    run_async(scenario())


def test_manager_uploads_own_department_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            manager = await create_user(
                session,
                role=UserRole.MANAGER,
                department_id=department.id,
            )

            document = await upload_document(
                session,
                tmp_path,
                current_user=manager,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=department.id,
            )

            assert document.department_id == department.id

    run_async(scenario())


def test_manager_cannot_upload_other_department_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            own_department = await create_department(session)
            other_department = await create_department(session)
            manager = await create_user(
                session,
                role=UserRole.MANAGER,
                department_id=own_department.id,
            )

            with pytest.raises(PermissionDeniedError):
                await upload_document(
                    session,
                    tmp_path,
                    current_user=manager,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=other_department.id,
                )

    run_async(scenario())


def test_manager_cannot_upload_organization_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            manager = await create_user(
                session,
                role=UserRole.MANAGER,
                department_id=department.id,
            )

            with pytest.raises(PermissionDeniedError):
                await upload_document(
                    session,
                    tmp_path,
                    current_user=manager,
                    access_scope=DocumentAccessScope.ORGANIZATION,
                )

    run_async(scenario())


def test_manager_without_department_cannot_upload_department_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            department = await create_department(session)
            manager = await create_user(session, role=UserRole.MANAGER)

            with pytest.raises(PermissionDeniedError):
                await upload_document(
                    session,
                    tmp_path,
                    current_user=manager,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=department.id,
                )

    run_async(scenario())


def test_staff_cannot_upload_pdf(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            staff = await create_user(session, role=UserRole.STAFF)

            with pytest.raises(PermissionDeniedError):
                await upload_document(session, tmp_path, current_user=staff)

    run_async(scenario())


def test_upload_creates_document_with_uploaded_status(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            document = await upload_document(session, tmp_path, current_user=admin)

            assert document.status == DocumentStatus.UPLOADED

    run_async(scenario())


def test_upload_sets_current_user_as_uploader(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            document = await upload_document(session, tmp_path, current_user=admin)

            assert document.uploaded_by == admin.id

    run_async(scenario())


def test_upload_stores_file_size(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            document = await upload_document(session, tmp_path, current_user=admin)

            assert document.file_size == len(PDF_BYTES)

    run_async(scenario())


def test_upload_stores_sha256_checksum(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            document = await upload_document(session, tmp_path, current_user=admin)

            assert len(document.checksum_sha256) == 64
            assert document.checksum_sha256 == document.checksum_sha256.lower()

    run_async(scenario())


def test_upload_generates_unique_storage_key(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            first = await upload_document(session, tmp_path, current_user=admin, content=PDF_BYTES)
            second = await upload_document(
                session,
                tmp_path,
                current_user=admin,
                content=OTHER_PDF_BYTES,
            )

            assert first.storage_key != second.storage_key
            assert first.original_filename not in first.storage_key

    run_async(scenario())


def test_upload_file_exists_in_storage(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            storage = LocalFileStorage(tmp_path)
            service = DocumentService(
                session,
                storage=storage,
                upload_limits=DocumentUploadLimits(1024, 5),
            )

            document = await service.upload_document(
                file=FakeUploadFile(),
                title="Employee Handbook",
                description=None,
                access_scope=DocumentAccessScope.PRIVATE,
                department_id=None,
                current_user=admin,
            )

            assert await storage.exists(document.storage_key)

    run_async(scenario())


def test_upload_does_not_expose_storage_key(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            document = await upload_document(session, tmp_path, current_user=admin)

            response = DocumentUploadResponse.from_document(document).model_dump()

            assert "storage_key" not in response
            assert "checksum_sha256" not in response

    run_async(scenario())


def test_upload_rejects_missing_department_for_department_scope(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            with pytest.raises(BusinessValidationError):
                await upload_document(
                    session,
                    tmp_path,
                    current_user=admin,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                )

    run_async(scenario())


def test_upload_rejects_department_for_private_scope(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            department = await create_department(session)

            with pytest.raises(BusinessValidationError):
                await upload_document(
                    session,
                    tmp_path,
                    current_user=admin,
                    department_id=department.id,
                )

    run_async(scenario())


def test_upload_rejects_department_for_organization_scope(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            department = await create_department(session)

            with pytest.raises(BusinessValidationError):
                await upload_document(
                    session,
                    tmp_path,
                    current_user=admin,
                    access_scope=DocumentAccessScope.ORGANIZATION,
                    department_id=department.id,
                )

    run_async(scenario())


def test_invalid_file_does_not_create_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            with pytest.raises(InvalidFileTypeError):
                await upload_document(session, tmp_path, current_user=admin, content=b"not-pdf")

            assert await count_documents(session) == 0

    run_async(scenario())


def test_empty_file_does_not_create_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            with pytest.raises(EmptyFileError):
                await upload_document(session, tmp_path, current_user=admin, content=b"")

            assert await count_documents(session) == 0

    run_async(scenario())


def test_oversized_file_does_not_create_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            with pytest.raises(FileTooLargeError):
                await upload_document(session, tmp_path, current_user=admin, max_bytes=8)

            assert await count_documents(session) == 0

    run_async(scenario())


def test_invalid_file_does_not_leave_stored_file(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            with pytest.raises(InvalidFileTypeError):
                await upload_document(session, tmp_path, current_user=admin, content=b"not-pdf")

            assert stored_files(tmp_path) == []

    run_async(scenario())


def test_duplicate_upload_does_not_create_second_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            await upload_document(session, tmp_path, current_user=admin)

            with pytest.raises(DuplicateDocumentError):
                await upload_document(session, tmp_path, current_user=admin)

            assert await count_documents(session) == 1

    run_async(scenario())


def test_duplicate_upload_removes_new_file(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            await upload_document(session, tmp_path, current_user=admin)

            with pytest.raises(DuplicateDocumentError):
                await upload_document(session, tmp_path, current_user=admin)

            assert len(stored_files(tmp_path)) == 1

    run_async(scenario())


def test_database_failure_removes_stored_file(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)

            async def fail_flush(*args: object, **kwargs: object) -> None:
                raise RuntimeError("simulated database flush failure")

            monkeypatch.setattr(session, "flush", fail_flush)

            with pytest.raises(InternalServerError):
                await upload_document(session, tmp_path, current_user=admin)

            assert stored_files(tmp_path) == []

    run_async(scenario())


def test_storage_failure_does_not_create_document(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, role=UserRole.ADMIN)
            service = DocumentService(
                session,
                storage=FailingStorage(),
                upload_limits=DocumentUploadLimits(1024, 5),
            )

            with pytest.raises(InternalServerError):
                await service.upload_document(
                    file=FakeUploadFile(),
                    title="Employee Handbook",
                    description=None,
                    access_scope=DocumentAccessScope.PRIVATE,
                    department_id=None,
                    current_user=admin,
                )

            assert await count_documents(session) == 0

    run_async(scenario())
