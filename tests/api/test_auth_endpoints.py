from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, hash_refresh_token, utc_now
from app.db.session import get_db_session
from app.main import app
from app.models import RefreshToken, User, UserRole

pytestmark = pytest.mark.integration


@pytest.fixture
def api_client(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> Iterator[TestClient]:
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with async_session_factory_for_tests() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


async def create_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str | None = None,
    password: str = "valid auth password",
    is_active: bool = True,
) -> User:
    async with session_factory() as session:
        user = User(
            email=email or f"api-{uuid.uuid4()}@example.com",
            full_name="API User",
            hashed_password=hash_password(password),
            role=UserRole.STAFF,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_refresh_token_row(
    session_factory: async_sessionmaker[AsyncSession],
    raw_token: str,
) -> RefreshToken | None:
    async with session_factory() as session:
        return await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        )


async def set_user_active(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    *,
    is_active: bool,
) -> None:
    async with session_factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.is_active = is_active
        await session.commit()


def create_test_user(
    session_factory: async_sessionmaker[AsyncSession],
    **kwargs: object,
) -> User:
    return asyncio.run(create_user(session_factory, **kwargs))


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def login(
    api_client: TestClient, *, email: str, password: str = "valid auth password"
) -> dict[str, object]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_login_endpoint_returns_token_pair(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-login@example.com")

    data = login(api_client, email="api-login@example.com")

    assert len(str(data["access_token"]).split(".")) == 3
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    assert data["user"]["email"] == "api-login@example.com"
    assert "hashed_password" not in data["user"]


def test_wrong_password_returns_invalid_credentials(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-wrong-password@example.com")

    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "api-wrong-password@example.com", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_unknown_email_returns_same_invalid_credentials(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown-api@example.com", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "INVALID_CREDENTIALS",
        "message": "Email or password is incorrect.",
        "details": None,
        "request_id": None,
    }


def test_login_error_does_not_enumerate_user(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(
        async_session_factory_for_tests,
        email="api-login-enumeration@example.com",
    )

    wrong_password = api_client.post(
        "/api/v1/auth/login",
        json={"email": "api-login-enumeration@example.com", "password": "wrong password"},
    )
    unknown_email = api_client.post(
        "/api/v1/auth/login",
        json={"email": "api-login-enumeration-missing@example.com", "password": "wrong password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["error"] == unknown_email.json()["error"]


def test_inactive_user_cannot_login(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(
        async_session_factory_for_tests,
        email="api-inactive-login@example.com",
        is_active=False,
    )

    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "api-inactive-login@example.com", "password": "valid auth password"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_INACTIVE"


def test_refresh_endpoint_rotates_refresh_token(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-refresh@example.com")
    original = login(api_client, email="api-refresh@example.com")

    response = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original["refresh_token"]},
    )

    assert response.status_code == 200
    refreshed = response.json()["data"]
    assert refreshed["refresh_token"] != original["refresh_token"]
    old_row = asyncio.run(
        get_refresh_token_row(async_session_factory_for_tests, str(original["refresh_token"]))
    )
    new_row = asyncio.run(
        get_refresh_token_row(async_session_factory_for_tests, str(refreshed["refresh_token"]))
    )
    assert old_row is not None
    assert old_row.revoked_at is not None
    assert new_row is not None
    assert new_row.revoked_at is None


def test_access_token_cannot_be_used_as_refresh(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-access-as-refresh@example.com")
    token_pair = login(api_client, email="api-access-as-refresh@example.com")

    response = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_pair["access_token"]},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


def test_refresh_token_cannot_be_used_as_access(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-refresh-as-access@example.com")
    token_pair = login(api_client, email="api-refresh-as-access@example.com")

    response = api_client.get(
        "/api/v1/auth/me",
        headers=auth_headers(str(token_pair["refresh_token"])),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_none_algorithm_rejected(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_user(async_session_factory_for_tests, email="api-none-alg@example.com")
    settings = get_settings()
    now = utc_now()
    token = jwt.encode(
        {
            "sub": str(user.id),
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=15),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        key="",
        algorithm="none",
    )

    response = api_client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_inactive_user_refresh_rejected(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_user(
        async_session_factory_for_tests,
        email="api-inactive-refresh@example.com",
    )
    token_pair = login(api_client, email="api-inactive-refresh@example.com")
    asyncio.run(set_user_active(async_session_factory_for_tests, user.id, is_active=False))

    response = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_INACTIVE"


def test_old_refresh_token_cannot_be_reused(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-refresh-reuse@example.com")
    original = login(api_client, email="api-refresh-reuse@example.com")
    first_refresh = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original["refresh_token"]},
    )
    assert first_refresh.status_code == 200

    second_refresh = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original["refresh_token"]},
    )

    assert second_refresh.status_code == 401
    assert second_refresh.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


def test_revoked_refresh_token_is_rejected(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-revoked-refresh@example.com")
    token_pair = login(api_client, email="api-revoked-refresh@example.com")
    logout_response = api_client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(str(token_pair["access_token"])),
        json={"refresh_token": token_pair["refresh_token"]},
    )
    assert logout_response.status_code == 204

    refresh_response = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


def test_me_returns_current_user(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_user(async_session_factory_for_tests, email="api-me@example.com")
    token_pair = login(api_client, email="api-me@example.com")

    response = api_client.get(
        "/api/v1/auth/me",
        headers=auth_headers(str(token_pair["access_token"])),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(user.id)
    assert data["email"] == "api-me@example.com"
    assert data["department_id"] is None


def test_me_does_not_return_hashed_password(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-me-no-hash@example.com")
    token_pair = login(api_client, email="api-me-no-hash@example.com")

    response = api_client.get(
        "/api/v1/auth/me",
        headers=auth_headers(str(token_pair["access_token"])),
    )

    assert response.status_code == 200
    assert "hashed_password" not in response.json()["data"]


def test_me_requires_bearer_token(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_me_rejects_invalid_access_token(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/auth/me",
        headers=auth_headers("not-a-jwt"),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_me_rejects_expired_access_token(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_user(async_session_factory_for_tests, email="api-expired-access@example.com")
    expired_token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))

    response = api_client.get(
        "/api/v1/auth/me",
        headers=auth_headers(expired_token),
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_me_rejects_access_token_for_missing_user(api_client: TestClient) -> None:
    token = create_access_token(uuid.uuid4())

    response = api_client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_me_rejects_inactive_user(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    user = create_test_user(
        async_session_factory_for_tests,
        email="api-inactive-me@example.com",
        is_active=False,
    )
    token = create_access_token(user.id)

    response = api_client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_INACTIVE"


def test_logout_revokes_refresh_token(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-logout@example.com")
    token_pair = login(api_client, email="api-logout@example.com")

    response = api_client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(str(token_pair["access_token"])),
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert response.status_code == 204
    stored_token = asyncio.run(
        get_refresh_token_row(async_session_factory_for_tests, str(token_pair["refresh_token"]))
    )
    assert stored_token is not None
    assert stored_token.revoked_at is not None


def test_logged_out_refresh_token_cannot_be_used(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-logout-refresh@example.com")
    token_pair = login(api_client, email="api-logout-refresh@example.com")
    logout_response = api_client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(str(token_pair["access_token"])),
        json={"refresh_token": token_pair["refresh_token"]},
    )
    assert logout_response.status_code == 204

    refresh_response = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


def test_logout_requires_access_token(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-logout-requires-token@example.com")
    token_pair = login(api_client, email="api-logout-requires-token@example.com")

    response = api_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"


def test_user_cannot_logout_another_users_refresh_token(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-user-a@example.com")
    create_test_user(async_session_factory_for_tests, email="api-user-b@example.com")
    user_a_tokens = login(api_client, email="api-user-a@example.com")
    user_b_tokens = login(api_client, email="api-user-b@example.com")

    response = api_client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(str(user_a_tokens["access_token"])),
        json={"refresh_token": user_b_tokens["refresh_token"]},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"
    refresh_response = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user_b_tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200


def test_logout_of_already_revoked_owned_token_is_idempotent(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    create_test_user(async_session_factory_for_tests, email="api-logout-idempotent@example.com")
    token_pair = login(api_client, email="api-logout-idempotent@example.com")

    first_response = api_client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(str(token_pair["access_token"])),
        json={"refresh_token": token_pair["refresh_token"]},
    )
    second_response = api_client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(str(token_pair["access_token"])),
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert first_response.status_code == 204
    assert second_response.status_code == 204
