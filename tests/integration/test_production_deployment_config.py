from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _compose_prod_config() -> dict[str, object]:
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--profile",
                "observability",
                "--env-file",
                ".env.production.example",
                "-f",
                "compose.prod.yaml",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        pytest.skip("Docker Compose is not installed.")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_production_compose_defines_runtime_observability_services() -> None:
    services = _compose_prod_config()["services"]

    assert {
        "postgres",
        "redis",
        "migration",
        "api",
        "worker",
        "reverse-proxy",
        "prometheus",
        "grafana",
    }.issubset(services)
    assert "ports" not in services["api"]
    assert "ports" not in services["worker"]
    assert "ports" not in services["postgres"]
    assert "ports" not in services["redis"]
    assert services["reverse-proxy"]["ports"]


def test_production_compose_sets_restart_healthchecks_and_resource_limits() -> None:
    services = _compose_prod_config()["services"]

    for service_name in ("api", "worker", "postgres", "redis", "reverse-proxy"):
        service = services[service_name]
        assert service["restart"] == "unless-stopped"
        assert "healthcheck" in service
        assert service["cpus"]
        assert service["mem_limit"]
        assert service["pids_limit"]
        assert service["logging"]["options"]["max-size"] == "20m"
        assert service["security_opt"] == ["no-new-privileges:true"]

    assert services["migration"]["restart"] == "no"
    assert "runtime_validation" in " ".join(services["api"]["command"])
    assert "runtime_validation" in " ".join(services["worker"]["command"])


def test_reverse_proxy_config_supports_sse_limits_and_security_headers() -> None:
    config = (ROOT / "deploy" / "nginx" / "conf.d" / "app.conf").read_text(encoding="utf-8")
    nginx = (ROOT / "deploy" / "nginx" / "nginx.conf").read_text(encoding="utf-8")

    assert "client_max_body_size 25m" in config
    assert "proxy_buffering off" in config
    assert "proxy_request_buffering off" in config
    assert "X-Forwarded-Proto" in config
    assert "X-Request-ID" in config
    assert "X-Content-Type-Options" in config
    assert "location = /metrics" in config
    assert "return 404" in config
    assert "log_format json_combined" in nginx
    assert "request_id" in nginx


def test_prometheus_and_grafana_provisioning_are_safe() -> None:
    prometheus = (ROOT / "deploy" / "prometheus" / "prometheus.yml").read_text(encoding="utf-8")
    datasource = (
        ROOT / "deploy" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
    ).read_text(encoding="utf-8")
    dashboard = (ROOT / "deploy" / "grafana" / "dashboards" / "system-overview.json").read_text(
        encoding="utf-8"
    )

    assert "api:8000" in prometheus
    assert "metrics_path: /metrics" in prometheus
    assert "http://prometheus:9090" in datasource
    assert "enterprise_ai_component_up" in dashboard
    assert "api_key" not in prometheus.lower()
    assert "password" not in prometheus.lower()
    assert "secret" not in dashboard.lower()


def test_backup_restore_scripts_are_present_and_guarded() -> None:
    script_dir = ROOT / "scripts" / "backup"
    postgres_backup = (script_dir / "postgres_backup.ps1").read_text(encoding="utf-8")
    postgres_restore = (script_dir / "postgres_restore.ps1").read_text(encoding="utf-8")
    uploads_backup = (script_dir / "uploads_backup.ps1").read_text(encoding="utf-8")
    uploads_restore = (script_dir / "uploads_restore.ps1").read_text(encoding="utf-8")

    assert "pg_dump" in postgres_backup
    assert "pg_restore --list" in postgres_backup
    assert "RetentionDays" in postgres_backup
    assert "AllowProductionOverwrite" in postgres_restore
    assert "pg_restore" in postgres_restore
    assert "tar czf" in uploads_backup
    assert "tar tzf" in uploads_backup
    assert "AllowProductionOverwrite" in uploads_restore
    for payload in (postgres_backup, postgres_restore, uploads_backup, uploads_restore):
        assert "replace-with" not in payload
        assert "POSTGRES_PASSWORD" not in payload
