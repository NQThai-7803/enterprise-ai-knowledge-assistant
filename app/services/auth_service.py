from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.audit import AuditEventType, AuditTargetType
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    UserInactiveError,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    utc_now,
    verify_password,
)
from app.models import User
from app.repositories import refresh_token_repository, user_repository
from app.services.audit_service import AuditContext, AuditService


@dataclass(frozen=True)
class AuthTokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def login(
        self,
        *,
        email: str,
        password: str,
        audit_context: AuditContext | None = None,
    ) -> AuthTokenPair:
        normalized_email = email.strip().lower()
        user = await user_repository.get_by_email(self.session, normalized_email)
        await self.session.commit()

        if user is None:
            await self._record_login_failure(
                audit_context=audit_context,
                error_code="INVALID_CREDENTIALS",
            )
            raise InvalidCredentialsError()

        password_is_valid = await run_in_threadpool(
            verify_password,
            password,
            user.hashed_password,
        )
        if not password_is_valid:
            await self._record_login_failure(
                audit_context=audit_context,
                error_code="INVALID_CREDENTIALS",
            )
            raise InvalidCredentialsError()

        if not user.is_active:
            await self._record_login_failure(
                audit_context=audit_context,
                error_code="ACCOUNT_INACTIVE",
            )
            raise UserInactiveError()

        try:
            token_pair = await self._create_token_pair(user)
            await AuditService(self.session, settings=self.settings).record_success(
                actor_user_id=user.id,
                event_type=AuditEventType.AUTH_LOGIN_SUCCEEDED,
                target_type=AuditTargetType.USER,
                target_id=user.id,
                context=audit_context,
                metadata={"role": user.role, "status": "ACTIVE"},
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return token_pair

    async def refresh(self, *, refresh_token: str) -> AuthTokenPair:
        token_hash = hash_refresh_token(refresh_token)
        now = utc_now()

        try:
            stored_token = await refresh_token_repository.get_by_hash_for_update(
                self.session,
                token_hash,
            )
            if stored_token is None:
                raise RefreshTokenInvalidError()
            if stored_token.revoked_at is not None:
                raise RefreshTokenInvalidError()
            if _is_expired(stored_token.expires_at, now):
                raise RefreshTokenInvalidError()

            user = await user_repository.get_by_id(self.session, stored_token.user_id)
            if user is None:
                raise RefreshTokenInvalidError()

            if not user.is_active:
                await refresh_token_repository.revoke(stored_token, revoked_at=now)
                await self.session.commit()
                raise UserInactiveError()

            await refresh_token_repository.revoke(stored_token, revoked_at=now)
            token_pair = await self._create_token_pair(user)
            await self.session.commit()
        except (RefreshTokenInvalidError, UserInactiveError):
            if self.session.in_transaction():
                await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        return token_pair

    async def logout(self, *, refresh_token: str, current_user: User) -> None:
        token_hash = hash_refresh_token(refresh_token)
        now = utc_now()

        try:
            stored_token = await refresh_token_repository.get_by_hash_for_update(
                self.session,
                token_hash,
            )
            if stored_token is None or stored_token.user_id != current_user.id:
                raise RefreshTokenInvalidError()

            await refresh_token_repository.revoke(stored_token, revoked_at=now)
            await self.session.commit()
        except RefreshTokenInvalidError:
            if self.session.in_transaction():
                await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def get_active_user(self, user_id: UUID) -> User:
        user = await user_repository.get_by_id(self.session, user_id)
        if user is None:
            from app.core.exceptions import AccessTokenInvalidError

            raise AccessTokenInvalidError()
        if not user.is_active:
            raise UserInactiveError()
        return user

    async def _create_token_pair(self, user: User) -> AuthTokenPair:
        raw_refresh_token = generate_refresh_token()
        refresh_token_hash = hash_refresh_token(raw_refresh_token)
        expires_at = utc_now() + timedelta(days=self.settings.refresh_token_expire_days)
        await refresh_token_repository.create(
            self.session,
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
        return AuthTokenPair(
            access_token=create_access_token(user.id, settings=self.settings),
            refresh_token=raw_refresh_token,
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=user,
        )

    async def _record_login_failure(
        self,
        *,
        audit_context: AuditContext | None,
        error_code: str,
    ) -> None:
        await AuditService(self.session, settings=self.settings).record_failure_best_effort(
            actor_user_id=None,
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            target_type=None,
            target_id=None,
            context=audit_context,
            error_code=error_code,
            metadata={},
        )


def _is_expired(expires_at: datetime, now: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now
