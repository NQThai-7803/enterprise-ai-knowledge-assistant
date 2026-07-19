from __future__ import annotations

import uuid
from collections.abc import AsyncIterable

import pytest

from app.core.exceptions import InternalServerError, InvalidFileTypeError
from app.models import Document, DocumentAccessScope, DocumentStatus, User, UserRole
from app.services import document_service as document_service_module
from app.services.document_service import DocumentService, DocumentUploadLimits
from app.storage.local import StorageError

PDF_BYTES = b"%PDF-1.7\nunit upload enqueue"


class FakeUploadFile:
    def __init__(self, content: bytes = PDF_BYTES) -> None:
        self.content = content
        self.filename = "enqueue.pdf"
        self.content_type = "application/pdf"
        self.offset = 0

    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            size = len(self.content) - self.offset
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class FakeStorage:
    def __init__(self, *, fail_save: bool = False) -> None:
        self.fail_save = fail_save
        self.saved_key: str | None = None
        self.saved_content = bytearray()
        self.deleted_keys: list[str] = []

    async def save(self, storage_key: str, chunks: AsyncIterable[bytes]) -> None:
        if self.fail_save:
            raise StorageError("broker secret should not matter")
        self.saved_key = storage_key
        async for chunk in chunks:
            self.saved_content.extend(chunk)

    async def open(self, storage_key: str) -> bytes:
        return bytes(self.saved_content)

    async def exists(self, storage_key: str) -> bool:
        return self.saved_key == storage_key

    async def delete(self, storage_key: str) -> None:
        self.deleted_keys.append(storage_key)


class FakeSession:
    def __init__(self, *, fail_flush: bool = False) -> None:
        self.fail_flush = fail_flush
        self.committed = False
        self.commit_count = 0
        self.rollback_count = 0
        self.refreshed = False
        self.events: list[str] = []

    async def flush(self) -> None:
        self.events.append("flush")
        if self.fail_flush:
            raise RuntimeError("database unavailable")

    async def commit(self) -> None:
        self.events.append("commit")
        self.committed = True
        self.commit_count += 1

    async def rollback(self) -> None:
        self.events.append("rollback")
        self.rollback_count += 1

    async def refresh(self, document: Document) -> None:
        self.events.append("refresh")
        self.refreshed = True


def make_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="enqueue@example.com",
        full_name="Enqueue User",
        hashed_password="not-used",
        role=UserRole.ADMIN,
        is_active=True,
    )


def make_document(**kwargs: object) -> Document:
    values = {
        "id": uuid.uuid4(),
        "title": "Enqueue PDF",
        "description": None,
        "original_filename": "enqueue.pdf",
        "storage_key": "documents/test/enqueue.pdf",
        "mime_type": "application/pdf",
        "file_size": len(PDF_BYTES),
        "checksum_sha256": "0" * 64,
        "status": DocumentStatus.UPLOADED,
        "access_scope": DocumentAccessScope.PRIVATE,
        "department_id": None,
        "uploaded_by": uuid.uuid4(),
        "error_message": None,
        "is_deleted": False,
    }
    values.update(kwargs)
    return Document(**values)


@pytest.fixture(autouse=True)
def patch_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_duplicate(*args, **kwargs):
        return None

    async def create_document(session, **kwargs):
        return make_document(**kwargs)

    monkeypatch.setattr(
        document_service_module.document_repository,
        "get_active_duplicate_by_uploader_and_checksum",
        no_duplicate,
    )
    monkeypatch.setattr(document_service_module.document_repository, "create", create_document)


async def upload_with(
    *,
    session: FakeSession | None = None,
    storage: FakeStorage | None = None,
    enqueue_processing=None,
    content: bytes = PDF_BYTES,
) -> tuple[Document, FakeSession, FakeStorage]:
    fake_session = session or FakeSession()
    fake_storage = storage or FakeStorage()
    service = DocumentService(
        fake_session,
        storage=fake_storage,
        upload_limits=DocumentUploadLimits(1024, 5),
        enqueue_processing=enqueue_processing,
    )
    document = await service.upload_document(
        file=FakeUploadFile(content),
        title="Enqueue PDF",
        description=None,
        access_scope=DocumentAccessScope.PRIVATE,
        department_id=None,
        current_user=make_user(),
    )
    return document, fake_session, fake_storage


