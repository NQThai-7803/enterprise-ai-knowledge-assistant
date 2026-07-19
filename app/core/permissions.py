from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.sql import ColumnElement

from app.core.exceptions import PermissionDeniedError
from app.models import (
    Document,
    DocumentAccessScope,
    DocumentPermission,
    DocumentPermissionLevel,
    User,
    UserRole,
)

VIEW_LEVELS = {
    DocumentPermissionLevel.VIEW,
    DocumentPermissionLevel.EDIT,
    DocumentPermissionLevel.MANAGE,
}
EDIT_LEVELS = {
    DocumentPermissionLevel.EDIT,
    DocumentPermissionLevel.MANAGE,
}
MANAGE_LEVELS = {DocumentPermissionLevel.MANAGE}
PERMISSION_PRIORITY = (
    DocumentPermissionLevel.MANAGE,
    DocumentPermissionLevel.EDIT,
    DocumentPermissionLevel.VIEW,
)


def can_access_department(current_user: User, department_id: UUID | None) -> bool:
    if current_user.role == UserRole.ADMIN:
        return True
    if department_id is None or current_user.department_id is None:
        return False
    return current_user.department_id == department_id


def can_manage_department_users(current_user: User, target_department_id: UUID | None) -> bool:
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role != UserRole.MANAGER:
        return False
    if target_department_id is None or current_user.department_id is None:
        return False
    return current_user.department_id == target_department_id


def can_manage_user(current_user: User, target_user: User) -> bool:
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role != UserRole.MANAGER:
        return False
    if current_user.department_id is None or target_user.department_id is None:
        return False
    return (
        target_user.role == UserRole.STAFF
        and current_user.department_id == target_user.department_id
    )


def can_assign_role(current_user: User, target_role: UserRole) -> bool:
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.MANAGER:
        return target_role == UserRole.STAFF
    return False


def can_view_document(
    current_user: User,
    document: Document,
    direct_permission: DocumentPermissionLevel | None = None,
) -> bool:
    if document.is_deleted:
        return False
    if current_user.role == UserRole.ADMIN:
        return True
    if document.access_scope == DocumentAccessScope.ORGANIZATION:
        return True
    if (
        document.access_scope == DocumentAccessScope.DEPARTMENT
        and current_user.department_id is not None
        and current_user.department_id == document.department_id
    ):
        return True
    if document.uploaded_by == current_user.id:
        return True
    return direct_permission in VIEW_LEVELS


def can_edit_document(
    current_user: User,
    document: Document,
    direct_permission: DocumentPermissionLevel | None = None,
) -> bool:
    if document.is_deleted:
        return False
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role != UserRole.MANAGER:
        return False
    if document.uploaded_by == current_user.id:
        return True
    if (
        document.access_scope == DocumentAccessScope.DEPARTMENT
        and current_user.department_id is not None
        and current_user.department_id == document.department_id
    ):
        return True
    return direct_permission in EDIT_LEVELS


def can_manage_document(
    current_user: User,
    document: Document,
    direct_permission: DocumentPermissionLevel | None = None,
) -> bool:
    if document.is_deleted:
        return False
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role != UserRole.MANAGER:
        return False
    if document.uploaded_by == current_user.id:
        return True
    if (
        document.access_scope == DocumentAccessScope.DEPARTMENT
        and current_user.department_id is not None
        and current_user.department_id == document.department_id
    ):
        return True
    return direct_permission in MANAGE_LEVELS


def choose_highest_permission(
    permissions: set[DocumentPermissionLevel],
) -> DocumentPermissionLevel | None:
    for permission in PERMISSION_PRIORITY:
        if permission in permissions:
            return permission
    return None


def build_accessible_document_filter(current_user: User) -> ColumnElement[bool]:
    if current_user.role == UserRole.ADMIN:
        return Document.is_deleted.is_(False)

    access_conditions: list[ColumnElement[bool]] = [
        Document.access_scope == DocumentAccessScope.ORGANIZATION,
        Document.uploaded_by == current_user.id,
        exists(
            select(1).where(
                DocumentPermission.document_id == Document.id,
                DocumentPermission.user_id == current_user.id,
                DocumentPermission.permission.in_(tuple(VIEW_LEVELS)),
            )
        ),
    ]

    if current_user.department_id is not None:
        access_conditions.extend(
            [
                and_(
                    Document.access_scope == DocumentAccessScope.DEPARTMENT,
                    Document.department_id == current_user.department_id,
                ),
                exists(
                    select(1).where(
                        DocumentPermission.document_id == Document.id,
                        DocumentPermission.department_id == current_user.department_id,
                        DocumentPermission.permission.in_(tuple(VIEW_LEVELS)),
                    )
                ),
            ]
        )

    return and_(Document.is_deleted.is_(False), or_(*access_conditions))


def ensure_permission(is_allowed: bool) -> None:
    if not is_allowed:
        raise PermissionDeniedError()
