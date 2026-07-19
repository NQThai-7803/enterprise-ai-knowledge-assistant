from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.exceptions import AccessTokenInvalidError, TokenExpiredError
from app.core.security import create_access_token, decode_access_token, utc_now


@pytest.fixture
def token_settings() -> Settings:
    return Settings(
        app_env="test",
        secret_key="test-secret-key-for-access-token-validation-123456789",
        database_url="postgresql+asyncpg://app_user:change-me-for-local-development@localhost:55432/enterprise_ai",
        jwt_issuer="test-issuer",
        jwt_audience="test-audience",
    )


def valid_payload(
    user_id: str, *, issuer: str = "test-issuer", audience: str = "test-audience"
) -> dict[str, object]:
    now = utc_now()
    return {
        "sub": user_id,
        "type": "access",
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=15),
        "iss": issuer,
        "aud": audience,
    }


def test_create_access_token_returns_jwt(token_settings: Settings) -> None:
    token = create_access_token(uuid4(), settings=token_settings)

    assert len(token.split(".")) == 3


def test_access_token_contains_required_claims(token_settings: Settings) -> None:
    user_id = uuid4()
    token = create_access_token(user_id, settings=token_settings)

    payload = jwt.decode(
        token,
        token_settings.secret_key,
        algorithms=["HS256"],
        audience=token_settings.jwt_audience,
        issuer=token_settings.jwt_issuer,
    )

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    for claim in ["jti", "iat", "nbf", "exp", "iss", "aud"]:
        assert claim in payload


def test_access_token_does_not_include_authorization_source_claims(
    token_settings: Settings,
) -> None:
    token = create_access_token(uuid4(), settings=token_settings)

    payload = jwt.decode(
        token,
        token_settings.secret_key,
        algorithms=["HS256"],
        audience=token_settings.jwt_audience,
        issuer=token_settings.jwt_issuer,
    )

    assert "role" not in payload
    assert "permissions" not in payload
    assert "department_id" not in payload


def test_decode_access_token_returns_user_id(token_settings: Settings) -> None:
    user_id = uuid4()
    token = create_access_token(user_id, settings=token_settings)

    payload = decode_access_token(token, settings=token_settings)

    assert payload.user_id == user_id


def test_decode_access_token_rejects_expired_token(token_settings: Settings) -> None:
    token = create_access_token(
        uuid4(),
        settings=token_settings,
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(TokenExpiredError):
        decode_access_token(token, settings=token_settings)


def test_decode_access_token_rejects_wrong_secret(token_settings: Settings) -> None:
    token = create_access_token(uuid4(), settings=token_settings)
    wrong_settings = Settings(
        app_env="test",
        secret_key="different-test-secret-for-access-token-validation-123456789",
        database_url=token_settings.database_url,
        jwt_issuer=token_settings.jwt_issuer,
        jwt_audience=token_settings.jwt_audience,
    )

    with pytest.raises(AccessTokenInvalidError):
        decode_access_token(token, settings=wrong_settings)


def test_decode_access_token_rejects_wrong_audience(token_settings: Settings) -> None:
    payload = valid_payload(str(uuid4()), audience="wrong-audience")
    token = jwt.encode(payload, token_settings.secret_key, algorithm="HS256")

    with pytest.raises(AccessTokenInvalidError):
        decode_access_token(token, settings=token_settings)


def test_decode_access_token_rejects_wrong_issuer(token_settings: Settings) -> None:
    payload = valid_payload(str(uuid4()), issuer="wrong-issuer")
    token = jwt.encode(payload, token_settings.secret_key, algorithm="HS256")

    with pytest.raises(AccessTokenInvalidError):
        decode_access_token(token, settings=token_settings)


def test_decode_access_token_rejects_missing_required_claim(token_settings: Settings) -> None:
    payload = valid_payload(str(uuid4()))
    del payload["jti"]
    token = jwt.encode(payload, token_settings.secret_key, algorithm="HS256")

    with pytest.raises(AccessTokenInvalidError):
        decode_access_token(token, settings=token_settings)


def test_decode_access_token_rejects_non_access_type(token_settings: Settings) -> None:
    payload = valid_payload(str(uuid4()))
    payload["type"] = "refresh"
    token = jwt.encode(payload, token_settings.secret_key, algorithm="HS256")

    with pytest.raises(AccessTokenInvalidError):
        decode_access_token(token, settings=token_settings)
