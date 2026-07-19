from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.models import Department, User, UserRole

pytestmark = pytest.mark.integration


def department_body(name: str = "Information Technology", code: str = "IT") -> dict[str, object]:
    return {"name": name, "code": code, "description": "Internal department"}


def test_departments_list_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/departments")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_departments_list_rejects_manager(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)

    response = api_client.get("/api/v1/departments", headers=make_auth_headers(manager))

    assert response.status_code == 403


def test_departments_list_rejects_staff(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)

    response = api_client.get("/api/v1/departments", headers=make_auth_headers(staff))

    assert response.status_code == 403


def test_departments_list_allows_admin(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get("/api/v1/departments", headers=make_auth_headers(admin))

    assert response.status_code == 200


def test_department_create_requires_admin(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)

    response = api_client.post(
        "/api/v1/departments",
        headers=make_auth_headers(manager),
        json=department_body(),
    )

    assert response.status_code == 403


def test_department_update_requires_admin(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)
    department = make_department()

    response = api_client.patch(
        f"/api/v1/departments/{department.id}",
        headers=make_auth_headers(manager),
        json={"name": "Updated Department"},
    )

    assert response.status_code == 403


def test_department_delete_requires_admin(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    manager = make_user(role=UserRole.MANAGER)
    department = make_department()

    response = api_client.delete(
        f"/api/v1/departments/{department.id}",
        headers=make_auth_headers(manager),
    )

    assert response.status_code == 403


def test_departments_list_returns_pagination_meta(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get(
        "/api/v1/departments?page=1&page_size=20",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["meta"]["page"] == 1
    assert response.json()["meta"]["page_size"] == 20


def test_departments_list_searches_name(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    expected = make_department(name="Unique Finance", code="UF")

    response = api_client.get(
        "/api/v1/departments?search=Unique Finance",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(expected.id)]


def test_departments_list_searches_code(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    expected = make_department(name="Operations", code="OPS-SEARCH")

    response = api_client.get(
        "/api/v1/departments?search=OPS-SEARCH",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(expected.id)]


def test_departments_list_sorts_by_allowed_field(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    make_department(name="Beta Department", code="BETA")
    make_department(name="Alpha Department", code="ALPHA")

    response = api_client.get(
        "/api/v1/departments?sort_by=name&sort_order=asc",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names == sorted(names)


def test_departments_list_rejects_invalid_sort_field(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.get(
        "/api/v1/departments?sort_by=description",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_department_returns_201(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    response = api_client.post(
        "/api/v1/departments",
        headers=make_auth_headers(admin),
        json=department_body(code="it"),
    )

    assert response.status_code == 201
    assert response.json()["data"]["code"] == "IT"


def test_patch_department_returns_200(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    department = make_department()

    response = api_client.patch(
        f"/api/v1/departments/{department.id}",
        headers=make_auth_headers(admin),
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["data"]["description"] is None


def test_delete_department_returns_204_without_body(
    api_client: TestClient,
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    department = make_department()

    response = api_client.delete(
        f"/api/v1/departments/{department.id}",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 204
    assert response.content == b""
