from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import (
    ApplicationError,
    RateLimitExceededError,
    application_error_handler,
)
from app.core.rate_limit import (
    InMemoryFixedWindowRateLimiter,
    RateLimiterUnavailableError,
    RateLimitRule,
    RedisFixedWindowRateLimiter,
    anonymous_identity,
    chat_rule,
    enforce_rate_limit,
    feedback_rule,
    login_rule,
    refresh_rule,
    upload_rule,
    user_identity,
)


def make_client() -> TestClient:
    limiter = InMemoryFixedWindowRateLimiter()
    rule = RateLimitRule(scope="login", requests=1, window_seconds=60, fail_closed=True)
    app = FastAPI()
    app.add_exception_handler(ApplicationError, application_error_handler)

    @app.post("/auth/login")
    async def login(request: Request) -> dict[str, str]:
        await enforce_rate_limit(
            request,
            rule=rule,
            identity="ip:127.0.0.1",
            limiter=limiter,
        )
        return {"status": "ok"}

    return TestClient(app)


def test_login_rate_limit_returns_429_with_retry_after() -> None:
    client = make_client()

    assert client.post("/auth/login").status_code == 200
    response = client.post("/auth/login")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert int(response.headers["retry-after"]) > 0


def test_rate_limit_errors_do_not_expose_backend_key() -> None:
    client = make_client()
    client.post("/auth/login")

    response = client.post("/auth/login")

    assert "rate-limit:" not in response.text
    assert "ip:127.0.0.1" not in response.text


class FailingLimiter:
    async def check(self, *, identity: str, rule: RateLimitRule):  # noqa: ANN201
        raise RateLimiterUnavailableError


def request_with_forwarded_headers() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "headers": [(b"x-forwarded-for", b"203.0.113.99")],
            "client": ("127.0.0.1", 12345),
        }
    )


@pytest.mark.anyio
async def test_redis_failure_fail_closed_returns_rate_limit_error() -> None:
    rule = RateLimitRule(scope="login", requests=1, window_seconds=60, fail_closed=True)

    with pytest.raises(RateLimitExceededError) as exc_info:
        await enforce_rate_limit(
            request_with_forwarded_headers(),
            rule=rule,
            identity="ip:127.0.0.1",
            limiter=FailingLimiter(),
            settings=Settings(_env_file=None),
        )

    assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"
    assert exc_info.value.headers == {"Retry-After": "60"}


@pytest.mark.anyio
async def test_redis_failure_fail_open_allows_non_critical_request() -> None:
    rule = RateLimitRule(scope="feedback", requests=1, window_seconds=60, fail_closed=False)

    await enforce_rate_limit(
        request_with_forwarded_headers(),
        rule=rule,
        identity="user:123",
        limiter=FailingLimiter(),
        settings=Settings(_env_file=None),
    )


@pytest.mark.anyio
async def test_redis_limiter_uses_transactional_pipeline(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    class FakePipeline:
        def incr(self, key: str) -> None:
            captured["incr_key"] = key

        def expire(self, key: str, seconds: int) -> None:
            captured["expire_key"] = key
            captured["expire_seconds"] = seconds

        async def execute(self) -> list[object]:
            captured["executed"] = True
            return [2, True]

    class FakeRedis:
        @classmethod
        def from_url(cls, url: str, **kwargs: object) -> FakeRedis:
            captured["url"] = url
            captured.update(kwargs)
            return cls()

        def pipeline(self, *, transaction: bool) -> FakePipeline:
            captured["transaction"] = transaction
            return FakePipeline()

        async def aclose(self) -> None:
            captured["closed"] = True

    settings = Settings(
        _env_file=None,
        redis_url="redis://redis.example.internal:6379/0",
        redis_connect_timeout_seconds=7,
        redis_socket_timeout_seconds=8,
        redis_health_check_interval_seconds=9,
    )
    monkeypatch.setattr("app.core.rate_limit.Redis", FakeRedis)

    decision = await RedisFixedWindowRateLimiter(settings).check(
        identity="user:abc",
        rule=RateLimitRule(scope="chat", requests=1, window_seconds=60, fail_closed=True),
    )

    assert decision.allowed is False
    assert captured["transaction"] is True
    assert captured["incr_key"] == captured["expire_key"]
    assert captured["expire_seconds"] == 60
    assert captured["socket_connect_timeout"] == 7
    assert captured["socket_timeout"] == 8
    assert captured["health_check_interval"] == 9
    assert captured["closed"] is True


def test_spoofed_forwarded_for_does_not_change_identity() -> None:
    assert anonymous_identity(request_with_forwarded_headers()) == "ip:127.0.0.1"


def test_rate_limit_rules_match_endpoint_policies() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        secret_key="prod-rate-limit-secret-key-000000000000000000000000",
        database_url=(
            "postgresql+asyncpg://app_user:prod-rate-pass@db.internal:5432/enterprise_ai"
        ),
        redis_url="redis://redis.internal:6379/0",
        celery_broker_url="redis://redis.internal:6379/1",
        celery_result_backend="redis://redis.internal:6379/2",
        cors_origins=["https://ui.example.com"],
        trusted_hosts=["api.example.com"],
    )

    assert login_rule(settings).scope == "login"
    assert refresh_rule(settings).scope == "refresh"
    assert upload_rule(settings).scope == "upload"
    assert chat_rule(settings).scope == "chat"
    assert feedback_rule(settings).scope == "feedback"
    assert login_rule(settings).fail_closed is True
    assert refresh_rule(settings).fail_closed is True
    assert upload_rule(settings).fail_closed is True
    assert chat_rule(settings).fail_closed is True
    assert feedback_rule(settings).fail_closed is False
    assert user_identity(uuid4()).startswith("user:")
