"""HTTP client for the eval runners: one keep-alive httpx.Client per run, explicit INFRA_ERROR.

Classification of one question:
- 2xx with a chat answer body                         -> OK
- transport error, timeout, 5xx, 2xx without a body   -> INFRA_ERROR (never OK)
- 429 after the configured retries                    -> INFRA_ERROR (rate limit)
- any other non-2xx (for example 400/422)             -> HTTP_ERROR
A 401 triggers one re-login and one retry of the same request.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

OK = "OK"
INFRA_ERROR = "INFRA_ERROR"
HTTP_ERROR = "HTTP_ERROR"


class EvalInfraError(RuntimeError):
    """Login or session creation failed for an infrastructure reason."""


@dataclass(frozen=True, slots=True)
class AskResult:
    http_status: int
    body: Any
    latency_ms: int
    execution_status: str
    failure_class: str | None


class EvalClient:
    def __init__(
        self,
        base_url: str,
        *,
        email: str,
        password: str,
        timeout_seconds: float = 420.0,
        rate_limit_retries: int = 3,
        retry_sleep_seconds: float = 2.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._email = email
        self._password = password
        self._rate_limit_retries = rate_limit_retries
        self._retry_sleep_seconds = retry_sleep_seconds
        self._token: str | None = None
        self._expires_at = 0.0
        # One client, so every request of a run reuses keep-alive connections.
        self.http = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    def __enter__(self) -> EvalClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self.http.close()

    def login(self) -> None:
        status, body, failure = self._send(
            "POST",
            "/api/v1/auth/login",
            {
                "email": self._email,
                "password": self._password,
            },
            authenticated=False,
        )
        if failure is not None or status != 200 or not isinstance(body, dict):
            raise EvalInfraError(f"login failed: status={status} failure={failure}")
        data = body["data"]
        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 900))

    def create_session(self, title: str) -> str:
        status, body, failure = self._send("POST", "/api/v1/chat/sessions", {"title": title})
        if failure is not None or status != 201 or not isinstance(body, dict):
            raise EvalInfraError(f"session failed: status={status} failure={failure}")
        return str(body["data"]["id"])

    def ask(self, session_id: str, question: str) -> AskResult:
        path = f"/api/v1/chat/sessions/{session_id}/messages"
        started = time.perf_counter()
        for attempt in range(self._rate_limit_retries + 1):
            status, body, failure = self._send("POST", path, {"content": question})
            if status == 429 and attempt < self._rate_limit_retries:
                time.sleep(self._retry_sleep_seconds * (attempt + 1))
                continue
            break
        latency_ms = round((time.perf_counter() - started) * 1000)
        return AskResult(status, body, latency_ms, *classify(status, body, failure))

    def _send(
        self,
        method: str,
        path: str,
        payload: dict[str, object],
        *,
        authenticated: bool = True,
    ) -> tuple[int, Any, str | None]:
        if authenticated and (self._token is None or time.time() > self._expires_at - 90):
            self.login()
        for attempt in (1, 2):
            headers = {"Authorization": f"Bearer {self._token}"} if authenticated else {}
            try:
                response = self.http.request(method, path, json=payload, headers=headers)
            except httpx.TimeoutException:
                return 0, None, "INFRA_TIMEOUT"
            except httpx.TransportError:
                return 0, None, "INFRA_TRANSPORT"
            if response.status_code == 401 and authenticated and attempt == 1:
                self.login()
                continue
            try:
                body: Any = response.json()
            except ValueError:
                body = None
            return response.status_code, body, None
        return 401, None, None


def classify(status: int, body: Any, failure: str | None) -> tuple[str, str | None]:
    if failure is not None:
        return INFRA_ERROR, failure
    if status == 429:
        return INFRA_ERROR, "INFRA_RATE_LIMIT"
    if status >= 500:
        return INFRA_ERROR, "INFRA_HTTP_5XX"
    if not 200 <= status < 300:
        return HTTP_ERROR, f"HTTP_{status}"
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict) or not isinstance(data.get("assistant_message"), dict):
        return INFRA_ERROR, "INFRA_BAD_RESPONSE"
    return OK, None


def extract(result: AskResult) -> dict[str, object]:
    """Flatten an answer into the case fields the graders read."""
    if result.execution_status == OK:
        data = result.body["data"]
        message = data["assistant_message"]
        return {
            "status": data.get("grounding_status"),
            "answer": message.get("content", ""),
            "citations": message.get("citations", []),
            "retrieved": data.get("retrieved_chunk_count", 0),
            "http": result.http_status,
            "latency_ms": result.latency_ms,
            "execution_status": OK,
            "failure_class": None,
        }
    return {
        "status": result.execution_status,
        "answer": "",
        "citations": [],
        "retrieved": 0,
        "http": result.http_status,
        "latency_ms": result.latency_ms,
        "execution_status": result.execution_status,
        "failure_class": result.failure_class,
    }
