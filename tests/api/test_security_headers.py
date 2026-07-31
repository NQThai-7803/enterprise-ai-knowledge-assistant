from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

REQUIRED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cache-control": "no-store",
}


def test_api_responses_have_security_headers() -> None:
    client = TestClient(create_app(Settings(_env_file=None, trusted_hosts=["testserver"])))

    response = client.get("/health/live")

    for key, value in REQUIRED_HEADERS.items():
        assert response.headers[key] == value


def test_error_responses_have_security_headers() -> None:
    client = TestClient(create_app(Settings(_env_file=None, trusted_hosts=["testserver"])))

    response = client.get("/missing")

    assert response.status_code == 404
    for key, value in REQUIRED_HEADERS.items():
        assert response.headers[key] == value


def test_hsts_disabled_on_local_http() -> None:
    client = TestClient(create_app(Settings(_env_file=None, trusted_hosts=["testserver"])))

    response = client.get("/health/live")

    assert "strict-transport-security" not in response.headers


def test_hsts_enabled_only_for_production_https() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        secret_key="prod-hsts-secret-key-000000000000000000000000",
        database_url="postgresql+asyncpg://app_user:prod-hsts-pass@db.internal:5432/enterprise_ai",
        redis_url="redis://redis.internal:6379/0",
        celery_broker_url="redis://redis.internal:6379/1",
        celery_result_backend="redis://redis.internal:6379/2",
        cors_origins=["https://ui.example.com"],
        trusted_hosts=["api.example.com"],
    )
    client = TestClient(create_app(settings), base_url="https://api.example.com")

    response = client.get("/health/live")

    assert response.headers["strict-transport-security"] == "max-age=31536000"
