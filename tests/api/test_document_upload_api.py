from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_document_processing_enqueue, get_document_upload_limits
from app.main import app
from app.models import User, UserRole
from app.services.document_service import DocumentUploadLimits
from app.storage.factory import get_file_storage
from app.storage.local import LocalFileStorage

pytestmark = pytest.mark.integration

PDF_BYTES = b"%PDF-1.7\nminimal pdf bytes"
UPLOAD_URL = "/api/v1/documents/upload"


@pytest.fixture
def upload_storage(api_client: TestClient, tmp_path: Path) -> LocalFileStorage:
    storage = LocalFileStorage(tmp_path)
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_document_upload_limits] = lambda: DocumentUploadLimits(1024, 5)
    return storage


def upload_request(
    api_client: TestClient,
    *,
    headers: dict[str, str] | None = None,
    content: bytes = PDF_BYTES,
    filename: str = "employee-handbook.pdf",
    content_type: str = "application/pdf",
    data: dict[str, Any] | None = None,
) -> Any:
    form_data = {"title": "Employee Handbook", "access_scope": "PRIVATE"}
    if data is not None:
        form_data.update(data)
    return api_client.post(
        UPLOAD_URL,
        headers=headers,
        data=form_data,
        files={"file": (filename, content, content_type)},
    )


def test_upload_requires_authentication(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
) -> None:
    response = upload_request(api_client)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_upload_rejects_staff(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    staff = make_user(role=UserRole.STAFF)

    response = upload_request(api_client, headers=make_auth_headers(staff))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_upload_allows_manager(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    manager = make_user(role=UserRole.MANAGER)

    response = upload_request(api_client, headers=make_auth_headers(manager))

    assert response.status_code == 202


def test_upload_allows_admin(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert response.status_code == 202


def test_valid_upload_returns_202(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert response.status_code == 202
    assert response.json()["data"]["title"] == "Employee Handbook"


def test_valid_upload_enqueues_document_processing_task(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    captured: list[Any] = []
    app.dependency_overrides[get_document_processing_enqueue] = lambda: (
        lambda document_id: captured.append(document_id) or True
    )
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert response.status_code == 202
    assert [str(value) for value in captured] == [response.json()["data"]["id"]]


def test_upload_response_does_not_expose_task_id(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert response.status_code == 202
    assert "task_id" not in response.json()["data"]
    assert "queue" not in response.json()["data"]


def test_upload_response_status_is_uploaded(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert response.json()["data"]["status"] == "UPLOADED"


def test_upload_response_does_not_contain_storage_key(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert "storage_key" not in response.json()["data"]


def test_upload_response_does_not_contain_checksum(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert "checksum_sha256" not in response.json()["data"]


def test_upload_response_does_not_contain_absolute_path(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
    tmp_path: Path,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert str(tmp_path) not in response.text
    assert "absolute_path" not in response.text


def test_non_pdf_extension_returns_415(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        filename="employee.txt",
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_wrong_mime_returns_415(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        content_type="text/plain",
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_wrong_signature_returns_415(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        content=b"not-pdf",
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_empty_file_returns_400(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin), content=b"")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_oversized_file_returns_413(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    app.dependency_overrides[get_document_upload_limits] = lambda: DocumentUploadLimits(8, 5)

    response = upload_request(api_client, headers=make_auth_headers(admin))

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_duplicate_file_returns_409(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    headers = make_auth_headers(admin)
    first = upload_request(api_client, headers=headers)
    assert first.status_code == 202

    response = upload_request(api_client, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_DOCUMENT"


def test_blank_title_returns_422(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        data={"title": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_department_scope_requires_department(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        data={"access_scope": "DEPARTMENT"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_manager_other_department_returns_403(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_department: Any,
    make_auth_headers: Any,
) -> None:
    own_department = make_department()
    other_department = make_department()
    manager = make_user(role=UserRole.MANAGER, department_id=own_department.id)

    response = upload_request(
        api_client,
        headers=make_auth_headers(manager),
        data={"access_scope": "DEPARTMENT", "department_id": str(other_department.id)},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_manager_organization_scope_returns_403(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    manager: User = make_user(role=UserRole.MANAGER)

    response = upload_request(
        api_client,
        headers=make_auth_headers(manager),
        data={"access_scope": "ORGANIZATION"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
