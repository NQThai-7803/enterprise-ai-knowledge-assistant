"""Refuse an eval run when Ollama is not the version and backend the measurements expect (DEC-014).

usage: python scripts/eval/ollama_check.py
Prints the recorded fields as JSON and exits 0, or explains and exits 2.

The version comes from GET <EVAL_OLLAMA>/api/version. The backend (CUDA, VULKAN, CPU, ...) is read
from the server log: the `inference compute` lines written after the last `Listening on` line.
The log is EVAL_OLLAMA_LOG, else %LOCALAPPDATA%\\Ollama\\server.log (the Windows app). Expected
values: EVAL_OLLAMA_EXPECTED_VERSION and EVAL_OLLAMA_EXPECTED_BACKEND, else the pinned local ones
below. The Windows app's auto-update setting is recorded too, not enforced.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

# Pinned 2026-11-08 (DEC-014): the local GTX 1650 runs on CUDA since 2026-11-06 18:26.
EXPECTED_VERSION = "0.40.15"
EXPECTED_BACKEND = "CUDA"
_LISTENING = "Listening on"
_LIBRARY = re.compile(r'msg="inference compute".*?\blibrary=(\S+)')


class OllamaMismatchError(RuntimeError):
    """Ollama's version or backend differs from what the run expects."""


def _base_url() -> str:
    return os.environ.get("EVAL_OLLAMA", "http://127.0.0.1:11434").rstrip("/")


def _app_dir() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "Ollama" if local else None


def log_path() -> Path | None:
    if os.environ.get("EVAL_OLLAMA_LOG"):
        return Path(os.environ["EVAL_OLLAMA_LOG"])
    app = _app_dir()
    return app / "server.log" if app else None


def read_version(timeout: float = 10.0) -> str | None:
    try:
        with urlopen(f"{_base_url()}/api/version", timeout=timeout) as response:
            return json.loads(response.read()).get("version")
    except (URLError, OSError, ValueError, AttributeError):
        return None


def backend_from_log(text: str) -> str | None:
    """The backend libraries the current server found, upper-cased and joined; None if unknown."""
    current = text[text.rfind(_LISTENING) :] if _LISTENING in text else text
    found = sorted({m.group(1).strip('"').upper() for m in _LIBRARY.finditer(current)})
    return "+".join(found) or None


def read_backend() -> str | None:
    path = log_path()
    if path is None or not path.is_file():
        return None
    return backend_from_log(path.read_text(encoding="utf-8", errors="replace"))


def read_auto_update() -> bool | None:
    app = _app_dir()
    db = app / "db.sqlite" if app else None
    if db is None or not db.is_file():
        return None
    try:
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5) as conn:
            row = conn.execute("SELECT auto_update_enabled FROM settings WHERE id = 1").fetchone()
    except sqlite3.Error:
        return None
    return bool(row[0]) if row else None


def expected() -> tuple[str, str]:
    return (
        os.environ.get("EVAL_OLLAMA_EXPECTED_VERSION") or EXPECTED_VERSION,
        (os.environ.get("EVAL_OLLAMA_EXPECTED_BACKEND") or EXPECTED_BACKEND).upper(),
    )


def refusal(version: str | None, backend: str | None, want: tuple[str, str]) -> str | None:
    want_version, want_backend = want
    if version != want_version:
        return f"Ollama version is {version}, this run expects {want_version}"
    if backend is None:
        return (
            f"Ollama backend is unknown (no `inference compute` line in {log_path()} since the "
            "server started); wait for GPU discovery or set EVAL_OLLAMA_LOG"
        )
    if backend != want_backend:
        return f"Ollama backend is {backend}, this run expects {want_backend}"
    return None


def read() -> dict[str, Any]:
    want_version, want_backend = expected()
    return {
        "ollama_version": read_version(),
        "ollama_backend": read_backend(),
        "ollama_expected_version": want_version,
        "ollama_expected_backend": want_backend,
        "ollama_auto_update": read_auto_update(),
    }


def guard() -> dict[str, Any]:
    """Return the fields the run records, or raise when Ollama differs from what it expects."""
    fields = read()
    reason = refusal(
        fields["ollama_version"],
        fields["ollama_backend"],
        (fields["ollama_expected_version"], fields["ollama_expected_backend"]),
    )
    if reason:
        raise OllamaMismatchError(reason)
    return fields


def main() -> int:
    try:
        print(json.dumps(guard()))
    except OllamaMismatchError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
