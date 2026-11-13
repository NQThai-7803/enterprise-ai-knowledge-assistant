"""Summarize PROMPT 6 batches: per set and configuration, case categories, stable changes, cost.

usage: python scripts/diagnostics/summarize_ablation.py <runs file> <artifacts dir> --out <json>

<runs file> lines are "<set> <group> <run id>"; <artifacts dir>/<run id>/eval-*/ holds what
`gh run download` fetched. Every case gets one category per run:
  correct, false_refusal (should answer, got NO_ANSWER), false_answer (should refuse or is an
  RBAC negative, got an answer), wrong (answered, but not the right answer or documents), infra.
A change counts only when both baseline runs agree, both runs of the configuration agree, and
the two differ (DEC-011). Leaks: RBAC negatives with leak reasons, or the retrieval check.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

UAT, RBAC = "uat", "rbac"


def categories(kind: str, results: dict[str, Any]) -> dict[str, str]:
    cases = results.get("cases") or next(v for v in results.values() if isinstance(v, list))
    out = {}
    for case in cases:
        if case.get("execution_status") == "INFRA_ERROR":
            out[case["id"] + case.get("kind", "")] = "infra"
            continue
        answered = (case.get("grounding_status") or case.get("status")) == "ANSWERED"
        if kind == UAT:
            if case["proxy_match"]:
                category = "correct"
            elif case["reference_status"] == "ANSWERED" and not answered:
                category = "false_refusal"
            elif case["reference_status"] != "ANSWERED" and answered:
                category = "false_answer"
            else:
                category = "wrong"
        elif kind == RBAC and case["kind"] == "negative":
            category = "false_answer" if answered or case.get("leak_reasons") else "correct"
        elif kind == RBAC:
            category = (
                "correct" if case["control_passed"] else "wrong" if answered else "false_refusal"
            )
        elif case["expect"] == "refuse":
            category = "false_answer" if answered else "correct"
        elif case.get("false_answer"):  # a half-answerable question answered in full
            category = "false_answer"
        else:
            category = "correct" if case["passed"] else "wrong" if answered else "false_refusal"
        out[case["id"] + case.get("kind", "")] = category
    return out


def leaks(kind: str, run_dir: Path, results: dict[str, Any]) -> int:
    if kind != RBAC:
        return 0
    cases = next(v for v in results.values() if isinstance(v, list))
    count = sum(1 for c in cases if c.get("kind") == "negative" and c.get("leak_reasons"))
    retrieval = run_dir / "retrieval.json"
    if retrieval.is_file():
        data = json.loads(retrieval.read_text(encoding="utf-8"))
        count += sum(1 for v in data.values() if isinstance(v, dict) and v.get("leak"))
    return count


def latencies(kind: str, run_dir: Path, results: dict[str, Any]) -> list[int]:
    source = results
    if kind == UAT and (run_dir / "runtime_results.json").is_file():
        source = json.loads((run_dir / "runtime_results.json").read_text(encoding="utf-8"))
    cases = source.get("cases") or next(v for v in source.values() if isinstance(v, list))
    return [c["latency_ms"] for c in cases if isinstance(c.get("latency_ms"), int)]


def stable_changes(base: list[dict[str, str]], flag: list[dict[str, str]]) -> list[tuple]:
    changes = []
    for case_id in sorted(base[0]):
        before = {run.get(case_id) for run in base}
        after = {run.get(case_id) for run in flag}
        if len(before) == len(after) == 1 and before != after:
            changes.append((case_id, before.pop(), after.pop()))
    return changes


def unstable(runs: list[dict[str, str]]) -> list[str]:
    return sorted(i for i in runs[0] if len({run.get(i) for run in runs}) > 1)


def memory_windows(batch_dir: Path) -> dict[str, dict[str, int]]:
    """Peak used and lowest available MB of the runner while each configuration ran."""
    memory = []
    for line in (batch_dir / "memory.log").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].isdigit():
            memory.append((parts[0], int(parts[1]), int(parts[2])))
    windows: dict[str, dict[str, int]] = {}
    for line in (batch_dir / "batch.log").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 4 or not parts[3].startswith("seconds="):
            continue
        end = datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%SZ")
        start = end - timedelta(seconds=int(parts[3].split("=")[1]))
        inside = [m for m in memory if start.strftime("%T") <= m[0] <= end.strftime("%T")]
        if inside:
            window = windows.setdefault(parts[1], {"peak_used_mb": 0, "min_available_mb": 10**9})
            window["peak_used_mb"] = max(window["peak_used_mb"], max(m[1] for m in inside))
            window["min_available_mb"] = min(window["min_available_mb"], min(m[2] for m in inside))
    return windows


def summarize_batch(kind: str, batch_dir: Path) -> dict[str, Any]:
    meta = json.loads((batch_dir / "batch.json").read_text(encoding="utf-8"))
    names = [entry.split(":", 1)[0] for entry in meta["configs"].split(";") if entry]
    configs: dict[str, Any] = {}
    for name in names:
        runs, leak, lat, modes = [], 0, [], set()
        for run in (1, 2):
            run_dir = batch_dir / name / f"run{run}"
            path = run_dir / "results.json"
            if not path.is_file():
                continue
            results = json.loads(path.read_text(encoding="utf-8-sig"))
            runs.append(categories(kind, results))
            leak += leaks(kind, run_dir, results)
            lat += latencies(kind, run_dir, results)
            runtime = run_dir / "runtime_results.json"
            modes.add(
                json.loads(runtime.read_text(encoding="utf-8")).get("reranker_mode")
                if kind == UAT and runtime.is_file()
                else results.get("reranker_mode")
            )
        configs[name] = {
            "runs": len(runs),
            "counts": [dict(Counter(run.values())) for run in runs],
            "leaks": leak,
            "latency_median_ms": int(statistics.median(lat)) if lat else None,
            "reranker_mode": sorted(m for m in modes if m),
            "unstable": unstable(runs) if len(runs) == 2 else None,
            "_runs": runs,
        }
    base = configs[names[0]]["_runs"]
    for name in names[1:]:
        flag = configs[name]["_runs"]
        configs[name]["changes"] = (
            stable_changes(base, flag) if len(base) == 2 and len(flag) == 2 else None
        )
    for config in configs.values():
        del config["_runs"]
    memory = memory_windows(batch_dir) if (batch_dir / "memory.log").is_file() else {}
    for name, window in memory.items():
        if name in configs:
            configs[name]["memory"] = window
    return {
        "configs": configs,
        "ollama": meta.get("ollama_version"),
        "git_sha": meta.get("git_sha"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary: dict[str, Any] = {}
    for line in args.runs.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        set_name, group, run_id = line.split()
        batches = sorted((args.artifacts / run_id).glob("eval-*"))
        if not batches or not (batches[0] / "batch.json").is_file():
            summary[f"{set_name} {group}"] = {"missing": run_id}
            continue
        kind = UAT if set_name == UAT else RBAC if set_name == RBAC else "relevance"
        summary[f"{set_name} {group}"] = {"run": run_id, **summarize_batch(kind, batches[0])}
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(summary)} batches -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
