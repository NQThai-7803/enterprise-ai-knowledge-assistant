from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

PROD_DEFAULTS = {
    "_env_file": None,
    "app_env": "production",
    "app_debug": False,
    "secret_key": "prod-jwt-signing-key-000000000000000000000000",
    "database_url": "postgresql+asyncpg://app_user:prod-db-pass-123@db.internal:5432/enterprise_ai",
    "redis_url": "redis://redis.internal:6379/0",
    "celery_broker_url": "redis://redis.internal:6379/1",
    "celery_result_backend": "redis://redis.internal:6379/2",
    "cors_origins": ["https://assistant.example.com"],
    "trusted_hosts": ["api.example.com"],
}


def production_settings(**overrides: object) -> Settings:
    values = dict(PROD_DEFAULTS)
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError) as exc_info:
        production_settings(secret_key="replace-with-a-long-random-secret-key")

    assert "SECRET_KEY must be a non-placeholder value" in str(exc_info.value)
    assert "replace-with-a-long-random-secret-key" not in str(exc_info.value)


def test_production_rejects_empty_database_password() -> None:
    with pytest.raises(ValidationError) as exc_info:
        production_settings(
            database_url="postgresql+asyncpg://app_user:@db.internal:5432/enterprise_ai"
        )

    assert "DATABASE_URL must include a non-placeholder password" in str(exc_info.value)
    assert "app_user:" not in str(exc_info.value)


def test_development_accepts_documented_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.app_debug is False
    assert settings.secret_key == "replace-with-a-long-random-secret-key"


def test_config_repr_hides_secrets() -> None:
    settings = Settings(
        _env_file=None,
        secret_key="repr-hidden-secret-key-000000000000000000000000",
        database_url="postgresql+asyncpg://app_user:hidden-db-pass@localhost:55432/enterprise_ai",
        redis_url="redis://:hidden-redis-pass@localhost:6379/0",
    )

    rendered = repr(settings)

    assert "repr-hidden-secret-key" not in rendered
    assert "hidden-db-pass" not in rendered
    assert "hidden-redis-pass" not in rendered


def test_production_rejects_debug_enabled() -> None:
    with pytest.raises(ValidationError) as exc_info:
        production_settings(app_debug=True)

    assert "APP_DEBUG must be false in production" in str(exc_info.value)


def test_production_rejects_legacy_debug_enabled() -> None:
    with pytest.raises(ValidationError) as exc_info:
        production_settings(app_debug=False, debug=True)

    assert "APP_DEBUG must be false in production" in str(exc_info.value)


def test_production_rejects_additional_placeholder_secrets() -> None:
    for placeholder in (
        "changeme",
        "secret",
        "development-secret",
        "replace-me",
        "your-secret-here",
        "example",
    ):
        with pytest.raises(ValidationError) as exc_info:
            production_settings(secret_key=placeholder)

        assert "SECRET_KEY must be a non-placeholder value" in str(exc_info.value)
        assert placeholder not in str(exc_info.value)


def test_test_environment_accepts_test_defaults() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        secret_key="test-environment-secret-key-000000000000000000000000",
        database_url="postgresql+asyncpg://app_user:test-password@localhost:55432/enterprise_ai_test",
    )

    assert settings.app_env == "test"
    assert settings.app_debug is False
