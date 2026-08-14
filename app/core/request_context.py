from __future__ import annotations

import re
from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import uuid4

MAX_REQUEST_ID_LENGTH = 128
_SAFE_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TRACEPARENT_PATTERN = re.compile(
    r"^[\da-f]{2}-[\da-f]{32}-[\da-f]{16}-[\da-f]{2}$",
    re.IGNORECASE,
)

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_traceparent: ContextVar[str | None] = ContextVar("traceparent", default=None)


@dataclass(frozen=True, slots=True)
class RequestContextTokens:
    request_id: Token[str | None]
    traceparent: Token[str | None]


def new_request_id() -> str:
    return uuid4().hex


def sanitize_request_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if _SAFE_REQUEST_ID_PATTERN.fullmatch(normalized):
        return normalized
    return None


def sanitize_traceparent(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if _TRACEPARENT_PATTERN.fullmatch(normalized):
        return normalized.lower()
    return None


def set_request_context(
    *,
    request_id: str,
    traceparent: str | None,
) -> RequestContextTokens:
    return RequestContextTokens(
        request_id=_request_id.set(request_id),
        traceparent=_traceparent.set(traceparent),
    )


def reset_request_context(tokens: RequestContextTokens) -> None:
    _request_id.reset(tokens.request_id)
    _traceparent.reset(tokens.traceparent)


def get_request_id() -> str | None:
    return _request_id.get()


def get_traceparent() -> str | None:
    return _traceparent.get()
