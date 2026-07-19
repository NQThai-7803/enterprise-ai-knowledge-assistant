from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.models import User, UserRole

USER_SORT_FIELDS = {
    "email": User.email,
    "full_name": User.full_name,
    "role": User.role,
    "created_at": User.created_at,
    "updated_at": User.updated_at,
}


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def get_by_email_excluding_id(
    session: AsyncSession,
    *,
    email: str,
    excluded_user_id: UUID,
) -> User | None:
    return await session.scalar(
        select(User).where(User.email == email, User.id != excluded_user_id)
    )


async def get_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def list_users(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    search: str | None = None,
    role: UserRole | None = None,
    department_id: UUID | None = None,
    is_active: bool | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> list[User]:
    sort_column = USER_SORT_FIELDS[sort_by]
    order_by = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    id_order_by = User.id.desc() if sort_order == "desc" else User.id.asc()
    statement = (
        select(User)
        .where(*_user_filter_conditions(search, role, department_id, is_active))
        .order_by(order_by, id_order_by)
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(statement))


async def count_users(
    session: AsyncSession,
    *,
    search: str | None = None,
    role: UserRole | None = None,
    department_id: UUID | None = None,
    is_active: bool | None = None,
) -> int:
    statement = (
        select(func.count())
        .select_from(User)
        .where(*_user_filter_conditions(search, role, department_id, is_active))
    )
    return await session.scalar(statement) or 0


async def create(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    hashed_password: str,
    role: UserRole,
    department_id: UUID | None,
) -> User:
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        department_id=department_id,
        is_active=True,
    )
    session.add(user)
    return user


async def count_active_admins(session: AsyncSession) -> int:
    statement = (
        select(func.count())
        .select_from(User)
        .where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
    )
    return await session.scalar(statement) or 0


async def count_active_users_by_department(
    session: AsyncSession,
    department_id: UUID,
) -> int:
    statement = (
        select(func.count())
        .select_from(User)
        .where(
            User.department_id == department_id,
            User.is_active.is_(True),
        )
    )
    return await session.scalar(statement) or 0


def _user_filter_conditions(
    search: str | None,
    role: UserRole | None,
    department_id: UUID | None,
    is_active: bool | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if search:
        search_term = f"%{search.strip()}%"
        conditions.append(or_(User.email.ilike(search_term), User.full_name.ilike(search_term)))
    if role is not None:
        conditions.append(User.role == role)
    if department_id is not None:
        conditions.append(User.department_id == department_id)
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))
    return conditions
