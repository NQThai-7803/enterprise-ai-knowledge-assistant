import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_live_returns_200() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "Enterprise AI Knowledge Assistant",
        "environment": "development",
    }


def test_health_ready_returns_200_when_database_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_database_ready() -> bool:
        return True

    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        fake_database_ready,
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok"},
    }


def test_health_ready_returns_503_when_database_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_database_unavailable() -> bool:
        return False

    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        fake_database_unavailable,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable"},
    }
