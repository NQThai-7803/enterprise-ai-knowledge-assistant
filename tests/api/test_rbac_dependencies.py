from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_current_user, require_admin, require_manager_or_admin
from app.core.exceptions import ApplicationError, application_error_handler
from app.core.security import hash_password
from app.db.session import get_db_session
from app.main import create_app
from app.models import User, UserRole

PASSWORD = "valid auth password"


def make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"rbac-{uuid.uuid4()}@example.com",
        full_name="RBAC Test User",
        hashed_password="not-used-by-dependency-override",
        role=role,
        is_active=True,
    )


def create_test_router() -> APIRouter:
    router = APIRouter()

    @router.get("/test/authenticated")
    def authenticated(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id), "role": current_user.role.value}

    @router.get("/test/admin")
    def admin(
        current_user: Annotated[User, Depends(require_admin)],
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id), "role": current_user.role.value}

    @router.get("/test/manager-or-admin")
    def manager_or_admin(
        current_user: Annotated[User, Depends(require_manager_or_admin)],
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id), "role": current_user.role.value}

    return router


def create_dependency_test_app(current_user: User | None = None) -> FastAPI:
    application = FastAPI()
    application.add_exception_handler(ApplicationError, application_error_handler)
    application.include_router(create_test_router())

    async def fake_db_session() -> AsyncIterator[object]:
        yield object()

    application.dependency_overrides[get_db_session] = fake_db_session
    if current_user is not None:
        application.dependency_overrides[get_current_user] = lambda: current_user
    return application


def get_with_user(path: str, user: User) -> tuple[int, dict[str, object]]:
    with TestClient(create_dependency_test_app(user)) as client:
        response = client.get(path)
    return response.status_code, response.json()


def get_without_token(path: str) -> tuple[int, dict[str, object], str | None]:
    with TestClient(create_dependency_test_app()) as client:
        response = client.get(path)
    return response.status_code, response.json(), response.headers.get("www-authenticate")


def assert_forbidden_response(payload: dict[str, object]) -> None:
    assert payload["error"] == {
        "code": "FORBIDDEN",
        "message": "You do not have permission to perform this action.",
        "details": None,
        "request_id": None,
    }


def test_authenticated_route_allows_admin() -> None:
    status_code, payload = get_with_user("/test/authenticated", make_user(UserRole.ADMIN))

    assert status_code == 200
    assert payload["role"] == "ADMIN"


def test_authenticated_route_allows_manager() -> None:
    status_code, payload = get_with_user("/test/authenticated", make_user(UserRole.MANAGER))

    assert status_code == 200
    assert payload["role"] == "MANAGER"


def test_authenticated_route_allows_staff() -> None:
    status_code, payload = get_with_user("/test/authenticated", make_user(UserRole.STAFF))

    assert status_code == 200
    assert payload["role"] == "STAFF"


def test_admin_route_allows_admin() -> None:
    status_code, payload = get_with_user("/test/admin", make_user(UserRole.ADMIN))

    assert status_code == 200
    assert payload["role"] == "ADMIN"


def test_admin_route_returns_403_for_manager() -> None:
    status_code, payload = get_with_user("/test/admin", make_user(UserRole.MANAGER))

    assert status_code == 403
    assert_forbidden_response(payload)


def test_admin_route_returns_403_for_staff() -> None:
    status_code, payload = get_with_user("/test/admin", make_user(UserRole.STAFF))

    assert status_code == 403
    assert_forbidden_response(payload)


