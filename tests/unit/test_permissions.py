from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.api.dependencies import require_admin, require_manager_or_admin, require_roles
from app.core.exceptions import PermissionDeniedError
from app.core.permissions import (
    can_access_department,
    can_assign_role,
    can_manage_department_users,
    can_manage_user,
    ensure_permission,
)
from app.models import User, UserRole


def make_user(
    *,
    role: UserRole,
    department_id: UUID | None = None,
    is_active: bool = True,
) -> User:
    return User(
        email=f"{uuid4()}@example.com",
        full_name="Permission Test User",
        hashed_password="not-used-in-policy-tests",
        role=role,
        department_id=department_id,
        is_active=is_active,
    )


def assert_forbidden(error: PermissionDeniedError) -> None:
    assert error.status_code == 403
    assert error.code == "FORBIDDEN"
    assert error.message == "You do not have permission to perform this action."


def test_require_roles_rejects_empty_role_list() -> None:
    with pytest.raises(ValueError):
        require_roles()


def test_require_admin_allows_admin() -> None:
    admin = make_user(role=UserRole.ADMIN)

    assert require_admin(admin) is admin


def test_require_admin_rejects_manager() -> None:
    manager = make_user(role=UserRole.MANAGER)

    with pytest.raises(PermissionDeniedError) as exc_info:
        require_admin(manager)

    assert_forbidden(exc_info.value)


def test_require_admin_rejects_staff() -> None:
    staff = make_user(role=UserRole.STAFF)

    with pytest.raises(PermissionDeniedError) as exc_info:
        require_admin(staff)

    assert_forbidden(exc_info.value)


def test_require_manager_or_admin_allows_admin() -> None:
    admin = make_user(role=UserRole.ADMIN)

    assert require_manager_or_admin(admin) is admin


def test_require_manager_or_admin_allows_manager() -> None:
    manager = make_user(role=UserRole.MANAGER)

    assert require_manager_or_admin(manager) is manager


def test_require_manager_or_admin_rejects_staff() -> None:
    staff = make_user(role=UserRole.STAFF)

    with pytest.raises(PermissionDeniedError) as exc_info:
        require_manager_or_admin(staff)

    assert_forbidden(exc_info.value)


def test_role_dependency_returns_current_user() -> None:
    department_id = uuid4()
    current_user = make_user(role=UserRole.MANAGER, department_id=department_id)
    original_role = current_user.role
    original_department_id = current_user.department_id

    returned_user = require_roles(UserRole.MANAGER)(current_user)

    assert returned_user is current_user
    assert current_user.role == original_role
    assert current_user.department_id == original_department_id


def test_admin_can_access_any_department() -> None:
    assert can_access_department(make_user(role=UserRole.ADMIN), uuid4())


def test_admin_can_access_unscoped_resource() -> None:
    assert can_access_department(make_user(role=UserRole.ADMIN), None)


def test_manager_can_access_own_department() -> None:
    department_id = uuid4()

    assert can_access_department(
        make_user(role=UserRole.MANAGER, department_id=department_id),
        department_id,
    )


def test_manager_cannot_access_other_department() -> None:
    assert not can_access_department(
        make_user(role=UserRole.MANAGER, department_id=uuid4()),
        uuid4(),
    )


def test_manager_without_department_has_no_department_access() -> None:
    assert not can_access_department(make_user(role=UserRole.MANAGER), uuid4())


def test_manager_cannot_access_unscoped_resource() -> None:
    assert not can_access_department(
        make_user(role=UserRole.MANAGER, department_id=uuid4()),
        None,
    )


def test_staff_can_access_own_department() -> None:
    department_id = uuid4()

    assert can_access_department(
        make_user(role=UserRole.STAFF, department_id=department_id),
        department_id,
    )


def test_staff_cannot_access_other_department() -> None:
    assert not can_access_department(
        make_user(role=UserRole.STAFF, department_id=uuid4()),
        uuid4(),
    )


def test_staff_without_department_has_no_department_access() -> None:
    assert not can_access_department(make_user(role=UserRole.STAFF), uuid4())


def test_admin_can_manage_department_users() -> None:
    assert can_manage_department_users(make_user(role=UserRole.ADMIN), None)
    assert can_manage_department_users(make_user(role=UserRole.ADMIN), uuid4())


