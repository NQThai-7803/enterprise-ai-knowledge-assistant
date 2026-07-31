from __future__ import annotations

from http import HTTPStatus

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings

REQUEST_TOO_LARGE_CODE = "REQUEST_TOO_LARGE"


class RequestBodyTooLargeError(Exception):
    """Raised internally when streamed request bytes exceed the configured cap."""


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
