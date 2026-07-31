from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from tests.unit.test_production_config_validation import production_settings


def test_trusted_host_is_allowed() -> None:
    client = TestClient(create_app(Settings(_env_file=None, trusted_hosts=["testserver"])))

    response = client.get("/health/live")

    assert response.status_code == 200


def test_untrusted_host_is_rejected() -> None:
    client = TestClient(create_app(Settings(_env_file=None, trusted_hosts=["testserver"])))

    response = client.get("/health/live", headers={"Host": "evil.example.com"})

    assert response.status_code == 400


def test_production_rejects_wildcard_trusted_hosts() -> None:
    with pytest.raises(ValidationError):
        production_settings(trusted_hosts=["*"])


def test_forwarded_host_is_not_blindly_trusted() -> None:
    client = TestClient(create_app(Settings(_env_file=None, trusted_hosts=["testserver"])))

    response = client.get(
        "/health/live",
        headers={"Host": "testserver", "X-Forwarded-Host": "evil.example.com"},
    )

    assert response.status_code == 200
