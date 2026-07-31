from __future__ import annotations

import pytest

from app.api.routes.health import check_redis_connection
from app.core.config import Settings


def test_redis_timeout_defaults_are_bounded() -> None:
    settings = Settings(_env_file=None)

    assert settings.redis_connect_timeout_seconds == 5
    assert settings.redis_socket_timeout_seconds == 5
    assert settings.redis_health_check_interval_seconds == 30


def test_redis_timeout_settings_reject_invalid_values() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, redis_connect_timeout_seconds=0)
    with pytest.raises(ValueError):
        Settings(_env_file=None, redis_socket_timeout_seconds=True)


@pytest.mark.anyio
async def test_readiness_uses_configured_redis_timeouts(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    class FakeRedis:
        @classmethod
        def from_url(cls, url: str, **kwargs: object) -> FakeRedis:
            captured["url"] = url
            captured.update(kwargs)
            return cls()

        async def ping(self) -> bool:
            return True

        async def aclose(self) -> None:
            return None

    settings = Settings(
        _env_file=None,
        redis_url="redis://redis.example.internal:6379/0",
        redis_connect_timeout_seconds=7,
        redis_socket_timeout_seconds=8,
        redis_health_check_interval_seconds=9,
    )
    monkeypatch.setattr("app.api.routes.health.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.health.Redis", FakeRedis)

    assert await check_redis_connection() is True
    assert captured == {
        "url": "redis://redis.example.internal:6379/0",
        "socket_connect_timeout": 7,
        "socket_timeout": 8,
        "health_check_interval": 9,
    }
