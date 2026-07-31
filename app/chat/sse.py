from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from fastapi.encoders import jsonable_encoder

_SAFE_SSE_NAME = re.compile(r"^[A-Za-z0-9_.:-]+$")


class SSEEventStateError(RuntimeError):
    """Raised when stream events would violate the public SSE contract."""


def encode_sse(
    *,
    event: str,
    data: Mapping[str, Any],
    event_id: str | None = None,
) -> bytes:
    if not _is_safe_sse_field(event):
        msg = "SSE event name is invalid."
        raise ValueError(msg)
    if event_id is not None and not _is_safe_sse_field(event_id):
        msg = "SSE event id is invalid."
        raise ValueError(msg)
    encoded_data = json.dumps(
        jsonable_encoder(data),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {encoded_data}")
    return ("\n".join(lines) + "\n\n").encode("utf-8")


class SSEEventWriter:
    def __init__(self, *, request_id: str) -> None:
        if not _is_safe_sse_field(request_id):
            msg = "SSE request id is invalid."
            raise ValueError(msg)
        self.request_id = request_id
        self._event_index = 0
        self._delta_sequence = 0
        self._started = False
        self._terminal_emitted = False

    @property
    def terminal_emitted(self) -> bool:
        return self._terminal_emitted

    def started(self, data: Mapping[str, Any]) -> bytes:
        if self._started:
            msg = "stream.started has already been emitted."
            raise SSEEventStateError(msg)
        self._started = True
        return self._event("stream.started", data)

    def delta(self, *, content: str) -> bytes:
        self._assert_can_emit_non_terminal()
        self._delta_sequence += 1
        return self._event(
            "message.delta",
            {
                "sequence": self._delta_sequence,
                "content": content,
            },
        )

    def citations_ready(self, data: Mapping[str, Any]) -> bytes:
        self._assert_can_emit_non_terminal()
        return self._event("citations.ready", data)

    def completed(self, data: Mapping[str, Any]) -> bytes:
        return self._terminal("message.completed", data)

    def error(self, data: Mapping[str, Any]) -> bytes:
        return self._terminal("stream.error", data)

    def cancelled(self, data: Mapping[str, Any]) -> bytes:
        return self._terminal("stream.cancelled", data)

    def heartbeat(self, data: Mapping[str, Any] | None = None) -> bytes:
        self._assert_can_emit_non_terminal()
        return self._event("heartbeat", data or {})

    def _event(self, event: str, data: Mapping[str, Any]) -> bytes:
        if not self._started and event != "stream.started":
            msg = "stream.started must be the first event."
            raise SSEEventStateError(msg)
        self._event_index += 1
        return encode_sse(
            event=event,
            data=data,
            event_id=f"{self.request_id}-{self._event_index}",
        )

    def _terminal(self, event: str, data: Mapping[str, Any]) -> bytes:
        self._assert_can_emit_non_terminal()
        self._terminal_emitted = True
        return self._event(event, data)

    def _assert_can_emit_non_terminal(self) -> None:
        if not self._started:
            msg = "stream.started must be emitted before stream events."
            raise SSEEventStateError(msg)
        if self._terminal_emitted:
            msg = "No stream events may be emitted after a terminal event."
            raise SSEEventStateError(msg)


def _is_safe_sse_field(value: str) -> bool:
    return bool(value and len(value) <= 128 and _SAFE_SSE_NAME.fullmatch(value))
