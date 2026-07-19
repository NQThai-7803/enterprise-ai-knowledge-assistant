from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentPermission, DocumentPermissionLevel


async def list_for_document(
    session: AsyncSession,
    document_id: UUID,
) -> list[DocumentPermission]:
    statement = (
        select(DocumentPermission)
        .where(DocumentPermission.document_id == document_id)
        .order_by(DocumentPermission.created_at.asc(), DocumentPermission.id.asc())
    )
    return list(await session.scalars(statement))


async def get_by_id(
    session: AsyncSession,
    permission_id: UUID,
) -> DocumentPermission | None:
    return await session.get(DocumentPermission, permission_id)


async def get_by_document_and_id(
    session: AsyncSession,
    *,
    document_id: UUID,
    permission_id: UUID,
) -> DocumentPermission | None:
    statement = select(DocumentPermission).where(
        DocumentPermission.document_id == document_id,
        DocumentPermission.id == permission_id,
    )
    return await session.scalar(statement)


async def get_by_document_and_user(
    session: AsyncSession,
    *,
    document_id: UUID,
    user_id: UUID,
) -> DocumentPermission | None:
    statement = select(DocumentPermission).where(
        DocumentPermission.document_id == document_id,
        DocumentPermission.user_id == user_id,
    )
    return await session.scalar(statement)


async def get_by_document_and_department(
    session: AsyncSession,
    *,
    document_id: UUID,
    department_id: UUID,
) -> DocumentPermission | None:
    statement = select(DocumentPermission).where(
        DocumentPermission.document_id == document_id,
        DocumentPermission.department_id == department_id,
    )
    return await session.scalar(statement)


async def create(
    session: AsyncSession,
    *,
    document_id: UUID,
    user_id: UUID | None,
    department_id: UUID | None,
    permission: DocumentPermissionLevel,
    created_by: UUID,
) -> DocumentPermission:
    document_permission = DocumentPermission(
        document_id=document_id,
        user_id=user_id,
        department_id=department_id,
        permission=permission,
        created_by=created_by,
    )
    session.add(document_permission)
    return document_permission


async def delete(session: AsyncSession, document_permission: DocumentPermission) -> None:
    await session.delete(document_permission)
