from __future__ import annotations

import json
import re
from collections.abc import Mapping
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias
from uuid import UUID

from pydantic import SecretStr

AuditScalar: TypeAlias = str | int | bool | None  # noqa: UP040

DEFAULT_AUDIT_METADATA_MAX_LENGTH = 2000

ALLOWED_METADATA_KEYS = frozenset(
    {
        "access_scope",
        "actor_type",
        "citation_count",
        "department_id",
        "document_id",
        "document_status",
        "grounding_status",
        "page_size",
        "permission",
        "principal_id",
        "principal_type",
        "processing_outcome",
        "rating",
        "result_count",
        "role",
        "status",
        "status_after",
        "status_before",
    }
)

_IDENTIFIER_KEYS = frozenset({"department_id", "document_id", "principal_id"})
_COUNT_KEYS = frozenset({"citation_count", "page_size", "result_count"})
_ALLOWED_STRING_VALUES_BY_KEY = {
    "access_scope": frozenset({"PRIVATE", "DEPARTMENT", "ORGANIZATION"}),
    "actor_type": frozenset({"SYSTEM"}),
    "document_status": frozenset({"UPLOADED", "PROCESSING", "READY", "FAILED", "ARCHIVED"}),
    "grounding_status": frozenset({"ANSWERED", "NO_ANSWER"}),
    "permission": frozenset({"VIEW", "EDIT", "MANAGE"}),
    "principal_type": frozenset({"USER", "DEPARTMENT"}),
    "processing_outcome": frozenset({"READY", "FAILED"}),
    "rating": frozenset({"HELPFUL", "NOT_HELPFUL"}),
    "role": frozenset({"ADMIN", "MANAGER", "STAFF"}),
    "status": frozenset(
        {"ACTIVE", "INACTIVE", "UPLOADED", "PROCESSING", "READY", "FAILED", "ARCHIVED"}
    ),
    "status_after": frozenset(
        {"ACTIVE", "INACTIVE", "UPLOADED", "PROCESSING", "READY", "FAILED", "ARCHIVED"}
    ),
    "status_before": frozenset(
        {"ACTIVE", "INACTIVE", "UPLOADED", "PROCESSING", "READY", "FAILED", "ARCHIVED"}
    ),
}

SENSITIVE_METADATA_KEY_FRAGMENTS = tuple(
    _fragment
    for _fragment in (
        "answer",
        "apikey",
        "authorization",
        "chunktext",
        "content",
        "context",
        "databaseurl",
        "documentcontent",
        "documenttext",
        "email",
        "excerpt",
        "filename",
        "fullname",
        "hashedpassword",
        "llmresponse",
        "password",
        "path",
        "prompt",
        "providererrorbody",
        "question",
        "reason",
        "refreshtoken",
        "secret",
        "storage",
        "storagekey",
        "token",
        "tokenhash",
    )
)


class AuditMetadataError(ValueError):
    pass


def sanitize_audit_metadata(
    metadata: Mapping[str, object] | None,
    *,
    max_length: int = DEFAULT_AUDIT_METADATA_MAX_LENGTH,
) -> Mapping[str, AuditScalar]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        msg = "Audit metadata must be a mapping."
        raise AuditMetadataError(msg)

    sanitized: dict[str, AuditScalar] = {}
    for key, value in metadata.items():
        _validate_metadata_key(key)
        sanitized[key] = _sanitize_metadata_value(key, value, max_length=max_length)
    _validate_serialized_length(sanitized, max_length=max_length)
    return MappingProxyType(dict(sanitized))


def sanitize_stored_audit_metadata_for_response(
    metadata: Mapping[str, object] | None,
    *,
    max_length: int = DEFAULT_AUDIT_METADATA_MAX_LENGTH,
) -> dict[str, AuditScalar]:
    if metadata is None or not isinstance(metadata, Mapping):
        return {}

    sanitized: dict[str, AuditScalar] = {}
    for key, value in metadata.items():
        try:
            _validate_metadata_key(key)
            sanitized[key] = _sanitize_metadata_value(key, value, max_length=max_length)
        except AuditMetadataError:
            continue
    try:
        _validate_serialized_length(sanitized, max_length=max_length)
    except AuditMetadataError:
        return {}
    return sanitized


