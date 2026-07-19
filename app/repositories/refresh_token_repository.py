from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


async def create(
    session: AsyncSession,
    *,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(refresh_token)
    return refresh_token


async def get_by_hash_for_update(
    session: AsyncSession,
    token_hash: str,
) -> RefreshToken | None:
    statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    return await session.scalar(statement)


async def revoke(
    refresh_token: RefreshToken,
    *,
    revoked_at: datetime,
) -> None:
    if refresh_token.revoked_at is None:
        refresh_token.revoked_at = revoked_at


async def revoke_all_active_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    revoked_at: datetime,
) -> int:
    statement = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
    result = await session.execute(statement)
    return result.rowcount or 0
