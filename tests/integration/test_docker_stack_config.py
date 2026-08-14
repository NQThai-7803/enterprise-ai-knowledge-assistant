from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _compose_config() -> dict[str, object]:
    try:
        result = subprocess.run(
            ["docker", "compose", "config", "--format", "json"],
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


def test_dockerfile_uses_python_312_non_root_runtime() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim AS builder" in dockerfile
    assert "FROM python:3.12-slim AS runtime" in dockerfile
    assert "USER app" in dockerfile
    assert "useradd --system --uid 10001" in dockerfile
    assert "COPY ." not in dockerfile
    assert ".env" not in dockerfile
    assert "create_all" not in dockerfile


def test_dockerignore_excludes_secrets_and_host_artifacts() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    ignored = {line.strip() for line in dockerignore if line.strip() and not line.startswith("#")}

    assert ".env" in ignored
    assert ".env.*" in ignored
    assert "!.env.example" in ignored
    assert ".git" in ignored
    assert ".venv" in ignored
    assert "data/uploads/*" in ignored
    assert "data/models/*" in ignored
    assert "app/db/migrations/" not in ignored
    assert "alembic.ini" not in ignored
    assert "pyproject.toml" not in ignored


def test_compose_contains_required_backend_services() -> None:
    services = _compose_config()["services"]

    assert {"postgres", "redis", "migration", "api", "worker"}.issubset(services)


def test_api_worker_and_migration_use_same_application_image() -> None:
    services = _compose_config()["services"]

    assert services["api"]["image"] == services["worker"]["image"]
    assert services["api"]["image"] == services["migration"]["image"]
    assert services["api"]["build"]["target"] == "runtime"
    assert services["worker"]["build"]["target"] == "runtime"
    assert services["migration"]["build"]["target"] == "runtime"


def test_migration_service_runs_alembic_upgrade_head_before_api_and_worker() -> None:
    services = _compose_config()["services"]

    assert services["migration"]["command"] == ["alembic", "upgrade", "head"]
    assert services["migration"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert services["api"]["depends_on"]["migration"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["worker"]["depends_on"]["migration"]["condition"] == (
        "service_completed_successfully"
    )


def test_containers_use_service_discovery_for_database_and_redis() -> None:
    services = _compose_config()["services"]

    for service_name in ("api", "worker", "migration"):
        environment = services[service_name]["environment"]
        assert "@postgres:5432/" in environment["DATABASE_URL"]
        assert environment["CELERY_BROKER_URL"] == "redis://redis:6379/1"
        assert environment["CELERY_RESULT_BACKEND"] == "redis://redis:6379/2"
        assert environment["REDIS_URL"] == "redis://redis:6379/0"


def test_shared_upload_and_model_cache_volumes_are_mounted_to_api_and_worker() -> None:
    services = _compose_config()["services"]

    for service_name in ("api", "worker"):
        volumes = services[service_name]["volumes"]
        volume_targets = {volume["target"]: volume["source"] for volume in volumes}
        assert volume_targets["/app/data/uploads"] == "uploads_data"
        assert volume_targets["/app/data/models"] == "model_cache"


def test_api_and_worker_security_relevant_compose_contracts() -> None:
    services = _compose_config()["services"]

    assert "8000:8000" not in json.dumps(services["worker"].get("ports", []))
    assert "ports" not in services["worker"]
    assert "docker.sock" not in json.dumps(services)
    assert "network_mode" not in services["api"]
    assert "network_mode" not in services["worker"]
    assert "--reload" not in services["api"]["command"]
    assert "alembic" not in services["api"]["command"]


def test_application_services_use_no_new_privileges() -> None:
    services = _compose_config()["services"]

    for service_name in ("migration", "api", "worker"):
        assert services[service_name]["security_opt"] == ["no-new-privileges:true"]


def _compose_uat_config() -> dict[str, object]:
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "compose.yaml",
                "-f",
                "compose.uat.yaml",
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


def test_default_compose_keeps_llm_local_safe() -> None:
    services = _compose_config()["services"]
    environment = services["api"]["environment"]

    assert "uat-llm" not in services
    assert (
        environment["LLM_PROVIDER"] != "openai_compatible"
        or environment.get("LLM_MODEL") != "uat-deterministic-model"
    )
    if environment["LLM_ENABLED"] == "true":
        assert environment["LLM_PROVIDER"] == "ollama"
        assert environment["LLM_OLLAMA_MODEL"] == "qwen2.5:3b"
        assert environment["LLM_OLLAMA_NUM_CTX"] == "4096"
        assert environment["LLM_OLLAMA_KEEP_ALIVE"] == "10m"
        assert environment["LLM_TEMPERATURE"] == "0"
        assert environment["LLM_MAX_OUTPUT_TOKENS"] == "512"
    else:
        assert environment["LLM_ENABLED"] == "false"
        assert not environment.get("LLM_MODEL")
        assert not environment.get("LLM_OPENAI_BASE_URL")


def test_uat_compose_enables_local_deterministic_llm_provider() -> None:
    services = _compose_uat_config()["services"]
    environment = services["api"]["environment"]

    assert "uat-llm" in services
    assert environment["LLM_ENABLED"] == "true"
    assert environment["LLM_PROVIDER"] == "openai_compatible"
    assert environment["LLM_MODEL"] == "uat-deterministic-model"
    assert environment["LLM_OPENAI_BASE_URL"] == "http://uat-llm:18080/v1"
    assert services["api"]["depends_on"]["uat-llm"]["condition"] == "service_started"
    assert services["uat-llm"]["command"] == [
        "node",
        "frontend/tests/e2e-live/fake-openai-provider.mjs",
    ]


def test_uat_compose_runs_idempotent_seed_before_api_and_worker() -> None:
    services = _compose_uat_config()["services"]
    seed = services["uat-seed"]
    seed_environment = seed["environment"]

    assert seed["image"] == services["api"]["image"]
    assert seed["build"]["target"] == "runtime"
    assert seed["command"] == ["python", "-m", "app.scripts.seed_uat_data"]
    assert seed["depends_on"]["migration"]["condition"] == "service_completed_successfully"
    assert seed["security_opt"] == ["no-new-privileges:true"]
    assert seed_environment["UAT_SEED_ENABLED"] == "true"
    assert seed_environment["UAT_ADMIN_PASSWORD"] == "LocalUatAdmin!2026"
    assert seed_environment["UAT_MANAGER_PASSWORD"] == "LocalUatManager!2026"
    assert seed_environment["UAT_STAFF_PASSWORD"] == "LocalUatStaff!2026"
    assert seed_environment["LLM_ENABLED"] == "false"
    assert seed_environment["DATABASE_URL"].endswith("@postgres:5432/enterprise_ai")
    seed_volumes = {volume["target"]: volume["source"] for volume in seed["volumes"]}
    assert seed_volumes["/app/data/uploads"] == "uploads_data"
    assert seed_volumes["/app/data/models"] == "model_cache"
    assert services["api"]["depends_on"]["uat-seed"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["worker"]["depends_on"]["uat-seed"]["condition"] == (
        "service_completed_successfully"
    )


def test_uat_fake_provider_is_local_only_and_covers_acceptance_questions() -> None:
    provider = (ROOT / "frontend/tests/e2e-live/fake-openai-provider.mjs").read_text(
        encoding="utf-8"
    )

    assert "createServer" in provider
    assert "0.0.0.0" in provider
    assert "/v1/chat/completions" in provider
    assert "api.openai.com" not in provider
    assert "generativelanguage.googleapis.com" not in provider
    assert "anthropic.com" not in provider
    assert "CEO Nova Digital" in provider
    assert "05 n" in provider
