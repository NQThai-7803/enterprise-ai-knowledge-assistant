from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import PyJWTError
from pwdlib import PasswordHash

from app.core.config import Settings, get_settings
from app.core.exceptions import AccessTokenInvalidError, TokenExpiredError

ACCESS_TOKEN_TYPE = "access"
ALLOWED_JWT_ALGORITHMS = ["HS256"]
REFRESH_TOKEN_RANDOM_BYTES = 48

password_hash = PasswordHash.recommended()


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: UUID
    token_id: UUID


def utc_now() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(
    user_id: UUID,
    *,
    settings: Settings | None = None,
    issued_at: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    settings = settings or get_settings()
    now = issued_at or utc_now()
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> AccessTokenPayload:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=ALLOWED_JWT_ALGORITHMS,
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "type", "jti", "iat", "nbf", "exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except PyJWTError as exc:
        raise AccessTokenInvalidError() from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise AccessTokenInvalidError()

    try:
        user_id = UUID(str(payload["sub"]))
        token_id = UUID(str(payload["jti"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AccessTokenInvalidError() from exc

    return AccessTokenPayload(user_id=user_id, token_id=token_id)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_RANDOM_BYTES)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