def test_admin_route_returns_401_without_token() -> None:
    status_code, payload, authenticate_header = get_without_token("/test/admin")

    assert status_code == 401
    assert authenticate_header == "Bearer"
    assert payload["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_manager_route_allows_admin() -> None:
    status_code, payload = get_with_user("/test/manager-or-admin", make_user(UserRole.ADMIN))

    assert status_code == 200
    assert payload["role"] == "ADMIN"


def test_manager_route_allows_manager() -> None:
    status_code, payload = get_with_user("/test/manager-or-admin", make_user(UserRole.MANAGER))

    assert status_code == 200
    assert payload["role"] == "MANAGER"


def test_manager_route_returns_403_for_staff() -> None:
    status_code, payload = get_with_user("/test/manager-or-admin", make_user(UserRole.STAFF))

    assert status_code == 403
    assert_forbidden_response(payload)


def test_manager_route_returns_401_without_token() -> None:
    status_code, payload, authenticate_header = get_without_token("/test/manager-or-admin")

    assert status_code == 401
    assert authenticate_header == "Bearer"
    assert payload["error"]["code"] == "ACCESS_TOKEN_INVALID"


@pytest.fixture
def rbac_integration_client(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> Iterator[TestClient]:
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with async_session_factory_for_tests() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    application = create_app()
    application.include_router(create_test_router())
    application.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(application) as client:
        yield client

    application.dependency_overrides.clear()


async def create_database_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    role: UserRole,
    email: str | None = None,
    is_active: bool = True,
) -> User:
    async with session_factory() as session:
        user = User(
            email=email or f"rbac-db-{uuid.uuid4()}@example.com",
            full_name="RBAC Database User",
            hashed_password=hash_password(PASSWORD),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def create_test_database_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    role: UserRole,
    email: str | None = None,
    is_active: bool = True,
) -> User:
    return asyncio.run(
        create_database_user(
            session_factory,
            role=role,
            email=email,
            is_active=is_active,
        )
    )


async def update_database_user_role(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    role: UserRole,
) -> None:
    async with session_factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.role = role
        await session.commit()


def set_database_user_role(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    role: UserRole,
) -> None:
    asyncio.run(update_database_user_role(session_factory, user_id, role))


async def update_database_user_active_status(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    is_active: bool,
) -> None:
    async with session_factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.is_active = is_active
        await session.commit()


def set_database_user_active_status(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    is_active: bool,
) -> None:
    asyncio.run(update_database_user_active_status(session_factory, user_id, is_active))


def login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["data"]["access_token"])


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.integration
def test_admin_route_uses_current_database_role_after_staff_is_promoted(
    rbac_integration_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_database_user(
        async_session_factory_for_tests,
        role=UserRole.STAFF,
        email="rbac-promote@example.com",
    )
    access_token = login(rbac_integration_client, "rbac-promote@example.com")

    denied_response = rbac_integration_client.get(
        "/test/admin",
        headers=auth_headers(access_token),
    )
    assert denied_response.status_code == 403
    assert denied_response.json()["error"]["code"] == "FORBIDDEN"

    set_database_user_role(async_session_factory_for_tests, user.id, UserRole.ADMIN)

    allowed_response = rbac_integration_client.get(
        "/test/admin",
        headers=auth_headers(access_token),
    )
    assert allowed_response.status_code == 200
    assert allowed_response.json()["role"] == "ADMIN"


@pytest.mark.integration
def test_admin_route_uses_current_database_role_after_admin_is_demoted(
    rbac_integration_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_database_user(
        async_session_factory_for_tests,
        role=UserRole.ADMIN,
        email="rbac-demote@example.com",
    )
    access_token = login(rbac_integration_client, "rbac-demote@example.com")

    allowed_response = rbac_integration_client.get(
        "/test/admin",
        headers=auth_headers(access_token),
    )
    assert allowed_response.status_code == 200

    set_database_user_role(async_session_factory_for_tests, user.id, UserRole.STAFF)

    denied_response = rbac_integration_client.get(
        "/test/admin",
        headers=auth_headers(access_token),
    )
    assert denied_response.status_code == 403
    assert denied_response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.integration
def test_authenticated_route_rechecks_inactive_user_after_token_issue(
    rbac_integration_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_database_user(
        async_session_factory_for_tests,
        role=UserRole.STAFF,
        email="rbac-deactivate@example.com",
    )
    access_token = login(rbac_integration_client, "rbac-deactivate@example.com")

    set_database_user_active_status(async_session_factory_for_tests, user.id, False)

    response = rbac_integration_client.get(
        "/test/authenticated",
        headers=auth_headers(access_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_INACTIVE"
