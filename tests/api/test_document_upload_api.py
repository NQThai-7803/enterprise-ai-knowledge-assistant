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
    assert response.json()["error"]["code"] == "DOCUMENT_FILE_TYPE_INVALID"


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
    assert response.json()["error"]["code"] == "DOCUMENT_FILE_TYPE_INVALID"


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
    assert response.json()["error"]["code"] == "DOCUMENT_FILE_SIGNATURE_INVALID"


def test_empty_file_returns_400(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin), content=b"")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DOCUMENT_FILE_EMPTY"


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
    assert response.json()["error"]["code"] == "DOCUMENT_FILE_TOO_LARGE"


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


def test_path_traversal_filename_is_sanitized(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        filename="..\\..\\confidential.pdf",
    )

    assert response.status_code == 202
    assert response.json()["data"]["original_filename"] == "confidential.pdf"
    assert ".." not in response.text


def test_client_filename_does_not_control_storage_path(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    client_filename = "client-controlled.pdf"

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        filename=client_filename,
    )

    saved_files = [path.name for path in upload_storage.root_path.rglob("*.pdf")]
    assert response.status_code == 202
    assert client_filename not in saved_files
    assert saved_files


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "extension"),
    [
        ("scan.png", "image/png", b"\x89PNG\r\n\x1a\nimage body", ".png"),
        ("receipt.jpg", "image/jpeg", b"\xff\xd8\xffimage body", ".jpg"),
        ("receipt.jpeg", "image/jpeg", b"\xff\xd8\xffimage body", ".jpg"),
    ],
)
def test_upload_accepts_supported_image_documents(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
    filename: str,
    content_type: str,
    content: bytes,
    extension: str,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        content=content,
        filename=filename,
        content_type=content_type,
    )

    assert response.status_code == 202
    assert response.json()["data"]["mime_type"] == content_type
    assert response.json()["data"]["original_filename"] == filename
    saved_files = [path.name for path in upload_storage.root_path.rglob(f"*{extension}")]
    assert saved_files
    assert filename not in saved_files


def test_upload_version_fields_are_returned_by_upload_detail_and_list(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    """BR-1: the version fields the UI sends and reads (API_SPEC section 7)."""
    admin = make_user(role=UserRole.ADMIN)
    headers = make_auth_headers(admin)
    fields = {"document_code": " ND-HR-007 ", "document_version": "1.0",
              "effective_from": "2026-09-01"}  # fmt: skip

    response = upload_request(api_client, headers=headers, data=fields)

    assert response.status_code == 202
    uploaded = response.json()["data"]
    expected = {"document_code": "ND-HR-007", "document_version": "1.0",
                "effective_from": "2026-09-01", "effective_to": None,
                "lifecycle_status": "ACTIVE", "supersedes_document_id": None}  # fmt: skip
    assert {key: uploaded[key] for key in expected} == expected
    detail = api_client.get(f"/api/v1/documents/{uploaded['id']}", headers=headers).json()["data"]
    assert {key: detail[key] for key in expected} == expected
    listed = api_client.get("/api/v1/documents", headers=headers).json()["data"]
    assert [{key: d[key] for key in expected} for d in listed if d["id"] == uploaded["id"]] == [
        expected
    ]


def test_upload_effective_to_before_effective_from_returns_422(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(
        api_client,
        headers=make_auth_headers(admin),
        data={"effective_from": "2026-09-01", "effective_to": "2026-08-31"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert not list(upload_storage.root_path.rglob("*.pdf"))


def test_upload_response_names_go_to_admin_only(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    """BR-4 option (a): a Manager's upload response has no name keys; an Admin's has them."""
    manager = make_user(role=UserRole.MANAGER, full_name="Manager An Danh")
    admin = make_user(role=UserRole.ADMIN, full_name="Admin Co Ten")

    as_manager = upload_request(api_client, headers=make_auth_headers(manager))
    as_admin = upload_request(
        api_client, headers=make_auth_headers(admin), content=PDF_BYTES + b"\n%admin"
    )

    assert as_manager.status_code == as_admin.status_code == 202
    managers = as_manager.json()["data"]
    assert managers["uploaded_by_me"] is True
    assert "uploaded_by_name" not in managers and "department_name" not in managers
    assert "Manager An Danh" not in as_manager.text
    admins = as_admin.json()["data"]
    assert (admins["uploaded_by_me"], admins["uploaded_by_name"], admins["department_name"]) == (
        True,
        "Admin Co Ten",
        None,
    )


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"title": "x" * 256}, {"field": "title", "code": "TOO_LONG"}),
        ({"effective_from": "2026-13-01"}, {"field": "effective_from", "code": "INVALID_DATE"}),
        ({"access_scope": "EVERYONE"}, {"field": "access_scope", "code": "INVALID_CHOICE"}),
        ({"access_scope": "DEPARTMENT"}, {"field": "department_id", "code": "REQUIRED"}),
        ({"effective_from": "2026-09-01", "effective_to": "2026-08-31"},
         {"field": "effective_to", "code": "INVALID_RANGE",
          "message": "effective_to must not precede effective_from."}),
    ],
)  # fmt: skip
def test_upload_422_details_name_the_form_field(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
    fields: dict[str, str],
    expected: dict[str, str],
) -> None:
    """BR-10: details is a list of {field, code, message}, the field named as in the form."""
    admin = make_user(role=UserRole.ADMIN)

    response = upload_request(api_client, headers=make_auth_headers(admin), data=fields)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [{k: d[k] for k in expected} for d in error["details"]] == [expected]
    assert all(set(d) == {"field", "code", "message"} for d in error["details"])


def test_upload_missing_field_is_a_required_detail(
    api_client: TestClient,
    upload_storage: LocalFileStorage,
    make_user: Any,
    make_auth_headers: Any,
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    response = api_client.post(
        UPLOAD_URL,
        headers=make_auth_headers(admin),
        data={"title": "Employee Handbook"},
        files={"file": ("employee-handbook.pdf", PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 422
    assert [(d["field"], d["code"]) for d in response.json()["error"]["details"]] == [
        ("access_scope", "REQUIRED")
    ]
