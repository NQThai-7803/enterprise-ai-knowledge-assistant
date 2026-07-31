from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.audit import AuditEvent, AuditEventType, AuditOutcome, AuditTargetType
from app.audit.metadata import AuditMetadataError


def make_event(**overrides: object) -> AuditEvent:
    values = {
        "event_type": AuditEventType.FEEDBACK_UPSERTED,
        "outcome": AuditOutcome.SUCCESS,
        "actor_user_id": uuid4(),
        "target_type": AuditTargetType.FEEDBACK,
        "target_id": str(uuid4()),
        "request_id": None,
        "error_code": None,
        "metadata": {"rating": "HELPFUL"},
    }
    values.update(overrides)
    return AuditEvent(**values)


def test_audit_event_is_immutable() -> None:
    event = make_event()

    with pytest.raises(FrozenInstanceError):
        event.event_type = AuditEventType.AUTH_LOGIN_FAILED

    with pytest.raises(TypeError):
        event.metadata["rating"] = "NOT_HELPFUL"


def test_audit_event_type_is_valid() -> None:
    assert AuditEventType("FEEDBACK_UPSERTED") is AuditEventType.FEEDBACK_UPSERTED


def test_audit_outcome_values() -> None:
    assert AuditOutcome.SUCCESS.value == "SUCCESS"
    assert AuditOutcome.FAILURE.value == "FAILURE"
    assert set(AuditOutcome) == {AuditOutcome.SUCCESS, AuditOutcome.FAILURE}


def test_audit_event_repr_hides_metadata() -> None:
    event = make_event(metadata={"rating": "HELPFUL"})

    representation = repr(event)

    assert "metadata_keys" in representation
    assert "HELPFUL" not in representation
    assert "CONFIDENTIAL_AUDIT_PASSWORD" not in representation


def test_audit_event_rejects_orm_object_metadata() -> None:
    orm_like = SimpleNamespace(_sa_instance_state=object())

    with pytest.raises(AuditMetadataError):
        make_event(metadata={"rating": orm_like})


def test_audit_event_rejects_exception_metadata() -> None:
    with pytest.raises(AuditMetadataError):
        make_event(metadata={"rating": RuntimeError("CONFIDENTIAL_AUDIT_TOKEN")})


def test_audit_event_rejects_secret_metadata() -> None:
    with pytest.raises(AuditMetadataError):
        make_event(metadata={"rating": SecretStr("CONFIDENTIAL_AUDIT_PASSWORD")})


def test_audit_event_rejects_nested_sensitive_content() -> None:
    with pytest.raises(AuditMetadataError) as exc_info:
        make_event(metadata={"rating": {"password": "CONFIDENTIAL_AUDIT_PASSWORD"}})

    assert "CONFIDENTIAL_AUDIT_PASSWORD" not in repr(exc_info.value)


def test_audit_event_accepts_safe_scalar_metadata() -> None:
    department_id = uuid4()
    event = make_event(
        metadata={
            "role": "STAFF",
            "status_after": "ACTIVE",
            "department_id": department_id,
            "citation_count": 2,
            "rating": "NOT_HELPFUL",
        }
    )

    assert event.metadata == {
        "role": "STAFF",
        "status_after": "ACTIVE",
        "department_id": str(department_id),
        "citation_count": 2,
        "rating": "NOT_HELPFUL",
    }
