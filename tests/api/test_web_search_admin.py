from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.models import User, UserRole
from app.web_search.manager import WebSearchProviderManager

pytestmark = pytest.mark.integration


def install_web_search_manager(api_client: TestClient, settings: Settings):
    previous = api_client.app.state.web_search_provider_manager
    manager = WebSearchProviderManager(settings)
    api_client.app.state.web_search_provider_manager = manager
    return previous, manager


def restore_web_search_manager(api_client: TestClient, previous, manager) -> None:  # noqa: ANN001
    asyncio.run(manager.aclose())
    api_client.app.state.web_search_provider_manager = previous


def test_web_search_provider_status_is_admin_only(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)
    admin = make_user(role=UserRole.ADMIN)

    forbidden = api_client.get(
        "/api/v1/web-search/provider-status",
        headers=make_auth_headers(staff),
    )
    allowed = api_client.get(
        "/api/v1/web-search/provider-status",
        headers=make_auth_headers(admin),
    )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    data = allowed.json()["data"]
    assert data["provider"] == "mock"
    assert data["status"] in {"disabled", "configured"}
    assert "api_key" not in allowed.text.lower()


def test_web_search_test_endpoint_uses_mock_provider(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    previous, manager = install_web_search_manager(
        api_client,
        Settings(
            _env_file=None,
            web_search_enabled=True,
            web_search_mode="hybrid",
            web_search_provider="mock",
            web_search_max_results=1,
        ),
    )
    try:
        response = api_client.post(
            "/api/v1/web-search/test",
            headers=make_auth_headers(admin),
            json={"query": "OpenAI Docs"},
        )
    finally:
        restore_web_search_manager(api_client, previous, manager)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["provider"] == "mock"
    assert data["result_count"] == 1
    assert data["results"][0]["source_url"] == "https://example.com/mock-web-result"


def test_web_search_test_endpoint_returns_safe_error_when_disabled(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    admin = make_user(role=UserRole.ADMIN)
    previous, manager = install_web_search_manager(
        api_client,
        Settings(_env_file=None, web_search_enabled=False, web_search_provider="mock"),
    )
    try:
        response = api_client.post(
            "/api/v1/web-search/test",
            headers=make_auth_headers(admin),
            json={"query": "CONFIDENTIAL_QUERY"},
        )
    finally:
        restore_web_search_manager(api_client, previous, manager)

    assert response.status_code == 422
    assert "Web search is disabled" in response.text
    assert "CONFIDENTIAL_QUERY" not in response.text
