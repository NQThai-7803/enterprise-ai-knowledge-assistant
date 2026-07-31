from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_LOG_KEYS = {
    "access_token",
    "api_key",
    "assistant_answer",
    "authorization",
    "chat_content",
    "chat_question",
    "citation_excerpt",
    "context",
    "cookie",
    "database_url",
    "document_content",
    "document_text",
    "excerpt",
    "feedback_reason",
    "password",
    "prompt",
    "question",
    "redis_url",
    "refresh_token",
    "secret",
    "token",
}
REDACTED = "[REDACTED]"
_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(access_token|api_key|assistant_answer|authorization|chat_content|chat_question|citation_excerpt|context|cookie|database_url|document_content|document_text|excerpt|feedback_reason|password|prompt|question|redis_url|refresh_token|secret|token)\b"
    r"\s*[:=]\s*([^\s,;]+)"
)


class SensitiveDataRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_string(str(record.msg))
        if isinstance(record.args, Mapping):
            record.args = redact_mapping(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(redact_value(value) for value in record.args)

        for key, value in list(record.__dict__.items()):
            if _is_sensitive_key(key):
                setattr(record, key, REDACTED)
            elif isinstance(value, Mapping):
                setattr(record, key, redact_mapping(value))
        return True


def configure_logging_redaction() -> None:
    root_logger = logging.getLogger()
    if any(isinstance(filter_, SensitiveDataRedactionFilter) for filter_ in root_logger.filters):
        return
    root_logger.addFilter(SensitiveDataRedactionFilter())


def redact_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): (REDACTED if _is_sensitive_key(str(key)) else redact_value(value))
        for key, value in mapping.items()
    }


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_string(value: str) -> str:
    return _KEY_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}={REDACTED}", value)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(marker in normalized for marker in SENSITIVE_LOG_KEYS)
