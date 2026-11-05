"""Latency by question position for eval runs, and whether run-to-run answer changes track it.

usage: latency_by_position.py <out_dir> <name>=<run_dir> [<name>=<run_dir> ...]
       [--pair a,b ...] [--watch Q002,Q033,...]

Each run_dir holds runtime_results.json from tests/acceptance/rag_h5_2_exact_100.py. Writes
<out_dir>/latency-by-position.md (one row per position, one column per run) and
<out_dir>/latency-correlation.json (per-run summary; for each pair, the changed cases and the
median absolute latency difference of changed vs unchanged cases).
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def _signature(case: dict) -> tuple:
    cites = tuple((c["document_id"], c["page_number"]) for c in case["citations"])
    return case["status"], cites, " ".join((case["answer"] or "").split())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir")
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--pair", action="append", default=[])
    parser.add_argument("--watch", default="")
    args = parser.parse_args()

    runs: dict[str, dict] = {}
    for item in args.runs:
        name, path = item.split("=", 1)
        cases = json.loads(Path(path, "runtime_results.json").read_text(encoding="utf-8"))["cases"]
        runs[name] = {"order": [c["id"] for c in cases], "cases": {c["id"]: c for c in cases}}
    ids = next(iter(runs.values()))["order"]
    if any(run["order"] != ids for run in runs.values()):
        raise SystemExit("question order differs between runs")
    watch = [w for w in args.watch.split(",") if w]

    header = "| Pos | Case | " + " | ".join(runs) + " | Watched |"
    lines = [header, "|---|---|" + "---|" * len(runs) + "---|"]
    for position, case_id in enumerate(ids, start=1):
        cells = " | ".join(str(run["cases"][case_id]["latency_ms"]) for run in runs.values())
        mark = "x" if case_id in watch else ""
        lines.append(f"| {position} | {case_id} | {cells} | {mark} |")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latency-by-position.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    report: dict[str, dict] = {"per_run": {}, "pairs": {}}
    for name, run in runs.items():
        latencies = [run["cases"][c]["latency_ms"] for c in ids]
        report["per_run"][name] = {
            "p50_ms": statistics.median(latencies),
            "max_ms": max(latencies),
            "max_case": ids[latencies.index(max(latencies))],
            "first10_mean_ms": round(statistics.mean(latencies[:10])),
            "rest_mean_ms": round(statistics.mean(latencies[10:])),
            "execution_errors": [c for c in ids if run["cases"][c].get("execution_status") != "OK"],
        }
    for pair in args.pair:
        a, b = pair.split(",")
        ca, cb = runs[a]["cases"], runs[b]["cases"]
        changed = [c for c in ids if _signature(ca[c]) != _signature(cb[c])]
        diff = {c: abs(ca[c]["latency_ms"] - cb[c]["latency_ms"]) for c in ids}
        unchanged = [diff[c] for c in ids if c not in changed]
        report["pairs"][pair] = {
            "changed": changed,
            "changed_latency_ms": {c: [ca[c]["latency_ms"], cb[c]["latency_ms"]] for c in changed},
            "abs_diff_median_changed_ms": (
                statistics.median([diff[c] for c in changed]) if changed else None
            ),
            "abs_diff_median_unchanged_ms": statistics.median(unchanged),
            "unchanged_over_10s": [c for c in ids if c not in changed and diff[c] > 10000],
        }
    report["watched"] = {
        c: {
            "position": ids.index(c) + 1,
            **{n: r["cases"][c]["latency_ms"] for n, r in runs.items()},
        }
        for c in watch
    }
    (out / "latency-correlation.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report["pairs"], indent=1))


if __name__ == "__main__":
    main()
