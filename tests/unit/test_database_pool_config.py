from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_pool_defaults_are_bounded() -> None:
    settings = Settings(_env_file=None)

    assert settings.db_pool_size == 10
    assert settings.db_max_overflow == 20
    assert settings.db_pool_timeout_seconds == 30
    assert settings.db_pool_recycle_seconds == 1800
    assert settings.db_connect_timeout_seconds == 10


def test_database_pool_rejects_invalid_bounds() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, db_pool_size=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, db_connect_timeout_seconds=True)