def _validate_metadata_key(key: object) -> None:
    if not isinstance(key, str) or not key:
        msg = "Audit metadata keys must be non-empty strings."
        raise AuditMetadataError(msg)
    if _is_sensitive_key(key):
        msg = "Audit metadata contains a sensitive key."
        raise AuditMetadataError(msg)
    if key not in ALLOWED_METADATA_KEYS:
        msg = "Audit metadata key is not allowlisted."
        raise AuditMetadataError(msg)


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    return any(fragment in normalized for fragment in SENSITIVE_METADATA_KEY_FRAGMENTS)


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _sanitize_metadata_value(key: str, value: object, *, max_length: int) -> AuditScalar:
    value = _coerce_safe_scalar(value, max_length=max_length)
    if key in _IDENTIFIER_KEYS:
        return _validate_identifier_value(value)
    if key in _COUNT_KEYS:
        return _validate_count_value(value)
    if key in _ALLOWED_STRING_VALUES_BY_KEY:
        return _validate_domain_string_value(key, value)
    if value is not None:
        msg = "Audit metadata key has no value policy."
        raise AuditMetadataError(msg)
    return None


def _coerce_safe_scalar(value: object, *, max_length: int) -> AuditScalar:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, SecretStr):
        msg = "Audit metadata must not contain secret values."
        raise AuditMetadataError(msg)
    if isinstance(value, bytes | bytearray | memoryview):
        msg = "Audit metadata must not contain bytes."
        raise AuditMetadataError(msg)
    if isinstance(value, BaseException):
        msg = "Audit metadata must not contain exceptions."
        raise AuditMetadataError(msg)
    if hasattr(value, "_sa_instance_state"):
        msg = "Audit metadata must not contain ORM instances."
        raise AuditMetadataError(msg)
    if isinstance(value, Mapping | list | tuple | set):
        msg = "Audit metadata must not contain nested values."
        raise AuditMetadataError(msg)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        enum_value = value.value
        if not isinstance(enum_value, str):
            msg = "Audit metadata enum values must be strings."
            raise AuditMetadataError(msg)
        return _validate_string(enum_value, max_length=max_length)
    if isinstance(value, str):
        return _validate_string(value, max_length=max_length)
    if isinstance(value, int):
        return value

    msg = "Audit metadata values must be safe scalar values."
    raise AuditMetadataError(msg)


def _validate_identifier_value(value: AuditScalar) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "Audit metadata identifiers must be UUID strings."
        raise AuditMetadataError(msg)
    try:
        return str(UUID(value))
    except ValueError as exc:
        msg = "Audit metadata identifiers must be UUID strings."
        raise AuditMetadataError(msg) from exc


def _validate_count_value(value: AuditScalar) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        msg = "Audit metadata counts must be non-negative integers."
        raise AuditMetadataError(msg)
    return value


def _validate_domain_string_value(key: str, value: AuditScalar) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "Audit metadata value must be a string enum."
        raise AuditMetadataError(msg)
    normalized = value.strip().upper()
    if normalized not in _ALLOWED_STRING_VALUES_BY_KEY[key]:
        msg = "Audit metadata value is not allowlisted."
        raise AuditMetadataError(msg)
    return normalized


def _validate_string(value: str, *, max_length: int) -> str:
    if len(value) > max_length:
        msg = "Audit metadata string value is too long."
        raise AuditMetadataError(msg)
    return value


def _validate_serialized_length(
    metadata: Mapping[str, AuditScalar],
    *,
    max_length: int,
) -> None:
    if max_length <= 0:
        msg = "Audit metadata maximum length must be positive."
        raise AuditMetadataError(msg)
    serialized = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if len(serialized) > max_length:
        msg = "Audit metadata is too long."
        raise AuditMetadataError(msg)
