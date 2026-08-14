from __future__ import annotations

import pytest

from app.core.config import Settings
from app.scripts.runtime_validation import validate_runtime


def production_settings(tmp_path, **overrides: object) -> Settings:  # noqa: ANN001
    values: dict[str, object] = {
        "_env_file": None,
        "app_env": "production",
        "api_docs_enabled": False,
        "secret_key": "prod-secret-key-000000000000000000000000000000",
        "database_url": "postgresql+asyncpg://app_user:prod-password@postgres:5432/enterprise_ai",
        "redis_url": "redis://redis:6379/0",
        "celery_broker_url": "redis://redis:6379/1",
        "celery_result_backend": "redis://redis:6379/2",
        "cors_origins": ["https://assistant.example.com"],
        "trusted_hosts": ["assistant.example.com"],
        "local_storage_path": str(tmp_path / "uploads"),
        "embedding_model_cache_path": str(tmp_path / "models"),
    }
    values.update(overrides)
    (tmp_path / "uploads").mkdir(exist_ok=True)
    (tmp_path / "models").mkdir(exist_ok=True)
    return Settings(**values)


def test_runtime_validation_accepts_valid_production_paths(tmp_path) -> None:
    settings = production_settings(tmp_path)

    assert validate_runtime(settings) == []


def test_runtime_validation_rejects_enabled_docs_in_production(tmp_path) -> None:
    settings = production_settings(tmp_path, api_docs_enabled=True)

    assert "API_DOCS_ENABLED must be false" in validate_runtime(settings)[0]


def test_settings_can_load_secret_file_values_before_production_validation(tmp_path) -> None:
    secret_key_file = tmp_path / "secret_key"
    database_url_file = tmp_path / "database_url"
    redis_url_file = tmp_path / "redis_url"
    broker_url_file = tmp_path / "broker_url"
    result_backend_file = tmp_path / "result_backend"
    llm_api_key_file = tmp_path / "llm_api_key"
    secret_key_file.write_text("file-secret-key-000000000000000000000000000000", encoding="utf-8")
    database_url_file.write_text(
        "postgresql+asyncpg://app_user:file-password@postgres:5432/enterprise_ai",
        encoding="utf-8",
    )
    redis_url_file.write_text("redis://redis:6379/0", encoding="utf-8")
    broker_url_file.write_text("redis://redis:6379/1", encoding="utf-8")
    result_backend_file.write_text("redis://redis:6379/2", encoding="utf-8")
    llm_api_key_file.write_text("llm-secret-from-file", encoding="utf-8")

    settings = production_settings(
        tmp_path,
        secret_key="replace-with-production-secret-key",
        database_url="postgresql+asyncpg://app_user:replace-with-production-postgres-password@postgres:5432/enterprise_ai",
        secret_key_file=str(secret_key_file),
        database_url_file=str(database_url_file),
        redis_url_file=str(redis_url_file),
        celery_broker_url_file=str(broker_url_file),
        celery_result_backend_file=str(result_backend_file),
        llm_api_key_file=str(llm_api_key_file),
    )

    assert settings.secret_key.startswith("file-secret-key")
    assert settings.database_url == database_url_file.read_text(encoding="utf-8")
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.celery_broker_url == "redis://redis:6379/1"
    assert settings.celery_result_backend == "redis://redis:6379/2"
    assert settings.llm_api_key.get_secret_value() == "llm-secret-from-file"


def test_secret_file_errors_are_generic(tmp_path) -> None:
    with pytest.raises(ValueError, match="Configured secret file"):
        production_settings(tmp_path, secret_key_file=str(tmp_path / "missing-secret"))
