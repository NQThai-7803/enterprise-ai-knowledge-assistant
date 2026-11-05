"""Resumable runtime runner for the immutable RAG-H5 exact Q001-Q100 set."""

from __future__ import annotations

import argparse
import json
import os
import runpy
import statistics
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.eval.eval_client import (  # noqa: E402
    INFRA_ERROR,
    OK,
    EvalClient,
    EvalInfraError,
    extract,
)

BENCHMARK_SOURCE = PROJECT_ROOT / "artifacts" / "rag-h5-1-stress-uat.py"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts" / "rag-h5-2-exact-100" / "runtime_results.json"


def _load_benchmark() -> tuple[tuple[str, str], tuple[tuple[str, str, str], ...]]:
    namespace = runpy.run_path(str(BENCHMARK_SOURCE))
    return (namespace["EMAIL"], namespace["PASSWORD"]), tuple(namespace["CORE"])


def _default_client(credentials: tuple[str, str]) -> EvalClient:
    email, password = credentials
    return EvalClient(
        os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:8000"),
        email=email,
        password=password,
    )


def _write_checkpoint(
    *,
    output: Path,
    started_at: str,
    cases: list[dict[str, Any]],
    planned_cases: int,
    status: str,
) -> None:
    latencies = [int(case["latency_ms"]) for case in cases if case.get("latency_ms") is not None]
    payload = {
        "status": status,
        "started_at": started_at,
        "updated_at": datetime.now(UTC).isoformat(),
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "benchmark_source": str(BENCHMARK_SOURCE),
        "benchmark_identity": "Q001-Q100",
        "planned_cases": planned_cases,
        "completed_cases": len(cases),
        "infra_error_cases": sum(case.get("execution_status") == INFRA_ERROR for case in cases),
        "infra_error_retried_cases": sum(int(case.get("attempts", 1)) > 1 for case in cases),
        "performance": {
            "average_ms": round(statistics.mean(latencies), 2) if latencies else None,
            "p50_ms": statistics.median(latencies) if latencies else None,
            "p95_ms": (
                statistics.quantiles(latencies, n=100, method="inclusive")[94]
                if len(latencies) >= 2
                else latencies[0]
                if latencies
                else None
            ),
            "max_ms": max(latencies) if latencies else None,
        },
        "cases": cases,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ask_case(
    client: EvalClient, case_id: str, category: str, question: str, attempts: int
) -> dict[str, Any]:
    try:
        session_id = client.create_session(f"RAG-H5.2 exact {case_id}")
    except EvalInfraError:
        result: dict[str, Any] = {
            "status": INFRA_ERROR,
            "answer": "",
            "citations": [],
            "retrieved": 0,
            "http": 0,
            "latency_ms": None,
            "execution_status": INFRA_ERROR,
            "failure_class": "INFRA_SESSION",
        }
        session_id = None
    else:
        result = extract(client.ask(session_id, question))
    result.update(
        {
            "id": case_id,
            "category": category,
            "question": question,
            "session_id": session_id,
            "attempts": attempts,
        }
    )
    return result


def _is_final(case: dict[str, Any]) -> bool:
    """A checkpointed case that --resume keeps: anything but an INFRA_ERROR not yet retried."""
    return case.get("execution_status") != INFRA_ERROR or int(case.get("attempts", 1)) > 1


def run(
    *,
    selected_ids: set[str],
    output: Path,
    resume: bool,
    delay_seconds: float,
    client_factory: Callable[[tuple[str, str]], EvalClient] = _default_client,
    benchmark_loader: Callable[[], tuple[tuple[str, str], tuple[tuple[str, str, str], ...]]] = (
        _load_benchmark
    ),
) -> int:
    credentials, benchmark = benchmark_loader()
    selected = tuple(row for row in benchmark if not selected_ids or row[0] in selected_ids)
    unknown = selected_ids.difference(row[0] for row in benchmark)
    if unknown:
        raise ValueError(f"Unknown benchmark case IDs: {sorted(unknown)}")

    existing: dict[str, dict[str, Any]] = {}
    started_at = datetime.now(UTC).isoformat()
    if resume and output.exists():
        checkpoint = json.loads(output.read_text(encoding="utf-8"))
        started_at = str(checkpoint.get("started_at") or started_at)
        existing = {
            str(case["id"]): case for case in checkpoint.get("cases", []) if _is_final(case)
        }

    def checkpoint(cases: list[dict[str, Any]], status: str) -> None:
        _write_checkpoint(
            output=output,
            started_at=started_at,
            cases=cases,
            planned_cases=len(selected),
            status=status,
        )

    results: list[dict[str, Any]] = []
    # One keep-alive client for the whole run (a new connection per question exhausted the
    # Windows socket buffers in PROMPT 3g: WinError 10055).
    with client_factory(credentials) as client:
        for index, (case_id, category, question) in enumerate(selected, start=1):
            if case_id in existing:
                results.append(existing[case_id])
                print(f"[{index}/{len(selected)}] {case_id} RESUMED", flush=True)
                continue
            if results and delay_seconds > 0:
                time.sleep(delay_seconds)
            result = _ask_case(client, case_id, category, question, attempts=1)
            results.append(result)
            checkpoint(results, "IN_PROGRESS")
            print(
                f"[{index}/{len(selected)}] {case_id} {result['status']} "
                f"{result['latency_ms']}ms {result['execution_status']}",
                flush=True,
            )

        # Retry each INFRA_ERROR exactly once, at the end of the run.
        for position, case in enumerate(results):
            if case.get("execution_status") != INFRA_ERROR or int(case.get("attempts", 1)) > 1:
                continue
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            retry = _ask_case(client, case["id"], case["category"], case["question"], attempts=2)
            retry["first_attempt_failure_class"] = case.get("failure_class")
            results[position] = retry
            checkpoint(results, "IN_PROGRESS")
            print(
                f"[retry] {retry['id']} {retry['status']} "
                f"{retry['latency_ms']}ms {retry['execution_status']}",
                flush=True,
            )

    complete = len(results) == len(selected) and all(
        case.get("execution_status") == OK for case in results
    )
    final_status = "COMPLETE" if complete else "PARTIAL"
    checkpoint(results, final_status)
    return 0 if complete else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", dest="case_ids", default=[])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    args = parser.parse_args()
    return run(
        selected_ids=set(args.case_ids),
        output=args.output,
        resume=args.resume,
        delay_seconds=max(0.0, args.delay_seconds),
    )


if __name__ == "__main__":
    raise SystemExit(main())
