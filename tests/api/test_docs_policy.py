from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_docs_enabled_in_development() -> None:
    client = TestClient(create_app(Settings(_env_file=None, trusted_hosts=["testserver"])))

    response = client.get("/docs")

    assert response.status_code == 200


def test_docs_disabled_in_production_when_configured() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        api_docs_enabled=False,
        secret_key="prod-docs-secret-key-000000000000000000000000",
        database_url="postgresql+asyncpg://app_user:prod-docs-pass@db.internal:5432/enterprise_ai",
        redis_url="redis://redis.internal:6379/0",
        celery_broker_url="redis://redis.internal:6379/1",
        celery_result_backend="redis://redis.internal:6379/2",
        cors_origins=["https://ui.example.com"],
        trusted_hosts=["testserver"],
    )
    client = TestClient(create_app(settings))

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/health/live").status_code == 200


def test_api_routes_available_when_docs_disabled() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        api_docs_enabled=False,
        secret_key="prod-docs-route-secret-key-000000000000000000000000",
        database_url="postgresql+asyncpg://app_user:prod-docs-pass@db.internal:5432/enterprise_ai",
        redis_url="redis://redis.internal:6379/0",
        celery_broker_url="redis://redis.internal:6379/1",
        celery_result_backend="redis://redis.internal:6379/2",
        cors_origins=["https://ui.example.com"],
        trusted_hosts=["testserver"],
    )
    client = TestClient(create_app(settings))

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCESS_TOKEN_INVALID"
