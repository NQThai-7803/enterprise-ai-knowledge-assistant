from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.observability.metrics import GLOBAL_METRICS, MetricsRegistry, prometheus_sample
from app.services.admin_monitoring_service import AdminMonitoringService

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class PrometheusMetricsService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        application: Any | None = None,
        registry: MetricsRegistry = GLOBAL_METRICS,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.application = application
        self.registry = registry
        self.settings = settings or _settings_from_application(application) or get_settings()

    async def render(self) -> str:
        lines = [
            "# HELP enterprise_ai_http_requests_total "
            "Total HTTP requests by method, route, and status.",
            "# TYPE enterprise_ai_http_requests_total counter",
        ]
        self._append_http_metrics(lines)
        self._append_observability_metrics(lines)
        if self.settings.metrics_include_subsystem_health:
            await self._append_runtime_metrics(lines)
        return "\n".join(lines) + "\n"

    def _append_http_metrics(self, lines: list[str]) -> None:
        snapshots = self.registry.http_snapshots()
        for snapshot in snapshots:
            labels = {
                "method": snapshot.method,
                "route": snapshot.route,
                "status": snapshot.status_code,
            }
            lines.append(
                prometheus_sample(
                    "enterprise_ai_http_requests_total",
                    snapshot.count,
                    labels,
                )
            )
        lines.extend(
            [
                "# HELP enterprise_ai_http_request_latency_seconds_sum Total HTTP request latency.",
                "# TYPE enterprise_ai_http_request_latency_seconds_sum counter",
            ]
        )
        for snapshot in snapshots:
            labels = {
                "method": snapshot.method,
                "route": snapshot.route,
                "status": snapshot.status_code,
            }
            lines.append(
                prometheus_sample(
                    "enterprise_ai_http_request_latency_seconds_sum",
                    snapshot.latency_sum_seconds,
                    labels,
                )
            )
        lines.extend(
            [
                "# HELP enterprise_ai_http_request_latency_seconds_count "
                "Count of HTTP latency samples.",
                "# TYPE enterprise_ai_http_request_latency_seconds_count counter",
            ]
        )
        for snapshot in snapshots:
            labels = {
                "method": snapshot.method,
                "route": snapshot.route,
                "status": snapshot.status_code,
            }
            lines.append(
                prometheus_sample(
                    "enterprise_ai_http_request_latency_seconds_count",
                    snapshot.count,
                    labels,
                )
            )
        lines.extend(
            [
                "# HELP enterprise_ai_http_request_latency_seconds_max "
                "Maximum observed HTTP request latency.",
                "# TYPE enterprise_ai_http_request_latency_seconds_max gauge",
            ]
        )
        for snapshot in snapshots:
            labels = {
                "method": snapshot.method,
                "route": snapshot.route,
                "status": snapshot.status_code,
            }
            lines.append(
                prometheus_sample(
                    "enterprise_ai_http_request_latency_seconds_max",
                    snapshot.latency_max_seconds,
                    labels,
                )
            )

    def _append_observability_metrics(self, lines: list[str]) -> None:
        lines.extend(
            [
                "# HELP enterprise_ai_observability_enabled Observability middleware enabled flag.",
                "# TYPE enterprise_ai_observability_enabled gauge",
                prometheus_sample(
                    "enterprise_ai_observability_enabled",
                    int(self.settings.observability_enabled),
                ),
                "# HELP enterprise_ai_tracing_hooks_enabled Trace propagation hook enabled flag.",
                "# TYPE enterprise_ai_tracing_hooks_enabled gauge",
                prometheus_sample(
                    "enterprise_ai_tracing_hooks_enabled",
                    int(self.settings.tracing_hooks_enabled),
                ),
            ]
        )

    async def _append_runtime_metrics(self, lines: list[str]) -> None:
        monitor = AdminMonitoringService(session=self.session, application=self.application)
        try:
            version = await monitor.get_version()
            health = await monitor.get_health()
            providers = monitor.get_providers()
            workers = await monitor.get_workers()
            queues = await monitor.get_queues()
        except Exception:
            lines.extend(
                [
                    "# HELP enterprise_ai_metrics_scrape_error Runtime metrics scrape error flag.",
                    "# TYPE enterprise_ai_metrics_scrape_error gauge",
                    prometheus_sample("enterprise_ai_metrics_scrape_error", 1),
                ]
            )
            return

        lines.extend(
            [
                "# HELP enterprise_ai_metrics_scrape_error Runtime metrics scrape error flag.",
                "# TYPE enterprise_ai_metrics_scrape_error gauge",
                prometheus_sample("enterprise_ai_metrics_scrape_error", 0),
                "# HELP enterprise_ai_app_info Application version and migration info.",
                "# TYPE enterprise_ai_app_info gauge",
                prometheus_sample(
                    "enterprise_ai_app_info",
                    1,
                    {
                        "version": version.version,
                        "environment": version.environment,
                        "migration_head": version.migration_head or "unknown",
                        "database_revision": version.database_revision or "unknown",
                    },
                ),
                "# HELP enterprise_ai_app_uptime_seconds Application process uptime in seconds.",
                "# TYPE enterprise_ai_app_uptime_seconds gauge",
                prometheus_sample("enterprise_ai_app_uptime_seconds", version.uptime_seconds),
                "# HELP enterprise_ai_component_up Component health as 1 for ok, otherwise 0.",
                "# TYPE enterprise_ai_component_up gauge",
            ]
        )
        for check in health.checks:
            lines.append(
                prometheus_sample(
                    "enterprise_ai_component_up",
                    1 if check.status == "ok" else 0,
                    {"component": check.name},
                )
            )
        lines.extend(
            [
                "# HELP enterprise_ai_component_status_info Component status label.",
                "# TYPE enterprise_ai_component_status_info gauge",
            ]
        )
        for check in health.checks:
            lines.append(
                prometheus_sample(
                    "enterprise_ai_component_status_info",
                    1,
                    {
                        "component": check.name,
                        "status": check.status,
                        "enabled": _bool_or_unknown(check.enabled),
                    },
                )
            )

        self._append_provider_metrics(lines, providers.llm)
        self._append_provider_metrics(lines, providers.web_search)

        worker_active_count = max(
            workers.active_worker_count,
            _worker_active_count_from_health(health.checks),
        )
        lines.extend(
            [
                "# HELP enterprise_ai_worker_active_count Active Celery worker count.",
                "# TYPE enterprise_ai_worker_active_count gauge",
                prometheus_sample(
                    "enterprise_ai_worker_active_count",
                    worker_active_count,
                ),
                "# HELP enterprise_ai_worker_up Individual Celery worker status.",
                "# TYPE enterprise_ai_worker_up gauge",
            ]
        )
        for worker in workers.workers:
            lines.append(
                prometheus_sample(
                    "enterprise_ai_worker_up",
                    1 if worker.status == "ok" else 0,
                    {"worker": worker.name},
                )
            )
        lines.extend(
            [
                "# HELP enterprise_ai_worker_registered_tasks Registered Celery task count.",
                "# TYPE enterprise_ai_worker_registered_tasks gauge",
                prometheus_sample(
                    "enterprise_ai_worker_registered_tasks",
                    len(workers.registered_tasks),
                ),
                "# HELP enterprise_ai_queue_pending Pending queue length when available.",
                "# TYPE enterprise_ai_queue_pending gauge",
            ]
        )
        for queue in queues.queues:
            if queue.pending is not None:
                lines.append(
                    prometheus_sample(
                        "enterprise_ai_queue_pending",
                        queue.pending,
                        {"kind": queue.kind, "queue": queue.name},
                    )
                )
        lines.extend(
            [
                "# HELP enterprise_ai_queue_configured Queue configured flag.",
                "# TYPE enterprise_ai_queue_configured gauge",
            ]
        )
        for queue in queues.queues:
            lines.append(
                prometheus_sample(
                    "enterprise_ai_queue_configured",
                    int(queue.configured),
                    {"kind": queue.kind, "queue": queue.name},
                )
            )
        lines.extend(
            [
                "# HELP enterprise_ai_queue_status_info Queue status label.",
                "# TYPE enterprise_ai_queue_status_info gauge",
            ]
        )
        for queue in queues.queues:
            lines.append(
                prometheus_sample(
                    "enterprise_ai_queue_status_info",
                    1,
                    {"kind": queue.kind, "queue": queue.name, "status": queue.status},
                )
            )

    def _append_provider_metrics(self, lines: list[str], provider: Any) -> None:
        base_labels = {
            "provider_type": provider.provider_type,
            "provider": provider.provider,
        }
        lines.extend(
            [
                prometheus_sample(
                    "enterprise_ai_provider_enabled",
                    int(provider.enabled),
                    base_labels,
                ),
                prometheus_sample(
                    "enterprise_ai_provider_configured",
                    int(provider.configured),
                    base_labels,
                ),
                prometheus_sample(
                    "enterprise_ai_provider_healthy",
                    1 if provider.status == "healthy" else 0,
                    base_labels,
                ),
                prometheus_sample(
                    "enterprise_ai_provider_status_info",
                    1,
                    {**base_labels, "status": provider.status},
                ),
            ]
        )


def _settings_from_application(application: Any | None) -> Settings | None:
    settings = getattr(getattr(application, "state", None), "settings", None)
    return settings if isinstance(settings, Settings) else None


def _bool_or_unknown(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "true" if value else "false"


def _worker_active_count_from_health(checks: list[Any]) -> int:
    for check in checks:
        if getattr(check, "name", None) != "worker":
            continue
        details = getattr(check, "details", {})
        value = details.get("active_worker_count") if isinstance(details, dict) else None
        if isinstance(value, int) and value >= 0:
            return value
    return 0
