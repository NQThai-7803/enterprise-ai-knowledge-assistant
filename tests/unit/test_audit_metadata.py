from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.audit.metadata import AuditMetadataError, sanitize_audit_metadata
from app.models import FeedbackRating, UserRole


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("role", UserRole.STAFF),
        ("status", "ACTIVE"),
        ("access_scope", "PRIVATE"),
        ("rating", FeedbackRating.HELPFUL),
        ("citation_count", 3),
        ("document_id", uuid4()),
        ("principal_id", str(uuid4())),
        ("actor_type", "SYSTEM"),
    ],
)
def test_metadata_allows_whitelisted_keys(key: str, value: object) -> None:
    result = sanitize_audit_metadata({key: value})

    assert key in result


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "Password",
        "PASSWORD",
        "accessToken",
        "refresh_token",
        "documentContent",
        "content",
        "question",
        "answer",
        "reason",
        "excerpt",
        "storage_key",
        "filename",
        "email",
        "full_name",
        "prompt",
        "context",
    ],
)
def test_metadata_rejects_sensitive_key_variants(key: str) -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({key: "CONFIDENTIAL_AUDIT_TOKEN"})


def test_metadata_rejects_password_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"Password": "CONFIDENTIAL_AUDIT_PASSWORD"})


def test_metadata_rejects_token_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"accessToken": "CONFIDENTIAL_AUDIT_TOKEN"})


def test_metadata_rejects_content_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"documentContent": "CONFIDENTIAL_AUDIT_QUESTION"})


def test_metadata_rejects_question_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"question": "CONFIDENTIAL_AUDIT_QUESTION"})


def test_metadata_rejects_answer_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"answer": "CONFIDENTIAL_AUDIT_ANSWER"})


def test_metadata_rejects_reason_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"reason": "CONFIDENTIAL_AUDIT_REASON"})


def test_metadata_rejects_excerpt_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"excerpt": "CONFIDENTIAL_AUDIT_EXCERPT"})


def test_metadata_rejects_storage_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"storage_key": "CONFIDENTIAL_AUDIT_STORAGE_KEY"})


def test_metadata_rejects_bytes() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"rating": b"HELPFUL"})


def test_metadata_rejects_orm_instance() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"rating": SimpleNamespace(_sa_instance_state=object())})


def test_metadata_returns_immutable_copy() -> None:
    source = {"rating": "HELPFUL"}
    result = sanitize_audit_metadata(source)
    source["rating"] = "NOT_HELPFUL"

    assert result["rating"] == "HELPFUL"
    with pytest.raises(TypeError):
        result["rating"] = "NOT_HELPFUL"


def test_metadata_applies_length_limits() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"rating": "HELPFUL"}, max_length=5)


def test_metadata_rejects_exception_object() -> None:
    with pytest.raises(AuditMetadataError) as exc_info:
        sanitize_audit_metadata({"rating": RuntimeError("CONFIDENTIAL_AUDIT_REASON")})

    assert "CONFIDENTIAL_AUDIT_REASON" not in repr(exc_info.value)


def test_metadata_rejects_secret_value() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"rating": SecretStr("CONFIDENTIAL_AUDIT_PASSWORD")})


def test_metadata_rejects_unknown_string_value_under_allowed_key() -> None:
    with pytest.raises(AuditMetadataError):
        sanitize_audit_metadata({"status": "CONFIDENTIAL_AUDIT_FILENAME"})
