from __future__ import annotations

import json

import pytest

from app.chat.sse import SSEEventStateError, SSEEventWriter, encode_sse


def _frame_text(frame: bytes) -> str:
    return frame.decode("utf-8")


def _event_data(frame: bytes) -> dict[str, object]:
    for line in _frame_text(frame).splitlines():
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError("SSE frame has no data line")


def test_sse_event_format() -> None:
    frame = _frame_text(encode_sse(event="message.delta", event_id="req-1", data={"x": 1}))

    assert frame.startswith("id: req-1\nevent: message.delta\ndata: ")
    assert frame.endswith("\n\n")


def test_sse_event_json_encoding() -> None:
    frame = _frame_text(encode_sse(event="message.delta", data={"content": "hello", "sequence": 1}))

    assert 'data: {"content":"hello","sequence":1}' in frame


def test_sse_supports_unicode() -> None:
    frame = _frame_text(encode_sse(event="message.delta", data={"content": "Xin chào"}))

    assert "Xin chào" in frame
    assert _event_data(frame.encode("utf-8"))["content"] == "Xin chào"


def test_sse_does_not_allow_raw_newline_injection() -> None:
    frame = _frame_text(
        encode_sse(
            event="message.delta",
            data={"content": "safe\nevent: stream.error\ndata: {}"},
        )
    )

    assert "\nevent: stream.error" not in frame
    assert "\\nevent: stream.error" in frame


def test_sse_terminal_blank_line() -> None:
    assert _frame_text(encode_sse(event="heartbeat", data={})).endswith("\n\n")


def test_stream_started_is_first_event() -> None:
    writer = SSEEventWriter(request_id="req")

    with pytest.raises(SSEEventStateError):
        writer.delta(content="not started")

    assert "event: stream.started" in _frame_text(writer.started({"request_id": "req"}))


def test_delta_sequence_is_monotonic() -> None:
    writer = SSEEventWriter(request_id="req")
    writer.started({"request_id": "req"})

    first = _event_data(writer.delta(content="a"))["sequence"]
    second = _event_data(writer.delta(content="b"))["sequence"]

    assert (first, second) == (1, 2)


def test_completed_is_terminal() -> None:
    writer = SSEEventWriter(request_id="req")
    writer.started({"request_id": "req"})

    completed = writer.completed({"message_id": "m1"})

    assert "event: message.completed" in _frame_text(completed)
    with pytest.raises(SSEEventStateError):
        writer.delta(content="late")


def test_error_is_terminal() -> None:
    writer = SSEEventWriter(request_id="req")
    writer.started({"request_id": "req"})

    error = writer.error({"code": "STREAM_INTERNAL_ERROR", "message": "safe"})

    assert "event: stream.error" in _frame_text(error)
    with pytest.raises(SSEEventStateError):
        writer.completed({"message_id": "late"})


def test_cancelled_is_terminal() -> None:
    writer = SSEEventWriter(request_id="req")
    writer.started({"request_id": "req"})

    cancelled = writer.cancelled({"code": "STREAM_CANCELLED"})

    assert "event: stream.cancelled" in _frame_text(cancelled)
    with pytest.raises(SSEEventStateError):
        writer.heartbeat()


def test_no_delta_after_terminal_event() -> None:
    writer = SSEEventWriter(request_id="req")
    writer.started({"request_id": "req"})
    writer.completed({"message_id": "m1"})

    with pytest.raises(SSEEventStateError):
        writer.delta(content="late")


def test_terminal_event_emitted_once() -> None:
    writer = SSEEventWriter(request_id="req")
    writer.started({"request_id": "req"})
    writer.error({"code": "STREAM_INTERNAL_ERROR"})

    with pytest.raises(SSEEventStateError):
        writer.error({"code": "STREAM_INTERNAL_ERROR"})
