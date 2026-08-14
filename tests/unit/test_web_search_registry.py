from __future__ import annotations

from pydantic import ValidationError

from app.core.config import Settings
from app.web_search.registry import create_web_search_provider_registry


def settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "web_search_provider": "mock",
        "chat_retrieval_top_k": 8,
        "citation_max_sources_per_answer": 8,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_registry_health_reports_disabled_by_default() -> None:
    registry = create_web_search_provider_registry(settings())

    health = registry.configuration_health()

    assert health.provider == "mock"
    assert health.status == "disabled"
    assert health.configured is False


def test_registry_creates_mock_provider_without_external_access() -> None:
    registry = create_web_search_provider_registry(
        settings(web_search_enabled=True, web_search_mode="hybrid")
    )

    provider = registry.create_provider()
    health = registry.configuration_health()

    assert provider.provider_name == "mock"
    assert health.status == "configured"
    assert health.external_allowed is True


def test_settings_rejects_unsupported_web_search_provider() -> None:
    try:
        Settings(_env_file=None, web_search_provider="unsupported")
    except ValidationError as exc:
        assert "WEB_SEARCH_PROVIDER" in str(exc) or "web_search_provider" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected validation failure")


def test_external_real_provider_requires_credentials_when_enabled() -> None:
    try:
        settings(
            web_search_enabled=True,
            web_search_mode="hybrid",
            web_search_provider="bing",
            web_search_allow_external=True,
        )
    except ValidationError as exc:
        assert "Selected web search provider" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected validation failure")


def test_google_custom_search_requires_key_and_engine_when_external() -> None:
    try:
        settings(
            web_search_enabled=True,
            web_search_mode="hybrid",
            web_search_provider="google_custom_search",
            web_search_allow_external=True,
            web_search_google_api_key="key",
            web_search_google_cx="",
        )
    except ValidationError as exc:
        assert "Selected web search provider" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected validation failure")
