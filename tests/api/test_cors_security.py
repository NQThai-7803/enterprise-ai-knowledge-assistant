from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from tests.unit.test_production_config_validation import production_settings


def test_production_rejects_wildcard_origin_with_credentials() -> None:
    with pytest.raises(ValidationError):
        production_settings(cors_origins=["*"], cors_allow_credentials=True)


def test_allowed_origin_receives_cors_headers() -> None:
    settings = Settings(
        _env_file=None,
        cors_origins=["https://ui.example.com"],
        trusted_hosts=["testserver"],
    )
    client = TestClient(create_app(settings))

    response = client.get("/health/live", headers={"Origin": "https://ui.example.com"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://ui.example.com"


def test_unknown_origin_does_not_receive_cors_headers() -> None:
    settings = Settings(
        _env_file=None,
        cors_origins=["https://ui.example.com"],
        trusted_hosts=["testserver"],
    )
    client = TestClient(create_app(settings))

    response = client.get("/health/live", headers={"Origin": "https://evil.example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_uses_allowed_methods() -> None:
    settings = Settings(
        _env_file=None,
        cors_origins=["https://ui.example.com"],
        cors_allowed_methods=["GET", "POST", "OPTIONS"],
        trusted_hosts=["testserver"],
    )
    client = TestClient(create_app(settings))

    response = client.options(
        "/health/live",
        headers={
            "Origin": "https://ui.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "PUT" not in response.headers["access-control-allow-methods"]


@pytest.mark.parametrize(
    "origin",
    [
        "https://ui.example.com/path",
        "https://ui.example.com?debug=true",
        "https://ui.example.com#fragment",
    ],
)
def test_origin_with_path_query_or_fragment_is_rejected(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])


def test_origin_with_invalid_port_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=["https://ui.example.com:not-a-port"])