def test_manager_can_manage_own_department_users() -> None:
    department_id = uuid4()

    assert can_manage_department_users(
        make_user(role=UserRole.MANAGER, department_id=department_id),
        department_id,
    )


def test_manager_cannot_manage_other_department_users() -> None:
    assert not can_manage_department_users(
        make_user(role=UserRole.MANAGER, department_id=uuid4()),
        uuid4(),
    )


def test_manager_cannot_manage_unscoped_department_users() -> None:
    assert not can_manage_department_users(
        make_user(role=UserRole.MANAGER, department_id=uuid4()),
        None,
    )


def test_staff_cannot_manage_department_users() -> None:
    assert not can_manage_department_users(
        make_user(role=UserRole.STAFF, department_id=uuid4()),
        uuid4(),
    )


def test_admin_can_manage_any_user() -> None:
    target_user = make_user(role=UserRole.ADMIN, is_active=False)

    assert can_manage_user(make_user(role=UserRole.ADMIN), target_user)


def test_manager_can_manage_staff_in_same_department() -> None:
    department_id = uuid4()

    assert can_manage_user(
        make_user(role=UserRole.MANAGER, department_id=department_id),
        make_user(role=UserRole.STAFF, department_id=department_id, is_active=False),
    )


def test_manager_cannot_manage_staff_in_other_department() -> None:
    assert not can_manage_user(
        make_user(role=UserRole.MANAGER, department_id=uuid4()),
        make_user(role=UserRole.STAFF, department_id=uuid4()),
    )


def test_manager_cannot_manage_manager() -> None:
    department_id = uuid4()

    assert not can_manage_user(
        make_user(role=UserRole.MANAGER, department_id=department_id),
        make_user(role=UserRole.MANAGER, department_id=department_id),
    )


def test_manager_cannot_manage_admin() -> None:
    department_id = uuid4()

    assert not can_manage_user(
        make_user(role=UserRole.MANAGER, department_id=department_id),
        make_user(role=UserRole.ADMIN, department_id=department_id),
    )


def test_manager_without_department_cannot_manage_user() -> None:
    assert not can_manage_user(
        make_user(role=UserRole.MANAGER),
        make_user(role=UserRole.STAFF, department_id=uuid4()),
    )


def test_manager_cannot_manage_user_without_department() -> None:
    assert not can_manage_user(
        make_user(role=UserRole.MANAGER, department_id=uuid4()),
        make_user(role=UserRole.STAFF),
    )


def test_staff_cannot_manage_user() -> None:
    department_id = uuid4()

    assert not can_manage_user(
        make_user(role=UserRole.STAFF, department_id=department_id),
        make_user(role=UserRole.STAFF, department_id=department_id),
    )


def test_admin_can_assign_admin_role() -> None:
    assert can_assign_role(make_user(role=UserRole.ADMIN), UserRole.ADMIN)


def test_admin_can_assign_manager_role() -> None:
    assert can_assign_role(make_user(role=UserRole.ADMIN), UserRole.MANAGER)


def test_admin_can_assign_staff_role() -> None:
    assert can_assign_role(make_user(role=UserRole.ADMIN), UserRole.STAFF)


def test_manager_can_assign_staff_role() -> None:
    assert can_assign_role(make_user(role=UserRole.MANAGER), UserRole.STAFF)


def test_manager_cannot_assign_manager_role() -> None:
    assert not can_assign_role(make_user(role=UserRole.MANAGER), UserRole.MANAGER)


def test_manager_cannot_assign_admin_role() -> None:
    assert not can_assign_role(make_user(role=UserRole.MANAGER), UserRole.ADMIN)


def test_staff_cannot_assign_any_role() -> None:
    staff = make_user(role=UserRole.STAFF)

    assert not can_assign_role(staff, UserRole.ADMIN)
    assert not can_assign_role(staff, UserRole.MANAGER)
    assert not can_assign_role(staff, UserRole.STAFF)


def test_ensure_permission_allows_true() -> None:
    assert ensure_permission(True) is None


def test_ensure_permission_raises_forbidden_for_false() -> None:
    with pytest.raises(PermissionDeniedError) as exc_info:
        ensure_permission(False)

    assert_forbidden(exc_info.value)
