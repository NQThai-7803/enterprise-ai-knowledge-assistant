from __future__ import annotations

from uuid import UUID, uuid4

from app.core.permissions import can_edit_document, can_manage_document, can_view_document
from app.models import (
    Document,
    DocumentAccessScope,
    DocumentPermissionLevel,
    DocumentStatus,
    User,
    UserRole,
)


def make_user(*, role: UserRole, department_id: UUID | None = None) -> User:
    return User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        full_name="Policy User",
        hashed_password="not-used",
        role=role,
        department_id=department_id,
        is_active=True,
    )


def make_document(
    *,
    uploaded_by: UUID,
    access_scope: DocumentAccessScope = DocumentAccessScope.PRIVATE,
    department_id: UUID | None = None,
    is_deleted: bool = False,
) -> Document:
    return Document(
        id=uuid4(),
        title="Policy Document",
        original_filename="policy.pdf",
        storage_key=f"documents/2026/07/{uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=10,
        checksum_sha256="a" * 64,
        status=DocumentStatus.UPLOADED,
        access_scope=access_scope,
        department_id=department_id,
        uploaded_by=uploaded_by,
        is_deleted=is_deleted,
    )


def test_admin_can_view_any_document() -> None:
    admin = make_user(role=UserRole.ADMIN)
    document = make_document(uploaded_by=uuid4())

    assert can_view_document(admin, document)


def test_organization_document_is_visible_to_authenticated_user() -> None:
    staff = make_user(role=UserRole.STAFF)
    document = make_document(uploaded_by=uuid4(), access_scope=DocumentAccessScope.ORGANIZATION)

    assert can_view_document(staff, document)


def test_department_document_is_visible_to_same_department_user() -> None:
    department_id = uuid4()
    staff = make_user(role=UserRole.STAFF, department_id=department_id)
    document = make_document(
        uploaded_by=uuid4(),
        access_scope=DocumentAccessScope.DEPARTMENT,
        department_id=department_id,
    )

    assert can_view_document(staff, document)


def test_department_document_is_hidden_from_other_department() -> None:
    staff = make_user(role=UserRole.STAFF, department_id=uuid4())
    document = make_document(
        uploaded_by=uuid4(),
        access_scope=DocumentAccessScope.DEPARTMENT,
        department_id=uuid4(),
    )

    assert not can_view_document(staff, document)


def test_private_document_is_visible_to_uploader() -> None:
    staff = make_user(role=UserRole.STAFF)
    document = make_document(uploaded_by=staff.id)

    assert can_view_document(staff, document)


def test_private_document_is_hidden_without_grant() -> None:
    staff = make_user(role=UserRole.STAFF)
    document = make_document(uploaded_by=uuid4())

    assert not can_view_document(staff, document)


def test_direct_user_view_grant_allows_access() -> None:
    staff = make_user(role=UserRole.STAFF)
    document = make_document(uploaded_by=uuid4())

    assert can_view_document(staff, document, DocumentPermissionLevel.VIEW)


def test_direct_department_view_grant_allows_access() -> None:
    staff = make_user(role=UserRole.STAFF, department_id=uuid4())
    document = make_document(uploaded_by=uuid4())

    assert can_view_document(staff, document, DocumentPermissionLevel.VIEW)


def test_soft_deleted_document_is_not_viewable() -> None:
    admin = make_user(role=UserRole.ADMIN)
    document = make_document(uploaded_by=admin.id, is_deleted=True)

    assert not can_view_document(admin, document)


def test_admin_can_edit_any_document() -> None:
    admin = make_user(role=UserRole.ADMIN)
    document = make_document(uploaded_by=uuid4())

    assert can_edit_document(admin, document)


def test_manager_can_edit_own_uploaded_document() -> None:
    manager = make_user(role=UserRole.MANAGER, department_id=uuid4())
    document = make_document(uploaded_by=manager.id)

    assert can_edit_document(manager, document)


def test_manager_can_edit_same_department_document() -> None:
    department_id = uuid4()
    manager = make_user(role=UserRole.MANAGER, department_id=department_id)
    document = make_document(
        uploaded_by=uuid4(),
        access_scope=DocumentAccessScope.DEPARTMENT,
        department_id=department_id,
    )

    assert can_edit_document(manager, document)


def test_manager_cannot_edit_other_department_document() -> None:
    manager = make_user(role=UserRole.MANAGER, department_id=uuid4())
    document = make_document(
        uploaded_by=uuid4(),
        access_scope=DocumentAccessScope.DEPARTMENT,
        department_id=uuid4(),
    )

    assert not can_edit_document(manager, document)


def test_manager_with_edit_grant_can_edit() -> None:
    manager = make_user(role=UserRole.MANAGER, department_id=uuid4())
    document = make_document(uploaded_by=uuid4())

    assert can_edit_document(manager, document, DocumentPermissionLevel.EDIT)


def test_staff_cannot_edit_with_edit_grant() -> None:
    staff = make_user(role=UserRole.STAFF, department_id=uuid4())
    document = make_document(uploaded_by=uuid4())

    assert not can_edit_document(staff, document, DocumentPermissionLevel.EDIT)


def test_admin_can_manage_any_document() -> None:
    admin = make_user(role=UserRole.ADMIN)
    document = make_document(uploaded_by=uuid4())

    assert can_manage_document(admin, document)


def test_manager_can_manage_uploaded_document() -> None:
    manager = make_user(role=UserRole.MANAGER, department_id=uuid4())
    document = make_document(uploaded_by=manager.id)

    assert can_manage_document(manager, document)


def test_manager_can_manage_same_department_document() -> None:
    department_id = uuid4()
    manager = make_user(role=UserRole.MANAGER, department_id=department_id)
    document = make_document(
        uploaded_by=uuid4(),
        access_scope=DocumentAccessScope.DEPARTMENT,
        department_id=department_id,
    )

    assert can_manage_document(manager, document)


def test_manager_with_manage_grant_can_manage() -> None:
    manager = make_user(role=UserRole.MANAGER, department_id=uuid4())
    document = make_document(uploaded_by=uuid4())

    assert can_manage_document(manager, document, DocumentPermissionLevel.MANAGE)


def test_staff_cannot_manage_with_manage_grant() -> None:
    staff = make_user(role=UserRole.STAFF, department_id=uuid4())
    document = make_document(uploaded_by=uuid4())

    assert not can_manage_document(staff, document, DocumentPermissionLevel.MANAGE)
