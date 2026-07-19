from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.department import DepartmentCreate, DepartmentUpdate


def test_department_create_normalizes_code_to_uppercase() -> None:
    payload = DepartmentCreate(name="Information Technology", code="it", description=None)

    assert payload.code == "IT"


def test_department_create_trims_name() -> None:
    payload = DepartmentCreate(name="  Information Technology  ", code="IT", description=None)

    assert payload.name == "Information Technology"


def test_department_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        DepartmentCreate(name="   ", code="IT", description=None)


def test_department_create_rejects_invalid_code() -> None:
    with pytest.raises(ValidationError):
        DepartmentCreate(name="Information Technology", code="IT TEAM", description=None)


def test_department_update_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        DepartmentUpdate()


def test_department_update_allows_description_null() -> None:
    payload = DepartmentUpdate(description=None)

    assert payload.description is None
    assert "description" in payload.model_fields_set
