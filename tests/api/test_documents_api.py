from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_document_upload_limits
from app.main import app
from app.models import (
    Document,
    DocumentAccessScope,
    DocumentPermissionLevel,
    DocumentStatus,
    User,
    UserRole,
)
from app.services.document_service import DocumentUploadLimits
from app.storage.factory import get_file_storage
from app.storage.local import LocalFileStorage

pytestmark = pytest.mark.integration
PDF_BYTES = b"%PDF-1.7\napi document bytes"


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


async def one_chunk(content: bytes) -> AsyncIterator[bytes]:
    yield content


@pytest.fixture
def documents_storage(api_client: TestClient, tmp_path: Path) -> LocalFileStorage:
    storage = LocalFileStorage(tmp_path)
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_document_upload_limits] = lambda: DocumentUploadLimits(1024, 7)
    return storage


async def create_document_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    uploader: User,
    title: str = "API Policy",
    access_scope: DocumentAccessScope = DocumentAccessScope.PRIVATE,
    department_id: uuid.UUID | None = None,
    storage_key: str | None = None,
    is_deleted: bool = False,
) -> Document:
    async with session_factory() as session:
        document = Document(
            title=title,
            description="API searchable description",
            original_filename="api-policy.pdf",
            storage_key=storage_key or f"documents/2026/07/{uuid.uuid4()}.pdf",
            mime_type="application/pdf",
            file_size=len(PDF_BYTES),
            checksum_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            status=DocumentStatus.UPLOADED,
            access_scope=access_scope,
            department_id=department_id,
            uploaded_by=uploader.id,
            is_deleted=is_deleted,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document


def make_document(
    session_factory: async_sessionmaker[AsyncSession],
    **kwargs: object,
) -> Document:
    return run_async(create_document_record(session_factory, **kwargs))


def create_storage_document(
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalFileStorage,
    *,
    uploader: User,
) -> Document:
    async def scenario() -> Document:
        storage_key = f"documents/2026/07/{uuid.uuid4()}.pdf"
        await storage.save(storage_key, one_chunk(PDF_BYTES))
        return await create_document_record(
            session_factory,
            uploader=uploader,
            storage_key=storage_key,
        )

    return run_async(scenario())


def test_documents_list_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/documents")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_documents_list_returns_pagination_meta_and_filters(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    visible = make_document(
        async_session_factory_for_tests,
        uploader=admin,
        title="Searchable Handbook",
        access_scope=DocumentAccessScope.ORGANIZATION,
    )
    make_document(async_session_factory_for_tests, uploader=admin, title="Other", is_deleted=True)

    response = api_client.get(
        "/api/v1/documents?page=1&page_size=20&search=Handbook&status=UPLOADED",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {"page": 1, "page_size": 20, "total": 1, "total_pages": 1}
    assert body["data"][0]["id"] == str(visible.id)
    assert "storage_key" not in body["data"][0]


def test_documents_list_rejects_invalid_sort_and_page_size(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    invalid_sort = api_client.get(
        "/api/v1/documents?sort_by=storage_key",
        headers=make_auth_headers(admin),
    )
    invalid_page_size = api_client.get(
        "/api/v1/documents?page_size=101",
        headers=make_auth_headers(admin),
    )

    assert invalid_sort.status_code == 422
    assert invalid_sort.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid_page_size.status_code == 422
    assert invalid_page_size.json()["error"]["code"] == "VALIDATION_ERROR"


def test_document_detail_status_and_inaccessible_document_returns_404(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF)
    visible = make_document(
        async_session_factory_for_tests,
        uploader=admin,
        access_scope=DocumentAccessScope.ORGANIZATION,
    )
    hidden = make_document(async_session_factory_for_tests, uploader=admin)

    detail = api_client.get(f"/api/v1/documents/{visible.id}", headers=make_auth_headers(staff))
    status_response = api_client.get(
        f"/api/v1/documents/{visible.id}/status",
        headers=make_auth_headers(staff),
    )
    inaccessible = api_client.get(
        f"/api/v1/documents/{hidden.id}",
        headers=make_auth_headers(staff),
    )

    assert detail.status_code == 200
    assert status_response.status_code == 200
    assert "checksum_sha256" not in detail.json()["data"]
    assert inaccessible.status_code == 404
    assert inaccessible.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_status_endpoint_reflects_pipeline_statuses_without_internal_content(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    document = make_document(async_session_factory_for_tests, uploader=admin)

    async def set_status(status: DocumentStatus, error_message: str | None = None) -> None:
        async with async_session_factory_for_tests() as session:
            saved = await session.get(Document, document.id)
            assert saved is not None
            saved.status = status
            saved.error_message = error_message
            await session.commit()

    for status_value in (
        DocumentStatus.UPLOADED,
        DocumentStatus.PROCESSING,
        DocumentStatus.READY,
        DocumentStatus.FAILED,
    ):
        error_message = (
            "The document processing operation failed."
            if status_value == DocumentStatus.FAILED
            else None
        )
        run_async(set_status(status_value, error_message))
        response = api_client.get(
            f"/api/v1/documents/{document.id}/status",
            headers=make_auth_headers(admin),
        )
        body = response.json()["data"]

        assert response.status_code == 200
        assert body["status"] == status_value.value
        assert "chunks" not in body
        assert "embedding" not in body
        assert "traceback" not in response.text.lower()
        assert "CONFIDENTIAL_PIPELINE_TEST_MARKER" not in response.text


def test_document_download_returns_200_with_secure_headers(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    uploader = make_user(role=UserRole.STAFF)
    document = create_storage_document(
        async_session_factory_for_tests,
        documents_storage,
        uploader=uploader,
    )

    response = api_client.get(
        f"/api/v1/documents/{document.id}/download",
        headers=make_auth_headers(uploader),
    )

    assert response.status_code == 200
    assert response.content == PDF_BYTES
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    assert str(documents_storage.root_path) not in response.text


def test_document_patch_and_delete(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    document = make_document(async_session_factory_for_tests, uploader=admin)

    patch = api_client.patch(
        f"/api/v1/documents/{document.id}",
        headers=make_auth_headers(admin),
        json={"title": "Updated API Title"},
    )
    delete = api_client.delete(f"/api/v1/documents/{document.id}", headers=make_auth_headers(admin))
    detail_after_delete = api_client.get(
        f"/api/v1/documents/{document.id}",
        headers=make_auth_headers(admin),
    )

    assert patch.status_code == 200
    assert patch.json()["data"]["title"] == "Updated API Title"
    assert delete.status_code == 204
    assert delete.content == b""
    assert detail_after_delete.status_code == 404


def test_staff_patch_and_delete_are_rejected(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF)
    document = make_document(
        async_session_factory_for_tests,
        uploader=admin,
        access_scope=DocumentAccessScope.ORGANIZATION,
    )

    patch = api_client.patch(
        f"/api/v1/documents/{document.id}",
        headers=make_auth_headers(staff),
        json={"title": "Nope"},
    )
    delete = api_client.delete(f"/api/v1/documents/{document.id}", headers=make_auth_headers(staff))

    assert patch.status_code == 403
    assert patch.json()["error"]["code"] == "FORBIDDEN"
    assert delete.status_code == 403
    assert delete.json()["error"]["code"] == "FORBIDDEN"


def test_permission_endpoints_require_admin(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    manager = make_user(role=UserRole.MANAGER)
    document = make_document(async_session_factory_for_tests, uploader=admin)

    response = api_client.get(
        f"/api/v1/documents/{document.id}/permissions",
        headers=make_auth_headers(manager),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_permission_create_patch_delete(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF)
    document = make_document(async_session_factory_for_tests, uploader=admin)
    headers = make_auth_headers(admin)

    created = api_client.post(
        f"/api/v1/documents/{document.id}/permissions",
        headers=headers,
        json={"user_id": str(staff.id), "permission": "VIEW"},
    )
    permission_id = created.json()["data"]["id"]
    listed = api_client.get(f"/api/v1/documents/{document.id}/permissions", headers=headers)
    patched = api_client.patch(
        f"/api/v1/documents/{document.id}/permissions/{permission_id}",
        headers=headers,
        json={"permission": "MANAGE"},
    )
    deleted = api_client.delete(
        f"/api/v1/documents/{document.id}/permissions/{permission_id}",
        headers=headers,
    )

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json()["data"][0]["id"] == permission_id
    assert patched.status_code == 200
    assert patched.json()["data"]["permission"] == DocumentPermissionLevel.MANAGE
    assert deleted.status_code == 204
    assert deleted.content == b""


def test_duplicate_permission_returns_409(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF)
    document = make_document(async_session_factory_for_tests, uploader=admin)
    headers = make_auth_headers(admin)
    payload = {"user_id": str(staff.id), "permission": "VIEW"}

    first = api_client.post(
        f"/api/v1/documents/{document.id}/permissions",
        headers=headers,
        json=payload,
    )
    duplicate = api_client.post(
        f"/api/v1/documents/{document.id}/permissions",
        headers=headers,
        json=payload,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DOCUMENT_PERMISSION_ALREADY_EXISTS"


def test_permission_update_cannot_change_grantee(
    api_client: TestClient,
    documents_storage: LocalFileStorage,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF)
    document = make_document(async_session_factory_for_tests, uploader=admin)
    headers = make_auth_headers(admin)
    created = api_client.post(
        f"/api/v1/documents/{document.id}/permissions",
        headers=headers,
        json={"user_id": str(staff.id), "permission": "VIEW"},
    )

    response = api_client.patch(
        f"/api/v1/documents/{document.id}/permissions/{created.json()['data']['id']}",
        headers=headers,
        json={"permission": "EDIT", "user_id": str(admin.id)},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
