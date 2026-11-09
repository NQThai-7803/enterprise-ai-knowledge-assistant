"""The RBAC dev runner logs in again once when setup outlives the access token."""

from __future__ import annotations

import httpx

from scripts.eval import run_rbac_dev


def test_admin_logs_in_again_once_on_401() -> None:
    calls: list[str] = []
    tokens = iter(["first", "second"])

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"access_token": next(tokens)}})
        if request.headers["Authorization"] == "Bearer first":
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"data": ["ok"]})

    admin = object.__new__(run_rbac_dev._Admin)
    admin.http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    admin.password = "x"
    admin._login()

    assert admin.get("/api/v1/users") == ["ok"]
    assert calls == ["/api/v1/auth/login", "/api/v1/users", "/api/v1/auth/login", "/api/v1/users"]
