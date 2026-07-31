from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize(
    "secret_message",
    [
        "SECRET_DATABASE_URL=postgresql://hidden",
        "REDIS_URL=redis://:hidden@redis:6379/0",
        "provider api_key=hidden-provider-key",
    ],
)
def test_unhandled_exception_returns_safe_500(secret_message: str) -> None:
    app = create_app(Settings(_env_file=None, app_debug=False, trusted_hosts=["testserver"]))

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError(secret_message)

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "Internal server error.",
        "details": None,
        "request_id": None,
    }
    assert secret_message not in response.text
    assert "Traceback" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