@pytest.mark.anyio
async def test_upload_enqueues_document_after_commit() -> None:
    captured: dict[str, object] = {}

    def enqueue(document_id: uuid.UUID) -> bool:
        captured["document_id"] = document_id
        captured["committed"] = session.committed
        captured["events"] = tuple(session.events)
        return True

    session = FakeSession()
    document, _, _ = await upload_with(session=session, enqueue_processing=enqueue)

    assert captured["document_id"] == document.id
    assert captured["committed"] is True
    assert captured["events"] == ("flush", "commit", "refresh")


@pytest.mark.anyio
async def test_upload_does_not_enqueue_before_commit() -> None:
    def enqueue(document_id: uuid.UUID) -> bool:
        assert session.commit_count == 1
        return True

    session = FakeSession()

    await upload_with(session=session, enqueue_processing=enqueue)


@pytest.mark.anyio
async def test_upload_enqueues_only_document_id() -> None:
    captured: list[object] = []

    def enqueue(document_id: uuid.UUID) -> bool:
        captured.append(document_id)
        return True

    document, _, _ = await upload_with(enqueue_processing=enqueue)

    assert captured == [document.id]


@pytest.mark.anyio
async def test_upload_does_not_enqueue_storage_key() -> None:
    captured: list[object] = []

    def enqueue(document_id: uuid.UUID) -> bool:
        captured.append(document_id)
        return True

    document, _, _ = await upload_with(enqueue_processing=enqueue)

    assert document.storage_key not in repr(captured)


@pytest.mark.anyio
async def test_upload_does_not_enqueue_file_content() -> None:
    captured: list[object] = []

    def enqueue(document_id: uuid.UUID) -> bool:
        captured.append(document_id)
        return True

    await upload_with(enqueue_processing=enqueue)

    assert PDF_BYTES.decode("utf-8") not in repr(captured)


@pytest.mark.anyio
async def test_upload_does_not_enqueue_on_validation_failure() -> None:
    called = False

    def enqueue(document_id: uuid.UUID) -> bool:
        nonlocal called
        called = True
        return True

    with pytest.raises(InvalidFileTypeError):
        await upload_with(content=b"not-pdf", enqueue_processing=enqueue)

    assert called is False


@pytest.mark.anyio
async def test_upload_does_not_enqueue_on_storage_failure() -> None:
    called = False

    def enqueue(document_id: uuid.UUID) -> bool:
        nonlocal called
        called = True
        return True

    with pytest.raises(InternalServerError):
        await upload_with(storage=FakeStorage(fail_save=True), enqueue_processing=enqueue)

    assert called is False


@pytest.mark.anyio
async def test_upload_does_not_enqueue_on_database_failure() -> None:
    called = False

    def enqueue(document_id: uuid.UUID) -> bool:
        nonlocal called
        called = True
        return True

    session = FakeSession(fail_flush=True)

    with pytest.raises(InternalServerError):
        await upload_with(session=session, enqueue_processing=enqueue)

    assert called is False


@pytest.mark.anyio
async def test_enqueue_failure_keeps_document_uploaded() -> None:
    def enqueue(document_id: uuid.UUID) -> bool:
        return False

    document, _, _ = await upload_with(enqueue_processing=enqueue)

    assert document.status == DocumentStatus.UPLOADED


@pytest.mark.anyio
async def test_enqueue_exception_keeps_document_uploaded() -> None:
    def enqueue(document_id: uuid.UUID) -> bool:
        raise RuntimeError("redis://secret:password@localhost/1")

    document, _, _ = await upload_with(enqueue_processing=enqueue)

    assert document.status == DocumentStatus.UPLOADED


@pytest.mark.anyio
async def test_enqueue_failure_does_not_delete_file() -> None:
    def enqueue(document_id: uuid.UUID) -> bool:
        return False

    _, _, storage = await upload_with(enqueue_processing=enqueue)

    assert storage.saved_key is not None
    assert storage.deleted_keys == []


@pytest.mark.anyio
async def test_enqueue_failure_does_not_expose_broker_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def enqueue(document_id: uuid.UUID) -> bool:
        raise RuntimeError("redis://secret:password@localhost/1")

    await upload_with(enqueue_processing=enqueue)

    assert "redis://" not in caplog.text
    assert "password" not in caplog.text
