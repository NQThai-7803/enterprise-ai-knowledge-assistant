from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import BusinessValidationError
from app.services.admin_analytics_service import (
    analytics_payload_to_csv,
    resolve_analytics_window,
)


def test_resolve_today_window_uses_utc_midnight() -> None:
    now = datetime(2026, 8, 4, 13, 45, tzinfo=UTC)

    window = resolve_analytics_window(period="today", now=now)

    assert window.date_from == datetime(2026, 8, 4, tzinfo=UTC)
    assert window.date_to == now
    assert window.period == "today"


def test_resolve_rolling_window_supports_7_30_90_days() -> None:
    now = datetime(2026, 8, 4, 13, 45, tzinfo=UTC)

    assert resolve_analytics_window(period="7d", now=now).date_from == now - timedelta(days=7)
    assert resolve_analytics_window(period="30d", now=now).date_from == now - timedelta(days=30)
    assert resolve_analytics_window(period="90d", now=now).date_from == now - timedelta(days=90)


def test_custom_window_requires_timezone_aware_bounds() -> None:
    with pytest.raises(BusinessValidationError):
        resolve_analytics_window(
            period="custom",
            date_from=datetime(2026, 8, 1),
            date_to=datetime(2026, 8, 2, tzinfo=UTC),
        )


def test_non_custom_window_rejects_custom_bounds() -> None:
    with pytest.raises(BusinessValidationError):
        resolve_analytics_window(
            period="30d",
            date_from=datetime(2026, 8, 1, tzinfo=UTC),
        )


def test_csv_export_flattens_safe_payload_without_raw_query() -> None:
    payload = {
        "report": "search",
        "data": {
            "top_queries": [
                {
                    "query_hash": "a1b2c3d4e5f6a7b8",
                    "count": 2,
                    "raw_query_available": False,
                }
            ],
            "note": "aggregate only",
        },
    }

    csv_text = analytics_payload_to_csv(payload)

    assert "data.top_queries" in csv_text
    assert "a1b2c3d4e5f6a7b8" in csv_text
    assert "What is the secret payroll plan?" not in csv_text
