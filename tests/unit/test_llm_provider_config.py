from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET_MARKER = "SECRET_PROVIDER_CONFIG_MARKER"


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {"_env_file": None}
    defaults.update(overrides)
    return Settings(**defaults)


def test_llm_disabled_requires_no_provider_key() -> None:
    settings = make_settings(
        llm_enabled=False,
        llm_provider="gemini",
        llm_model="",
        llm_gemini_model="",
        llm_gemini_api_key="",
    )

    assert settings.llm_enabled is False


def test_selected_provider_requires_its_configuration() -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_enabled=True, llm_provider="azure_openai")


def test_unselected_provider_does_not_require_key() -> None:
    settings = make_settings(
        llm_enabled=True,
        llm_provider="ollama",
        llm_ollama_model="llama3",
        llm_gemini_api_key="",
        llm_anthropic_api_key="",
    )

    assert settings.llm_provider == "ollama"


def test_ollama_reasoning_effort_defaults_to_none() -> None:
    settings = make_settings(
        llm_enabled=True,
        llm_provider="ollama",
        llm_ollama_model="qwen3:4b",
    )

    assert settings.llm_ollama_reasoning_effort == "none"


def test_ollama_reasoning_effort_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        make_settings(
            llm_enabled=True,
            llm_provider="ollama",
            llm_ollama_model="qwen3:4b",
            llm_ollama_reasoning_effort="verbose",
        )


def test_provider_secrets_hidden_from_repr() -> None:
    settings = make_settings(
        llm_enabled=True,
        llm_provider="openrouter",
        llm_openrouter_model="openai/gpt-test",
        llm_openrouter_api_key=SECRET_MARKER,
    )

    assert SECRET_MARKER not in repr(settings)


def test_provider_secret_not_in_validation_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_settings(
            llm_enabled=True,
            llm_provider="openrouter",
            llm_openrouter_base_url="https://user:pass@example.com/api/v1",
            llm_openrouter_model="openai/gpt-test",
            llm_openrouter_api_key=SECRET_MARKER,
        )

    rendered = str(exc_info.value)
    assert SECRET_MARKER not in rendered
    assert "user:pass" not in rendered


def test_openai_compatible_remote_provider_requires_api_key() -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_settings(
            llm_enabled=True,
            llm_provider="openai_compatible",
            llm_base_url="https://api.openai.example/v1",
            llm_model="gpt-test",
            llm_api_key="",
        )

    rendered = str(exc_info.value)
    assert "SECRET" not in rendered
    assert "api.openai.example" not in rendered


def test_openai_compatible_remote_provider_accepts_api_key() -> None:
    settings = make_settings(
        llm_enabled=True,
        llm_provider="openai_compatible",
        llm_base_url="https://api.openai.example/v1",
        llm_model="gpt-test",
        llm_api_key=SECRET_MARKER,
    )

    assert settings.llm_provider == "openai_compatible"


def test_openai_compatible_local_provider_allows_optional_api_key() -> None:
    settings = make_settings(
        llm_enabled=True,
        llm_provider="openai_compatible",
        llm_base_url="http://localhost:11434/v1",
        llm_model="local-test",
        llm_api_key="",
    )

    assert settings.llm_provider == "openai_compatible"
