from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.core.permissions import build_accessible_document_filter, choose_highest_permission
from app.models import (
    Document,
    DocumentAccessScope,
    DocumentPermission,
    DocumentPermissionLevel,
    DocumentStatus,
    User,
)

DOCUMENT_SORT_FIELDS = {
    "title": Document.title,
    "status": Document.status,
    "created_at": Document.created_at,
    "updated_at": Document.updated_at,
    "file_size": Document.file_size,
}


async def create(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
    original_filename: str,
    storage_key: str,
    mime_type: str,
    file_size: int,
    checksum_sha256: str,
    access_scope: DocumentAccessScope,
    department_id: UUID | None,
    uploaded_by: UUID,
) -> Document:
    document = Document(
        title=title,
        description=description,
        original_filename=original_filename,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=file_size,
        checksum_sha256=checksum_sha256,
        status=DocumentStatus.UPLOADED,
        access_scope=access_scope,
        department_id=department_id,
        uploaded_by=uploaded_by,
        error_message=None,
        is_deleted=False,
    )
    session.add(document)
    return document


async def get_active_duplicate_by_uploader_and_checksum(
    session: AsyncSession,
    *,
    uploaded_by: UUID,
    checksum_sha256: str,
) -> Document | None:
    statement = select(Document).where(
        Document.uploaded_by == uploaded_by,
        Document.checksum_sha256 == checksum_sha256,
        Document.is_deleted.is_(False),
    )
    return await session.scalar(statement)


async def list_accessible_documents(
    session: AsyncSession,
    *,
    current_user: User,
    limit: int,
    offset: int,
    search: str | None = None,
    status: DocumentStatus | None = None,
    access_scope: DocumentAccessScope | None = None,
    department_id: UUID | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> list[Document]:
    sort_column = DOCUMENT_SORT_FIELDS[sort_by]
    order_by = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    id_order_by = Document.id.desc() if sort_order == "desc" else Document.id.asc()
    statement = (
        select(Document)
        .where(
            build_accessible_document_filter(current_user),
            *_document_filter_conditions(
                search=search,
                status=status,
                access_scope=access_scope,
                department_id=department_id,
            ),
        )
        .order_by(order_by, id_order_by)
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(statement))


async def count_accessible_documents(
    session: AsyncSession,
    *,
    current_user: User,
    search: str | None = None,
    status: DocumentStatus | None = None,
    access_scope: DocumentAccessScope | None = None,
    department_id: UUID | None = None,
) -> int:
    statement = (
        select(func.count())
        .select_from(Document)
        .where(
            build_accessible_document_filter(current_user),
            *_document_filter_conditions(
                search=search,
                status=status,
                access_scope=access_scope,
                department_id=department_id,
            ),
        )
    )
    return await session.scalar(statement) or 0


async def get_accessible_by_id(
    session: AsyncSession,
    *,
    document_id: UUID,
    current_user: User,
) -> Document | None:
    statement = select(Document).where(
        Document.id == document_id,
        build_accessible_document_filter(current_user),
    )
    return await session.scalar(statement)


async def get_by_id_including_deleted(
    session: AsyncSession,
    document_id: UUID,
) -> Document | None:
    return await session.get(Document, document_id)


async def get_active_by_id(
    session: AsyncSession,
    document_id: UUID,
) -> Document | None:
    statement = select(Document).where(
        Document.id == document_id,
        Document.is_deleted.is_(False),
    )
    return await session.scalar(statement)


async def get_effective_direct_permission(
    session: AsyncSession,
    *,
    document_id: UUID,
    user_id: UUID,
    department_id: UUID | None,
) -> DocumentPermissionLevel | None:
    conditions = [DocumentPermission.user_id == user_id]
    if department_id is not None:
        conditions.append(DocumentPermission.department_id == department_id)
    statement = select(DocumentPermission.permission).where(
        DocumentPermission.document_id == document_id,
        or_(*conditions),
    )
    permissions = set(await session.scalars(statement))
    return choose_highest_permission(permissions)


async def count_documents_by_department(
    session: AsyncSession,
    department_id: UUID,
) -> int:
    statement = (
        select(func.count()).select_from(Document).where(Document.department_id == department_id)
    )
    return await session.scalar(statement) or 0


def _document_filter_conditions(
    *,
    search: str | None,
    status: DocumentStatus | None,
    access_scope: DocumentAccessScope | None,
    department_id: UUID | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if search:
        search_term = f"%{search.strip()}%"
        conditions.append(
            or_(
                Document.title.ilike(search_term),
                Document.original_filename.ilike(search_term),
                Document.description.ilike(search_term),
            )
        )
    if status is not None:
        conditions.append(Document.status == status)
    if access_scope is not None:
        conditions.append(Document.access_scope == access_scope)
    if department_id is not None:
        conditions.append(Document.department_id == department_id)
    return conditions
