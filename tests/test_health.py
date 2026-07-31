import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_live_returns_200() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_does_not_expose_configuration() -> None:
    response = client.get("/health/live")
    payload = response.json()

    assert payload == {"status": "ok"}
    assert "app_name" not in payload
    assert "environment" not in payload
    assert "version" not in payload
    assert "host" not in payload


def test_liveness_does_not_require_database_or_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_database_ready() -> bool:
        raise AssertionError("liveness must not check database")

    async def fail_redis_ready() -> bool:
        raise AssertionError("liveness must not check redis")

    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        fail_database_ready,
    )
    monkeypatch.setattr(
        "app.api.routes.health.check_redis_connection",
        fail_redis_ready,
    )

    response = client.get("/health/live")

    assert response.status_code == 200


def test_health_ready_returns_200_when_dependencies_are_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_database_ready() -> bool:
        return True

    async def fake_redis_ready() -> bool:
        return True

    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        fake_database_ready,
    )
    monkeypatch.setattr(
        "app.api.routes.health.check_redis_connection",
        fake_redis_ready,
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok"},
    }


def test_health_ready_returns_503_when_database_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_database_unavailable() -> bool:
        return False

    async def fake_redis_ready() -> bool:
        return True

    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        fake_database_unavailable,
    )
    monkeypatch.setattr(
        "app.api.routes.health.check_redis_connection",
        fake_redis_ready,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable", "redis": "ok"},
    }


def test_health_ready_returns_503_when_redis_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_database_ready() -> bool:
        return True

    async def fake_redis_unavailable() -> bool:
        return False

    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        fake_database_ready,
    )
    monkeypatch.setattr(
        "app.api.routes.health.check_redis_connection",
        fake_redis_unavailable,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "redis": "unavailable"},
    }


def test_health_response_does_not_expose_connection_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_database_unavailable() -> bool:
        return False

    async def fake_redis_unavailable() -> bool:
        return False

    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        fake_database_unavailable,
    )
    monkeypatch.setattr(
        "app.api.routes.health.check_redis_connection",
        fake_redis_unavailable,
    )

    response = client.get("/health/ready")
    payload_text = response.text.lower()

    assert response.status_code == 503
    assert "postgresql" not in payload_text
    assert "redis://" not in payload_text
    assert "password" not in payload_text
    assert "secret" not in payload_text
    assert "token" not in payload_text
