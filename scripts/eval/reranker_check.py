"""Refuse an eval run when the stack ranks with something other than what the run expects.

It also refuses a run when Ollama's version or backend is not the pinned one (ollama_check.py,
DEC-014), and records both in the run output, at the start and at the end.

usage: python scripts/eval/reranker_check.py --base-url <api> [--expected-reranker-mode MODE]
           [--allow-reranker-fallback]
Prints the mode reported by GET /health/ready and exits 0, or explains and exits 2.

The expected mode comes from the flag, else EVAL_EXPECTED_RERANKER_MODE, else cross_encoder, the
configured default. --allow-reranker-fallback accepts lexical_fallback and only that; the runner
records that it was used. A stack too old to report a mode is refused.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

try:
    from scripts.eval import ollama_check
except ModuleNotFoundError:  # run as `python scripts/eval/reranker_check.py`
    import ollama_check  # type: ignore[no-redef]

CROSS_ENCODER = "cross_encoder"
LEXICAL_FALLBACK = "lexical_fallback"
DISABLED = "disabled"
MODES = (CROSS_ENCODER, LEXICAL_FALLBACK, DISABLED)
ENV_EXPECTED = "EVAL_EXPECTED_RERANKER_MODE"
EXIT_MODE_CHANGED = 3


class RerankerModeRefusedError(RuntimeError):
    """The stack's reranker mode does not match what the run expects."""


def read_mode(base_url: str, timeout: float = 15.0) -> str | None:
    """Read reranker_mode from the readiness endpoint; None when it cannot be read."""
    url = f"{base_url.rstrip('/')}/health/ready"
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read()
    except HTTPError as exc:  # 503 still carries the same body
        body = exc.read()
    except (URLError, OSError):
        return None
    try:
        mode = json.loads(body).get("reranker_mode")
    except (ValueError, AttributeError):
        return None
    return mode if mode in MODES else None


def refusal(actual: str | None, expected: str, allow_fallback: bool) -> str | None:
    """Return why the run must not start, or None when it may."""
    if actual is None:
        return "the stack does not report reranker_mode; rebuild it or check that it is up"
    if actual == expected:
        return None
    if allow_fallback and actual == LEXICAL_FALLBACK:
        return None
    return (
        f"reranker_mode is {actual}, this run expects {expected}; "
        "pass --allow-reranker-fallback only to accept lexical_fallback on purpose"
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--expected-reranker-mode",
        choices=MODES,
        default=os.environ.get(ENV_EXPECTED) or CROSS_ENCODER,
    )
    parser.add_argument("--allow-reranker-fallback", action="store_true")


def guard(args: argparse.Namespace, base_url: str) -> dict[str, Any]:
    """Check the stack before a run and return the fields the run records."""
    actual = read_mode(base_url)
    reason = refusal(actual, args.expected_reranker_mode, args.allow_reranker_fallback)
    if reason:
        raise RerankerModeRefusedError(reason)
    try:
        ollama = ollama_check.guard()
    except ollama_check.OllamaMismatchError as exc:
        raise RerankerModeRefusedError(str(exc)) from exc
    return {
        "reranker_mode": actual,
        "expected_reranker_mode": args.expected_reranker_mode,
        "allow_reranker_fallback": args.allow_reranker_fallback,
        **ollama,
    }


def finish(output: Path, metadata: dict[str, Any], base_url: str, code: int) -> int:
    """Record the mode and Ollama after the run; a change during the run invalidates it."""
    end_mode = read_mode(base_url)
    end_ollama = ollama_check.read()
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["reranker_mode_end"] = end_mode
    payload["ollama_version_end"] = end_ollama["ollama_version"]
    payload["ollama_backend_end"] = end_ollama["ollama_backend"]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    changed = [
        f"{key} changed from {metadata.get(key)} to {value}"
        for key, value in (
            ("reranker_mode", end_mode),
            ("ollama_version", end_ollama["ollama_version"]),
            ("ollama_backend", end_ollama["ollama_backend"]),
        )
        if value != metadata.get(key)
    ]
    if changed:
        print("INVALID RUN: " + "; ".join(changed), file=sys.stderr)
        return code or EXIT_MODE_CHANGED
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    add_arguments(parser)
    args = parser.parse_args()
    try:
        print(guard(args, args.base_url)["reranker_mode"])
    except RerankerModeRefusedError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
