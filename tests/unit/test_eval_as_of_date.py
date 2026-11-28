"""EVAL_AS_OF_DATE: the date document versions are ranked by on an eval stack (no database)."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.retrieval import authority

PRODUCTION = {
    "_env_file": None,  # not the developer's .env
    "app_env": "production",
    "app_debug": False,
    "debug": False,
    "secret_key": "s" * 40,
    "database_url": "postgresql+asyncpg://app:real-password@db:5432/app",
    "redis_url": "redis://redis:6379/0",
    "celery_broker_url": "redis://redis:6379/1",
    "celery_result_backend": "redis://redis:6379/2",
}


def _sql(monkeypatch: pytest.MonkeyPatch, **settings: object) -> str:
    monkeypatch.setattr(authority, "get_settings", lambda: Settings(**settings))
    expression = authority.current_authority_order_expression()
    return str(
        expression.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def test_unset_ranks_by_the_database_date(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings.model_fields["eval_as_of_date"].default is None
    sql = _sql(monkeypatch)
    assert sql.count("CURRENT_DATE") == 2  # effective_from and effective_to


def test_set_ranks_by_that_date_instead(monkeypatch: pytest.MonkeyPatch) -> None:
    sql = _sql(monkeypatch, eval_as_of_date="2026-12-15")
    assert "CURRENT_DATE" not in sql
    assert "documents.effective_from <= '2026-12-15'" in sql
    assert "documents.effective_to >= '2026-12-15'" in sql


def test_blank_means_unset_and_production_refuses_it() -> None:
    assert Settings(eval_as_of_date=" ").eval_as_of_date is None
    assert Settings(eval_as_of_date="2026-12-15").eval_as_of_date == date(2026, 12, 15)
    Settings(**PRODUCTION)  # the base production settings are valid
    with pytest.raises(ValidationError, match="EVAL_AS_OF_DATE"):
        Settings(**PRODUCTION, eval_as_of_date="2026-12-15")
