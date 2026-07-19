from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.services.user_service as user_service_module
from app.models import Department, User, UserRole

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fast_hash_for_users_api_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(user_service_module, "hash_password", lambda password: f"hashed:{password}")


def create_user_body(department_id: str) -> dict[str, object]:
    return {
        "email": f"created-{uuid4()}@example.com",
        "full_name": "Created User",
        "password": "StrongPassword123!",
        "role": "STAFF",
        "department_id": department_id,
    }


def test_users_list_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/users")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_users_list_rejects_manager(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)

    response = api_client.get("/api/v1/users", headers=make_auth_headers(manager))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_users_list_rejects_staff(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)

    response = api_client.get("/api/v1/users", headers=make_auth_headers(staff))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_users_list_allows_admin(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get("/api/v1/users", headers=make_auth_headers(admin))

    assert response.status_code == 200


def test_user_create_requires_admin(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department()
    manager = make_user(role=UserRole.MANAGER, department_id=department.id)

    response = api_client.post(
        "/api/v1/users",
        headers=make_auth_headers(manager),
        json=create_user_body(str(department.id)),
    )

    assert response.status_code == 403


def test_user_update_requires_admin(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department()
    manager = make_user(role=UserRole.MANAGER, department_id=department.id)
    target = make_user(role=UserRole.STAFF, department_id=department.id)

    response = api_client.patch(
        f"/api/v1/users/{target.id}",
        headers=make_auth_headers(manager),
        json={"full_name": "Updated"},
    )

    assert response.status_code == 403


def test_user_delete_requires_admin(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department()
    manager = make_user(role=UserRole.MANAGER, department_id=department.id)
    target = make_user(role=UserRole.STAFF, department_id=department.id)

    response = api_client.delete(f"/api/v1/users/{target.id}", headers=make_auth_headers(manager))

    assert response.status_code == 403


def test_user_can_read_own_profile(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(role=UserRole.STAFF)

    response = api_client.get(f"/api/v1/users/{user.id}", headers=make_auth_headers(user))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(user.id)


def test_staff_cannot_read_another_user(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)
    other = make_user(role=UserRole.STAFF)

    response = api_client.get(f"/api/v1/users/{other.id}", headers=make_auth_headers(staff))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_manager_cannot_read_another_user(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)
    other = make_user(role=UserRole.STAFF)

    response = api_client.get(f"/api/v1/users/{other.id}", headers=make_auth_headers(manager))

    assert response.status_code == 404


def test_admin_can_read_any_user(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    other = make_user(role=UserRole.STAFF)

    response = api_client.get(f"/api/v1/users/{other.id}", headers=make_auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(other.id)


def test_users_list_returns_pagination_meta(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get("/api/v1/users?page=1&page_size=20", headers=make_auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["meta"]["page"] == 1
    assert response.json()["meta"]["page_size"] == 20


def test_users_list_filters_by_role(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department()
    admin = make_user(role=UserRole.ADMIN)
    make_user(role=UserRole.STAFF, department_id=department.id)
    make_user(role=UserRole.MANAGER, department_id=department.id)

    response = api_client.get("/api/v1/users?role=STAFF", headers=make_auth_headers(admin))

    assert response.status_code == 200
    assert {item["role"] for item in response.json()["data"]} == {"STAFF"}


def test_users_list_filters_by_department(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department_a = make_department()
    department_b = make_department()
    admin = make_user(role=UserRole.ADMIN)
    expected = make_user(role=UserRole.STAFF, department_id=department_a.id)
    make_user(role=UserRole.STAFF, department_id=department_b.id)

    response = api_client.get(
        f"/api/v1/users?department_id={department_a.id}",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(expected.id)]


def test_users_list_filters_by_active_status(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    inactive = make_user(role=UserRole.STAFF, is_active=False)
    make_user(role=UserRole.STAFF, is_active=True)

    response = api_client.get("/api/v1/users?is_active=false", headers=make_auth_headers(admin))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(inactive.id)]


def test_users_list_searches_email(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    expected = make_user(role=UserRole.STAFF, email="unique-search@example.com")

    response = api_client.get(
        "/api/v1/users?search=unique-search", headers=make_auth_headers(admin)
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(expected.id)]


def test_users_list_searches_full_name(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    expected = make_user(role=UserRole.STAFF, full_name="Unique Search Name")

    response = api_client.get(
        "/api/v1/users?search=Unique Search", headers=make_auth_headers(admin)
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(expected.id)]


def test_users_list_sorts_by_allowed_field(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    make_user(role=UserRole.STAFF, email="b-sort@example.com")
    make_user(role=UserRole.STAFF, email="a-sort@example.com")

    response = api_client.get(
        "/api/v1/users?role=STAFF&sort_by=email&sort_order=asc",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    assert [item["email"] for item in response.json()["data"]] == [
        "a-sort@example.com",
        "b-sort@example.com",
    ]


def test_users_list_rejects_invalid_sort_field(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get(
        "/api/v1/users?sort_by=hashed_password", headers=make_auth_headers(admin)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_users_list_rejects_page_size_over_100(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get("/api/v1/users?page_size=101", headers=make_auth_headers(admin))

    assert response.status_code == 422


def test_create_user_returns_201(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    department = make_department()

    response = api_client.post(
        "/api/v1/users",
        headers=make_auth_headers(admin),
        json=create_user_body(str(department.id)),
    )

    assert response.status_code == 201
    assert response.json()["data"]["role"] == "STAFF"


def test_patch_user_returns_200(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    department = make_department()
    target = make_user(role=UserRole.STAFF, department_id=department.id)

    response = api_client.patch(
        f"/api/v1/users/{target.id}",
        headers=make_auth_headers(admin),
        json={"full_name": "Updated Staff"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Updated Staff"


def test_delete_user_returns_204_without_body(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    department = make_department()
    target = make_user(role=UserRole.STAFF, department_id=department.id)

    response = api_client.delete(f"/api/v1/users/{target.id}", headers=make_auth_headers(admin))

    assert response.status_code == 204
    assert response.content == b""


def test_user_response_never_contains_hashed_password(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    target = make_user(role=UserRole.STAFF)

    response = api_client.get(f"/api/v1/users/{target.id}", headers=make_auth_headers(admin))

    assert response.status_code == 200
    assert "hashed_password" not in response.json()["data"]
    assert "password" not in response.json()["data"]
