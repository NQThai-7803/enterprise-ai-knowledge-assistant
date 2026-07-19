from sqlalchemy import CheckConstraint, UniqueConstraint

from app.db.base import Base
from app.models import (
    Document,
    DocumentAccessScope,
    DocumentPermission,
    DocumentPermissionLevel,
    DocumentStatus,
)


def _check_constraint_sql(table: object) -> list[str]:
    return [
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    ]


def _unique_constraint_column_sets(table: object) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_document_status_values() -> None:
    assert [status.value for status in DocumentStatus] == [
        "UPLOADED",
        "PROCESSING",
        "READY",
        "FAILED",
        "ARCHIVED",
    ]


def test_document_access_scope_values() -> None:
    assert [scope.value for scope in DocumentAccessScope] == [
        "PRIVATE",
        "DEPARTMENT",
        "ORGANIZATION",
    ]


def test_document_permission_level_values() -> None:
    assert [level.value for level in DocumentPermissionLevel] == ["VIEW", "EDIT", "MANAGE"]


def test_document_table_registered() -> None:
    assert Document.__tablename__ == "documents"
    assert "documents" in Base.metadata.tables


def test_document_permission_table_registered() -> None:
    assert DocumentPermission.__tablename__ == "document_permissions"
    assert "document_permissions" in Base.metadata.tables


def test_document_default_status_is_uploaded() -> None:
    assert Document.__table__.c.status.default is not None
    assert Document.__table__.c.status.default.arg == DocumentStatus.UPLOADED
    assert Document.__table__.c.status.server_default is not None


def test_document_default_access_scope_is_private() -> None:
    assert Document.__table__.c.access_scope.default is not None
    assert Document.__table__.c.access_scope.default.arg == DocumentAccessScope.PRIVATE
    assert Document.__table__.c.access_scope.server_default is not None


def test_document_default_is_deleted_is_false() -> None:
    assert Document.__table__.c.is_deleted.default is not None
    assert Document.__table__.c.is_deleted.default.arg is False
    assert Document.__table__.c.is_deleted.server_default is not None


def test_document_storage_key_is_unique() -> None:
    assert ("storage_key",) in _unique_constraint_column_sets(Document.__table__)


def test_document_file_size_check_constraint_exists() -> None:
    constraints = _check_constraint_sql(Document.__table__)

    assert any("file_size" in constraint and "> 0" in constraint for constraint in constraints)


def test_document_scope_check_constraint_exists() -> None:
    constraints = _check_constraint_sql(Document.__table__)

    assert any(
        "access_scope" in constraint
        and "department_id" in constraint
        and "DEPARTMENT" in constraint
        and "PRIVATE" in constraint
        and "ORGANIZATION" in constraint
        for constraint in constraints
    )


def test_document_permission_grantee_check_constraint_exists() -> None:
    constraints = _check_constraint_sql(DocumentPermission.__table__)

    assert any(
        "user_id" in constraint
        and "department_id" in constraint
        and "IS NOT NULL" in constraint
        and "IS NULL" in constraint
        for constraint in constraints
    )


def test_document_permission_user_unique_constraint_exists() -> None:
    assert ("document_id", "user_id") in _unique_constraint_column_sets(
        DocumentPermission.__table__
    )


def test_document_permission_department_unique_constraint_exists() -> None:
    assert ("document_id", "department_id") in _unique_constraint_column_sets(
        DocumentPermission.__table__
    )
