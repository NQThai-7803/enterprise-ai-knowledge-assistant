from __future__ import annotations

from app.observability.metrics import (
    MetricsRegistry,
    normalize_route_path,
    prometheus_labels,
    prometheus_sample,
)


def test_metrics_registry_records_bounded_http_labels() -> None:
    registry = MetricsRegistry()

    registry.record_http_request(
        method="get",
        route="/api/v1/documents/123e4567-e89b-12d3-a456-426614174000",
        status_code=200,
        latency_seconds=0.125,
    )

    snapshot = registry.http_snapshots()[0]
    assert snapshot.method == "GET"
    assert snapshot.route == "/api/v1/documents/{id}"
    assert snapshot.status_code == 200
    assert snapshot.count == 1
    assert snapshot.latency_sum_seconds == 0.125


def test_route_normalization_does_not_keep_unbounded_identifiers() -> None:
    route = normalize_route_path(
        "/api/v1/documents/abcdef0123456789abcdef0123456789/chunks/987654321"
    )

    assert route == "/api/v1/documents/{id}/chunks/{id}"
    assert "abcdef0123456789abcdef0123456789" not in route
    assert "987654321" not in route


def test_prometheus_labels_escape_values() -> None:
    labels = prometheus_labels({"route": '/safe/"quoted"', "line": "a\nb"})

    assert 'route="/safe/\\"quoted\\""' in labels
    assert 'line="a\\nb"' in labels


def test_prometheus_sample_uses_safe_metric_format() -> None:
    sample = prometheus_sample(
        "enterprise_ai_component_up",
        1,
        {"component": "postgres"},
    )

    assert sample == 'enterprise_ai_component_up{component="postgres"} 1'
