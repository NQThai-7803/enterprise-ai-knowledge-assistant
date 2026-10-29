"""Resumable runtime runner for the immutable RAG-H5 exact Q001-Q100 set."""

from __future__ import annotations

import argparse
import json
import os
import runpy
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_SOURCE = PROJECT_ROOT / "artifacts" / "rag-h5-1-stress-uat.py"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts" / "rag-h5-2-exact-100" / "runtime_results.json"


def _load_benchmark() -> tuple[type[Any], Any, tuple[tuple[str, str, str], ...]]:
    namespace = runpy.run_path(str(BENCHMARK_SOURCE))
    namespace["Client"].req.__globals__["BASE"] = os.environ.get(
        "RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:8000"
    )
    return namespace["Client"], namespace["extract"], tuple(namespace["CORE"])


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
        "infra_error_cases": sum(case.get("execution_status") == "INFRA_ERROR" for case in cases),
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


def run(
    *,
    selected_ids: set[str],
    output: Path,
    resume: bool,
    delay_seconds: float,
    max_rate_limit_retries: int,
) -> int:
    client_type, extract, benchmark = _load_benchmark()
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
            str(case["id"]): case
            for case in checkpoint.get("cases", [])
            if case.get("execution_status") == "OK"
        }

    client = client_type()
    client.login()
    results: list[dict[str, Any]] = []
    for index, (case_id, category, question) in enumerate(selected, start=1):
        if case_id in existing:
            results.append(existing[case_id])
            print(f"[{index}/{len(selected)}] {case_id} RESUMED", flush=True)
            continue
        if results and delay_seconds > 0:
            time.sleep(delay_seconds)

        session_id = client.session(f"RAG-H5.2 exact {case_id}")
        response: dict[str, Any] | None = None
        for attempt in range(max_rate_limit_retries + 1):
            response = client.ask(session_id, question)
            if response.get("http_status") != 429:
                break
            if attempt < max_rate_limit_retries:
                time.sleep(max(delay_seconds, min(2**attempt, 8)))
        assert response is not None
        result = extract(response)
        result.update(
            {
                "id": case_id,
                "category": category,
                "question": question,
                "session_id": session_id,
                "execution_status": ("INFRA_ERROR" if response.get("http_status") == 429 else "OK"),
                "failure_class": (
                    "INFRA_RATE_LIMIT" if response.get("http_status") == 429 else None
                ),
            }
        )
        results.append(result)
        _write_checkpoint(
            output=output,
            started_at=started_at,
            cases=results,
            planned_cases=len(selected),
            status="IN_PROGRESS",
        )
        print(
            f"[{index}/{len(selected)}] {case_id} {result['status']} "
            f"{result['latency_ms']}ms {result['execution_status']}",
            flush=True,
        )

    final_status = (
        "COMPLETE"
        if len(results) == len(selected)
        and all(case.get("execution_status") == "OK" for case in results)
        else "PARTIAL"
    )
    _write_checkpoint(
        output=output,
        started_at=started_at,
        cases=results,
        planned_cases=len(selected),
        status=final_status,
    )
    return 0 if final_status == "COMPLETE" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", dest="case_ids", default=[])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    parser.add_argument("--max-rate-limit-retries", type=int, default=3)
    args = parser.parse_args()
    return run(
        selected_ids=set(args.case_ids),
        output=args.output,
        resume=args.resume,
        delay_seconds=max(0.0, args.delay_seconds),
        max_rate_limit_retries=max(0, args.max_rate_limit_retries),
    )


if __name__ == "__main__":
    raise SystemExit(main())
