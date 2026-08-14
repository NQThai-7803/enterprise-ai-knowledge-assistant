from __future__ import annotations

import logging
from http import HTTPStatus
from time import perf_counter

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.request_context import (
    new_request_id,
    reset_request_context,
    sanitize_request_id,
    sanitize_traceparent,
    set_request_context,
)
from app.observability.metrics import GLOBAL_METRICS, MetricsRegistry, route_template_from_scope

REQUEST_TOO_LARGE_CODE = "REQUEST_TOO_LARGE"
logger = logging.getLogger(__name__)


class RequestBodyTooLargeError(Exception):
    """Raised internally when streamed request bytes exceed the configured cap."""


class RequestObservabilityMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings,
        metrics_registry: MetricsRegistry = GLOBAL_METRICS,
    ) -> None:
        self.app = app
        self.settings = settings
        self.metrics_registry = metrics_registry
        self.request_id_header = settings.request_id_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.observability_enabled:
            await self.app(scope, receive, send)
            return

        headers = _scope_headers(scope)
        request_id = (
            sanitize_request_id(_header_value(headers, self.settings.request_id_header))
            or new_request_id()
        )
        traceparent = (
            sanitize_traceparent(_header_value(headers, self.settings.traceparent_header))
            if self.settings.tracing_hooks_enabled
            else None
        )
        context_tokens = set_request_context(
            request_id=request_id,
            traceparent=traceparent,
        )
        method = str(scope.get("method") or "GET").upper()
        status_code = int(HTTPStatus.INTERNAL_SERVER_ERROR)
        started_at = perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_headers = MutableHeaders(scope=message)
                response_headers.setdefault(self.request_id_header, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            latency_seconds = perf_counter() - started_at
            route = route_template_from_scope(scope, status_code=status_code)
            if self.settings.metrics_enabled:
                self.metrics_registry.record_http_request(
                    method=method,
                    route=route,
                    status_code=status_code,
                    latency_seconds=latency_seconds,
                )
            if self.settings.request_log_enabled:
                logger.info(
                    "HTTP request completed.",
                    extra={
                        "event": "http_request_completed",
                        "request_id": request_id,
                        "method": method,
                        "route": route,
                        "status_code": status_code,
                        "latency_ms": round(latency_seconds * 1000, 3),
                        "trace_present": traceparent is not None,
                    },
                )
            reset_request_context(context_tokens)


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_body_bytes: int) -> None:
        if max_body_bytes <= 0:
            msg = "max_body_bytes must be greater than zero."
            raise ValueError(msg)
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = _scope_headers(scope)
        content_length = headers.get(b"content-length")
        if content_length is not None and _content_length_over_limit(
            content_length,
            self.max_body_bytes,
        ):
            await _send_request_too_large(send)
            return

        consumed = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] != "http.request":
                return message
            body = message.get("body", b"")
            if body:
                consumed += len(body)
                if consumed > self.max_body_bytes:
                    raise RequestBodyTooLargeError
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, send_wrapper)
        except RequestBodyTooLargeError:
            if not response_started:
                await _send_request_too_large(send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault(
                    "Permissions-Policy",
                    "camera=(), microphone=(), geolocation=()",
                )
                headers.setdefault("Cache-Control", "no-store")
                if self.settings.app_env == "production" and scope.get("scheme") == "https":
                    headers.setdefault("Strict-Transport-Security", "max-age=31536000")
            await send(message)

        await self.app(scope, receive, send_wrapper)


def _scope_headers(scope: Scope) -> dict[bytes, bytes]:
    return {key.lower(): value for key, value in scope.get("headers", [])}


def _header_value(headers: dict[bytes, bytes], header_name: str) -> str | None:
    try:
        raw_value = headers.get(header_name.lower().encode("ascii"))
    except UnicodeEncodeError:
        return None
    if raw_value is None:
        return None
    try:
        return raw_value.decode("ascii")
    except UnicodeDecodeError:
        return None


def _content_length_over_limit(value: bytes, max_body_bytes: int) -> bool:
    try:
        content_length = int(value.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return False
    return content_length > max_body_bytes


async def _send_request_too_large(send: Send) -> None:
    body = (
        b'{"error":{"code":"REQUEST_TOO_LARGE",'
        b'"message":"Request body is too large.",'
        b'"details":null,"request_id":null}}'
    )
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    ]
    await send(
        {
            "type": "http.response.start",
            "status": HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            "headers": headers,
        }
    )
    await send({"type": "http.response.body", "body": body})
