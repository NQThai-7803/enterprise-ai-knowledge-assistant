"""DEC-042: the variants against base, per set, and the selection rule. Dev sets only.

usage: python scripts/diagnostics/dec042_table.py <artifacts dir> [--json <out>]

<artifacts dir>/<run id>/eval-<set>-<run id>/ holds what `gh run download` fetched for each job
of the DEC-042 batch; a job's first configuration is its base (UAT runs as three jobs whose
bases are base1, base2, base3; their counts are summed). Categories and leaks are those of
summarize_ablation.py. Prints counts, item IDs and verdicts only, never question or answer text.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.diagnostics.summarize_ablation import RBAC, UAT, categories, leaks  # noqa: E402

GUARD_SETS = ("rbac", "relevance", "false_refusal", "false_refusal_v2", "compound")
GAIN_SETS = ("natural", "uat")
ORDER_DEPENDENT = frozenset({"FR2-L01", "FR2-L06"})  # DEC-041, registered in DEC-042
VARIANTS = ("c2a", "c2b", "v2", "c2a1", "c2b1")
CATS = ("correct", "false_refusal", "false_answer", "wrong", "infra")


def config_name(name: str, index: int) -> str:
    return "base" if index == 0 else name


def load(root: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """set -> config -> {"cats": {id: category}, "leaks": n, "prompt_tokens": [..]}."""
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for batch in sorted(root.glob("*/eval-*")):
        meta = json.loads((batch / "batch.json").read_text(encoding="utf-8"))
        set_name = meta["set"]
        kind = UAT if set_name == "uat" else RBAC if set_name == "rbac" else "relevance"
        names = [entry.split(":", 1)[0] for entry in meta["configs"].split(";") if entry]
        for index, name in enumerate(names):
            run = batch / name / "run1"
            results = json.loads((run / "results.json").read_text(encoding="utf-8-sig"))
            tokens = []
            trace = run / "simple_trace.jsonl"
            if trace.is_file():
                for line in trace.read_text(encoding="utf-8").splitlines():
                    record = json.loads(line)
                    if record.get("kind") == "question":
                        tokens += [t for t in record.get("prompt_tokens", []) if t]
            entry = out[set_name].setdefault(
                config_name(name, index), {"cats": {}, "leaks": 0, "prompt_tokens": []}
            )
            entry["cats"].update(categories(kind, results))
            entry["leaks"] += leaks(kind, run, results)
            entry["prompt_tokens"] += tokens
    return out


def row(entry: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(entry["cats"].values())
    tokens = entry["prompt_tokens"]
    return {
        **{cat: counts.get(cat, 0) for cat in CATS},
        "fa_wrong": counts.get("false_answer", 0) + counts.get("wrong", 0),
        "leaks": entry["leaks"],
        "mean_prompt_tokens": round(statistics.mean(tokens)) if tokens else None,
        "llm_calls": len(tokens),
    }


def infra_items(base: dict[str, str], variant: dict[str, str]) -> set[str]:
    """Items with an infra error in either configuration: left out of both (DEC-042)."""
    return {i for i in base.keys() | variant.keys() if "infra" in (base.get(i), variant.get(i))}


def changes(base: dict[str, str], variant: dict[str, str]) -> dict[str, list[str]]:
    infra = infra_items(base, variant)
    shared = sorted((set(base) & set(variant)) - infra)
    return {
        "fixed": [i for i in shared if base[i] != "correct" and variant[i] == "correct"],
        "broken": [i for i in shared if base[i] == "correct" and variant[i] != "correct"],
        "new_fa_wrong": [
            i
            for i in shared
            if base[i] not in ("false_answer", "wrong") and variant[i] in ("false_answer", "wrong")
        ],
        "infra": sorted(infra),
    }


def guard_count(cats: dict[str, str], skip: set[str]) -> int:
    return sum(1 for i, c in cats.items() if i not in skip and c in ("false_answer", "wrong"))


def verdict(data: dict[str, dict[str, dict[str, Any]]], variant: str) -> dict[str, Any]:
    reasons = []
    if any(data[s][variant]["leaks"] for s in data if variant in data[s]):
        reasons.append("leaks")
    for set_name in GUARD_SETS:
        base, flag = data[set_name]["base"]["cats"], data[set_name][variant]["cats"]
        order = ORDER_DEPENDENT if set_name == "false_refusal_v2" else set()
        skip = infra_items(base, flag) | order
        if guard_count(flag, skip) > guard_count(base, skip):
            reasons.append(f"{set_name}: false answers + wrong values up")
    gain = sum(
        Counter(data[s][variant]["cats"].values())["correct"]
        - Counter(data[s]["base"]["cats"].values())["correct"]
        for s in GAIN_SETS
    )
    if gain <= 0:
        reasons.append(f"natural + UAT correct {gain:+d}")
    return {"accepted": not reasons, "natural_uat_gain": gain, "reasons": reasons}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)
    data = load(args.root)
    report: dict[str, Any] = {"sets": {}, "changes": {}, "verdicts": {}}
    for set_name in sorted(data):
        report["sets"][set_name] = {name: row(entry) for name, entry in data[set_name].items()}
        base = data[set_name]["base"]["cats"]
        report["changes"][set_name] = {
            name: changes(base, data[set_name][name]["cats"])
            for name in VARIANTS
            if name in data[set_name]
        }
    for variant in VARIANTS:
        if all(variant in data[s] for s in (*GUARD_SETS, *GAIN_SETS)):
            report["verdicts"][variant] = verdict(data, variant)
    for set_name, rows in report["sets"].items():
        for name, values in rows.items():
            print(f"{set_name:16} {name:5} {json.dumps(values)}")
    for set_name, per_variant in report["changes"].items():
        for name, delta in per_variant.items():
            if any(delta.values()):
                print(f"{set_name:16} {name:5} {json.dumps(delta)}")
    for variant, result in report["verdicts"].items():
        print(f"VERDICT {variant}: {json.dumps(result)}")
    if args.json:
        args.json.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
