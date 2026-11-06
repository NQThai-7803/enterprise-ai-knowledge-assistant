"""Compare two baseline runs with two runs of a flag, keeping only changes seen in both.

usage (repo root, project venv):
  python scripts/eval/compare_flag_runs.py relevance <base1> <base2> <flag1> <flag2>
  python scripts/eval/compare_flag_runs.py rbac <base1> <base2> <flag1> <flag2>
  python scripts/eval/compare_flag_runs.py uat <base1> <base2> <flag1> <flag2>

Inputs are run_answer_relevance_dev.py results, run_rbac_dev.py results, or grade_proxy.py output.
A case counts as changed only when both baseline runs agree, both flag runs agree, and the two
outcomes differ. A case whose runs disagree on either side is reported as unstable and not counted.
Prints JSON: ids and counts only, never question or answer text.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

Outcome = str


def relevance_outcomes(run: Mapping[str, Any]) -> dict[str, Outcome]:
    return {
        case["id"]: "false_answer"
        if case["false_answer"]
        else ("correct" if case["passed"] else "wrong")
        for case in run["cases"]
    }


def rbac_outcomes(run: Mapping[str, Any]) -> dict[str, Outcome]:
    outcomes = {}
    for case in run["cases"]:
        key = f"{case['id']}:{case['kind']}"
        if case["kind"] == "negative":
            if case["leak_reasons"]:
                outcomes[key] = "leak"
            else:
                outcomes[key] = "correct" if case["status"] == "NO_ANSWER" else "false_answer"
        else:
            outcomes[key] = "correct" if case["control_passed"] else "wrong"
    return outcomes


def uat_outcomes(run: Mapping[str, Any]) -> dict[str, Outcome]:
    outcomes = {}
    for case in run["cases"]:
        if case["proxy_match"]:
            outcomes[case["id"]] = "correct"
        elif case["reference_status"] == "NO_ANSWER" and case["grounding_status"] == "ANSWERED":
            outcomes[case["id"]] = "false_answer"
        else:
            outcomes[case["id"]] = "wrong"
    return outcomes


READERS: dict[str, Callable[[Mapping[str, Any]], dict[str, Outcome]]] = {
    "relevance": relevance_outcomes,
    "rbac": rbac_outcomes,
    "uat": uat_outcomes,
}


def _counts(outcomes: Mapping[str, Outcome]) -> dict[str, int]:
    return {
        name: sum(value == name for value in outcomes.values())
        for name in ("correct", "false_answer", "wrong", "leak")
    }


def compare(
    base: Sequence[Mapping[str, Outcome]], flag: Sequence[Mapping[str, Outcome]]
) -> dict[str, Any]:
    changed = []
    unstable = []
    for key in sorted(base[0]):
        baseline = {run[key] for run in base}
        flagged = {run[key] for run in flag}
        if len(baseline) > 1 or len(flagged) > 1:
            unstable.append(key)
        elif baseline != flagged:
            changed.append({"id": key, "base": baseline.pop(), "flag": flagged.pop()})
    return {
        "base_runs": [_counts(run) for run in base],
        "flag_runs": [_counts(run) for run in flag],
        "changed_in_both_runs": changed,
        "unstable": unstable,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=sorted(READERS))
    parser.add_argument("runs", type=Path, nargs=4)
    args = parser.parse_args(argv)
    outcomes = [
        READERS[args.kind](json.loads(path.read_text(encoding="utf-8-sig"))) for path in args.runs
    ]
    if any(set(run) != set(outcomes[0]) for run in outcomes):
        print("REFUSED: the runs do not hold the same cases", file=sys.stderr)
        return 2
    print(json.dumps(compare(outcomes[:2], outcomes[2:]), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
