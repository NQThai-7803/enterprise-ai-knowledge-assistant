from __future__ import annotations

from app.core.permissions import (
    EDIT_LEVELS,
    MANAGE_LEVELS,
    VIEW_LEVELS,
    choose_highest_permission,
)
from app.models import DocumentPermissionLevel


def test_view_permission_allows_view() -> None:
    assert DocumentPermissionLevel.VIEW in VIEW_LEVELS
    assert DocumentPermissionLevel.VIEW not in EDIT_LEVELS
    assert DocumentPermissionLevel.VIEW not in MANAGE_LEVELS


def test_edit_permission_allows_view_and_edit() -> None:
    assert DocumentPermissionLevel.EDIT in VIEW_LEVELS
    assert DocumentPermissionLevel.EDIT in EDIT_LEVELS
    assert DocumentPermissionLevel.EDIT not in MANAGE_LEVELS


def test_manage_permission_allows_view_edit_and_manage() -> None:
    assert DocumentPermissionLevel.MANAGE in VIEW_LEVELS
    assert DocumentPermissionLevel.MANAGE in EDIT_LEVELS
    assert DocumentPermissionLevel.MANAGE in MANAGE_LEVELS


def test_permission_mapping_does_not_depend_on_string_order() -> None:
    permissions = {
        DocumentPermissionLevel.VIEW,
        DocumentPermissionLevel.MANAGE,
        DocumentPermissionLevel.EDIT,
    }

    assert choose_highest_permission(permissions) == DocumentPermissionLevel.MANAGE
    assert choose_highest_permission({DocumentPermissionLevel.EDIT}) == DocumentPermissionLevel.EDIT
