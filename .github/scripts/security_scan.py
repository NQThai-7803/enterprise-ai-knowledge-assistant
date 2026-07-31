from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_TARGETS = (
    REPO_ROOT / "app",
    REPO_ROOT / "Dockerfile",
    REPO_ROOT / "compose.yaml",
    REPO_ROOT / "pyproject.toml",
    REPO_ROOT / "alembic.ini",
)
TEXT_SUFFIXES = {".py", ".toml", ".yaml", ".yml", ".ini", ""}
ALLOWED_SECRET_VALUES = {
    "",
    "change-me",
    "change-me-for-local-development",
    "replace-with-a-long-random-secret-key",
}

FINDINGS: list[str] = []


def iter_scan_files() -> list[Path]:
    files: list[Path] = []
    for target in SCAN_TARGETS:
        if not target.exists():
            continue
        if target.is_file():
            files.append(target)
            continue
        for path in target.rglob("*"):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                files.append(path)
    return sorted(files)


def add(path: Path, line_number: int, rule: str, detail: str) -> None:
    rel = path.relative_to(REPO_ROOT).as_posix()
    FINDINGS.append(f"{rel}:{line_number}: {rule}: {detail}")


def scan_text_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        if re.search(r"\bcreate_all\s*\(", line):
            add(path, line_number, "create_all", "schema creation outside Alembic is forbidden")

        if re.search(r"\bpickle\b", line, flags=re.IGNORECASE):
            add(path, line_number, "pickle", "pickle serialization is forbidden")

        if re.search(r"\b(?:execute|text)\s*\(\s*f[\"']", line):
            add(path, line_number, "raw-sql-interpolation", "f-string SQL execution is forbidden")
        if re.search(r"\.execute\s*\([^\n]*(?:\.format\(|%\s*)", line):
            add(path, line_number, "raw-sql-interpolation", "formatted SQL execution is forbidden")

        secret_match = re.search(
            r"(?i)\b(secret_key|api_key|token|password)\b\s*[:=]\s*[\"']([^\"']*)[\"']",
            line,
        )
        if secret_match:
            value = secret_match.group(2)
            if (
                value
                and value not in ALLOWED_SECRET_VALUES
                and not value.startswith(("ci-", "test-"))
            ):
                add(path, line_number, "hardcoded-secret", "hardcoded secret-like value detected")

        if re.search(
            r"\b(?:logger|logging)\.(?:debug|info|warning|error|exception)\s*\([^\n]*(?:password|token|secret|api_key|question|answer|context|excerpt|storage_key)",
            line,
            flags=re.IGNORECASE,
        ):
            add(path, line_number, "unsafe-logging", "sensitive field name in log call")


def verify_production_debug_rejected() -> None:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "production",
            "APP_DEBUG": "true",
            "SECRET_KEY": "ci-production-secret-key-000000000000000000000000",
            "DATABASE_URL": "postgresql+asyncpg://app_user:password@postgres:5432/enterprise_ai",
            "CELERY_BROKER_URL": "redis://redis:6379/1",
            "CELERY_RESULT_BACKEND": "redis://redis:6379/2",
            "LLM_ENABLED": "false",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "from app.core.config import Settings; Settings()"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 or "APP_DEBUG must be false in production" not in (
        result.stderr + result.stdout
    ):
        FINDINGS.append("production-debug: APP_DEBUG=true was not rejected for production")


def verify_celery_json_serialization() -> None:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "APP_DEBUG": "false",
            "SECRET_KEY": "ci-test-secret-key-000000000000000000000000",
            "DATABASE_URL": "postgresql+asyncpg://app_user:password@postgres:5432/enterprise_ai",
            "CELERY_BROKER_URL": "redis://redis:6379/1",
            "CELERY_RESULT_BACKEND": "redis://redis:6379/2",
            "LLM_ENABLED": "false",
        }
    )
    code = """
from app.workers.celery_app import celery_app
conf = celery_app.conf
assert conf.task_serializer == 'json'
assert conf.result_serializer == 'json'
assert list(conf.accept_content) == ['json']
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        FINDINGS.append("celery-serialization: Celery must accept JSON only")


def main() -> int:
    for path in iter_scan_files():
        scan_text_file(path)
    verify_production_debug_rejected()
    verify_celery_json_serialization()

    if FINDINGS:
        print("Security scan failed:")
        for finding in FINDINGS:
            print(f"- {finding}")
        return 1

    print("Security scan passed.")
    print(
        "Checked: create_all, pickle serializer, raw SQL interpolation, "
        "hardcoded secrets, production debug rejection, unsafe logging, "
        "Celery JSON-only serialization."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
