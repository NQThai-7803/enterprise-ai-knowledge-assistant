from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import Settings, get_settings


def validate_runtime(settings: Settings) -> list[str]:
    failures: list[str] = []
    if settings.app_env == "production" and settings.api_docs_enabled:
        failures.append("API_DOCS_ENABLED must be false in production runtime.")
    _validate_runtime_path(
        settings.local_storage_path,
        label="LOCAL_STORAGE_PATH",
        failures=failures,
    )
    _validate_runtime_path(
        settings.embedding_model_cache_path,
        label="EMBEDDING_MODEL_CACHE_PATH",
        failures=failures,
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate production runtime configuration.")
    parser.add_argument(
        "--print-ok",
        action="store_true",
        help="Print a generic success message without exposing configuration.",
    )
    args = parser.parse_args()

    settings = get_settings()
    failures = validate_runtime(settings)
    if failures:
        for failure in failures:
            print(f"runtime validation failed: {failure}")
        return 1
    if args.print_ok:
        print("runtime validation ok")
    return 0


def _validate_runtime_path(path_value: str, *, label: str, failures: list[str]) -> None:
    path = Path(path_value)
    if not path.exists():
        failures.append(f"{label} does not exist.")
        return
    if not path.is_dir():
        failures.append(f"{label} must be a directory.")
        return
    probe = path / ".runtime-write-check"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        failures.append(f"{label} is not writable.")


if __name__ == "__main__":
    raise SystemExit(main())
