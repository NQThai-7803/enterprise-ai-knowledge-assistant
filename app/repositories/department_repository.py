from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.models import Department

DEPARTMENT_SORT_FIELDS = {
    "name": Department.name,
    "code": Department.code,
    "created_at": Department.created_at,
}


async def get_by_id(session: AsyncSession, department_id: UUID) -> Department | None:
    return await session.get(Department, department_id)


async def get_by_name(session: AsyncSession, name: str) -> Department | None:
    return await session.scalar(select(Department).where(Department.name == name))


async def get_by_code(session: AsyncSession, code: str) -> Department | None:
    return await session.scalar(select(Department).where(Department.code == code))


async def get_by_name_excluding_id(
    session: AsyncSession,
    *,
    name: str,
    excluded_department_id: UUID,
) -> Department | None:
    return await session.scalar(
        select(Department).where(Department.name == name, Department.id != excluded_department_id)
    )


async def get_by_code_excluding_id(
    session: AsyncSession,
    *,
    code: str,
    excluded_department_id: UUID,
) -> Department | None:
    return await session.scalar(
        select(Department).where(Department.code == code, Department.id != excluded_department_id)
    )


async def list_departments(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> list[Department]:
    sort_column = DEPARTMENT_SORT_FIELDS[sort_by]
    order_by = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    id_order_by = Department.id.desc() if sort_order == "desc" else Department.id.asc()
    statement = (
        select(Department)
        .where(*_department_filter_conditions(search))
        .order_by(order_by, id_order_by)
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(statement))


async def count_departments(
    session: AsyncSession,
    *,
    search: str | None = None,
) -> int:
    statement = (
        select(func.count()).select_from(Department).where(*_department_filter_conditions(search))
    )
    return await session.scalar(statement) or 0


async def create(
    session: AsyncSession,
    *,
    name: str,
    code: str,
    description: str | None,
) -> Department:
    department = Department(name=name, code=code, description=description)
    session.add(department)
    return department


async def delete(session: AsyncSession, department: Department) -> None:
    await session.delete(department)


def _department_filter_conditions(search: str | None) -> list[ColumnElement[bool]]:
    if not search:
        return []
    search_term = f"%{search.strip()}%"
    return [or_(Department.name.ilike(search_term), Department.code.ilike(search_term))]
