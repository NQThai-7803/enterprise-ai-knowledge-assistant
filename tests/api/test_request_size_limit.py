from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.middleware import RequestSizeLimitMiddleware


def make_client(*, max_body_bytes: int = 5) -> TestClient:
    app = FastAPI()

    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        body = await request.body()
        return {"size": len(body)}

    app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=max_body_bytes)
    return TestClient(app, raise_server_exceptions=False)


def test_request_under_limit_passes() -> None:
    response = make_client().post("/echo", content=b"12345")

    assert response.status_code == 200
    assert response.json() == {"size": 5}


def test_content_length_over_limit_returns_413() -> None:
    response = make_client().post("/echo", content=b"", headers={"content-length": "6"})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_streamed_body_over_limit_returns_413() -> None:
    def chunks():
        yield b"123"
        yield b"456"

    response = make_client().post("/echo", content=chunks())

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_error_does_not_include_request_body() -> None:
    marker = b"SECRET_BODY_MARKER"
    response = make_client(max_body_bytes=4).post("/echo", content=marker)

    assert response.status_code == 413
    assert marker.decode("ascii") not in response.text


def test_missing_content_length_still_enforces_limit() -> None:
    def chunks():
        yield b"12"
        yield b"345"

    response = make_client(max_body_bytes=4).post("/echo", content=chunks())

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_request_body_is_not_logged(caplog) -> None:  # noqa: ANN001
    marker = "SECRET_REQUEST_BODY_MARKER"

    with caplog.at_level("INFO"):
        response = make_client(max_body_bytes=4).post("/echo", content=marker.encode("ascii"))

    assert response.status_code == 413
    assert marker not in caplog.text
