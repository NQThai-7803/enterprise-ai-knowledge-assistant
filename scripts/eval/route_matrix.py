"""DEC-041 measurement of the dev sets: legacy, s3t and hybrid in one job per set.

usage: python scripts/eval/route_matrix.py <batch dir>... --md <summary.md> [--json <out.json>]

Each <batch dir> is one downloaded eval artifact (eval-<set>-<run id>) whose configurations are
named legacy, s3t and hybrid, run once. Per set and configuration: the categories of
summarize_ablation.py (correct, false_refusal, wrong, false_answer, infra), leaks, time. Then the
route matrix: whether legacy's deterministic route answered before the LLM (det), after it
(repair) or not (none), against legacy right/wrong and s3t right/wrong; how often the route fired
and was right; the items hybrid loses to s3t or to legacy; and the items where hybrid's route
decision differs from legacy's (it should not: the same route runs under the same conditions).
Prints and writes ids and counts only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.diagnostics.summarize_ablation import (  # noqa: E402
    RBAC,
    UAT,
    categories,
    latencies,
    leaks,
)

CONFIGS = ("legacy", "s3t", "hybrid")
CATEGORIES = ("correct", "false_refusal", "wrong", "false_answer", "infra")


def route_state(route: str | None) -> str:
    """det: the deterministic route answered before any LLM call; repair: after it."""
    if route is None:
        return "unknown"
    if route.startswith("det_"):
        return "det"
    return "repair" if route.startswith("repair_") else "none"


def _rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    return results.get("cases") or next(v for v in results.values() if isinstance(v, list))


def summarize(batch: Path) -> dict[str, Any]:
    meta = json.loads((batch / "batch.json").read_text(encoding="utf-8"))
    kind = UAT if meta["set"] == UAT else RBAC if meta["set"] == RBAC else "relevance"
    cats: dict[str, dict[str, str]] = {}
    routes: dict[str, dict[str, str | None]] = {}
    configs: dict[str, Any] = {}
    for name in CONFIGS:
        run = batch / name / "run1"
        results = json.loads((run / "results.json").read_text(encoding="utf-8-sig"))
        cats[name] = categories(kind, results)
        routes[name] = {r["id"] + r.get("kind", ""): r.get("answer_route") for r in _rows(results)}
        timing = run / "timing.txt"
        lat = latencies(kind, run, results)
        configs[name] = {
            **{c: Counter(cats[name].values()).get(c, 0) for c in CATEGORIES},
            "leaks": leaks(kind, run, results),
            "seconds": int(timing.read_text().split("=")[1]) if timing.is_file() else None,
            "latency_p50_ms": int(statistics.median(lat)) if lat else None,
            "routes": dict(Counter(route_state(r) for r in routes[name].values())),
        }
    ids = sorted(cats["legacy"])
    right = {name: {i for i in ids if cats[name].get(i) == "correct"} for name in CONFIGS}
    matrix = Counter(
        (route_state(routes["legacy"].get(i)), i in right["legacy"], i in right["s3t"]) for i in ids
    )
    fired = {
        name: sorted(i for i in ids if route_state(routes[name].get(i)) == "det")
        for name in ("legacy", "hybrid")
    }
    return {
        "set": meta["set"],
        "git_sha": meta.get("git_sha"),
        "items": len(ids),
        "configs": configs,
        "matrix": [
            {"legacy_route": s, "legacy_correct": lc, "s3t_correct": sc, "items": n}
            for (s, lc, sc), n in sorted(matrix.items())
        ],
        "route_fired": {
            name: {"items": len(f), "correct": len(right[name].intersection(f)), "ids": f}
            for name, f in fired.items()
        },
        "hybrid_loses_to_s3t": sorted(right["s3t"] - right["hybrid"]),
        "hybrid_loses_to_legacy": sorted(right["legacy"] - right["hybrid"]),
        "route_mismatch": sorted(set(fired["legacy"]) ^ set(fired["hybrid"])),
    }


def markdown(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "| Set | Config | Correct | False refusal | Wrong value | False answer | Infra | Leaks "
        "| Seconds | p50 ms | Route det / repair / none |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for s in summaries:
        for name, c in s["configs"].items():
            r = c["routes"]
            lines.append(
                f"| {s['set']} ({s['items']}) | {name} | {c['correct']} | {c['false_refusal']} "
                f"| {c['wrong']} | {c['false_answer']} | {c['infra']} | {c['leaks']} "
                f"| {c['seconds']} | {c['latency_p50_ms']} "
                f"| {r.get('det', 0)} / {r.get('repair', 0)} / {r.get('none', 0)} |"
            )
    lines += [
        "",
        "Route matrix: legacy's route x legacy correct x s3t correct (items).",
        "",
        "| Set | Legacy route | Legacy correct | s3t correct | Items |",
        "|---|---|---|---|---:|",
    ]
    for s in summaries:
        for row in s["matrix"]:
            lines.append(
                f"| {s['set']} | {row['legacy_route']} | {row['legacy_correct']} "
                f"| {row['s3t_correct']} | {row['items']} |"
            )
    lines += ["", "| Set | Route fired (legacy) | Right | Route fired (hybrid) | Right "
              "| Hybrid loses to s3t | Hybrid loses to legacy | Route mismatch |",
              "|---|---:|---:|---:|---:|---|---|---|"]  # fmt: skip
    for s in summaries:
        f = s["route_fired"]
        lines.append(
            f"| {s['set']} | {f['legacy']['items']} | {f['legacy']['correct']} "
            f"| {f['hybrid']['items']} | {f['hybrid']['correct']} "
            f"| {' '.join(s['hybrid_loses_to_s3t']) or '-'} "
            f"| {' '.join(s['hybrid_loses_to_legacy']) or '-'} "
            f"| {' '.join(s['route_mismatch']) or '-'} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", type=Path, nargs="+")
    parser.add_argument("--md", type=Path, required=True)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    summaries = [summarize(batch) for batch in args.batches]
    args.md.write_text(markdown(summaries), encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps(summaries, indent=1), encoding="utf-8")
    print(f"{len(summaries)} sets -> {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
