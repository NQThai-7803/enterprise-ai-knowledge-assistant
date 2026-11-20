"""The question sets of ci_batch.sh (DEC-016): the one registry it resolves a set name with.

usage (ci_batch.sh calls it before anything else, and alone under --validate-only):
  python scripts/eval/batch_sets.py validate <set> --configs "<name> <name>..." [case ids...]

validate resolves the set, checks its frozen files (for heldout_v3: the DEC-038 gate with no item
PENDING, ACTIVE items only), and that the password of every eval account its questions need is
set. It calls no API and no model. It prints the set name, the number of questions, their ids and
the ids not asked: never any question text. Exit 0 when the set would run, 2 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import (  # noqa: E402
    heldout_v3,
    heldout_v3_release,
    run_answer_relevance_dev,
    run_natural_dev,
    run_rbac_dev,
)

UAT = ROOT / "eval-data" / "uat" / "questions.json"
# set name -> frozen file of run_answer_relevance_dev.py --set
FROZEN = {
    "relevance": "answer_relevance_dev_v1",
    "false_refusal": "false_refusal_dev_v1",
    "false_refusal_v2": "false_refusal_dev_v2",
    "compound": "compound_partial_dev_v1",
}


class BatchSetError(RuntimeError):
    """The set would not run: unknown, changed, gated or missing an account password."""


# Each loader returns the ids asked, the ids not asked, and the env variables holding passwords.
Plan = tuple[list[str], list[str], list[str]]


def _passwords(roles: Sequence[str]) -> list[str]:
    return [f"EVAL_PASSWORD_{role.upper()}" for role in sorted(set(roles))]


def _uat(cases: Sequence[str]) -> Plan:
    data = json.loads(UAT.read_text(encoding="utf-8"))
    ids = [item["id"] for item in data["items"]]
    unknown = sorted(set(cases) - set(ids))
    if unknown:
        raise BatchSetError(f"unknown uat case ids: {' '.join(unknown)}")
    return [i for i in ids if not cases or i in cases], [], [data["password_env"]]


def _rbac(_: Sequence[str]) -> Plan:
    ids = [item["id"] for item in run_rbac_dev.load_set()["items"]]
    return ids, [], _passwords(list(run_rbac_dev.ACCOUNTS))


def _frozen(name: str) -> Callable[[Sequence[str]], Plan]:
    def load(_: Sequence[str]) -> Plan:
        source = ROOT / "tests" / "acceptance" / f"{name}.yaml"
        try:
            run_answer_relevance_dev.verify_frozen(source, source.with_suffix(".lock"))
        except run_answer_relevance_dev.SetChangedError as exc:
            raise BatchSetError(str(exc)) from exc
        ids = [item["id"] for item in run_rbac_dev.load_set(source)["items"]]
        return ids, [], _passwords(["admin", run_answer_relevance_dev.ROLE])

    return load


def _natural(_: Sequence[str]) -> Plan:
    try:
        items = run_natural_dev.verified_inputs()["items"]
    except run_natural_dev.NaturalRefusedError as exc:
        raise BatchSetError(str(exc)) from exc
    return [i["id"] for i in items], [], _passwords([i["role"] for i in items])


def _heldout_v3(_: Sequence[str]) -> Plan:
    """The same gate and plan as heldout_v3_release.py run (DEC-035/038)."""
    try:
        lock = heldout_v3_release.gate()
    except heldout_v3_release.GateRefusedError as exc:
        raise BatchSetError(str(exc)) from exc
    asked, not_run, pending = heldout_v3_release.plan(lock["items"])
    if pending:
        raise BatchSetError(f"still {heldout_v3.PENDING}: {', '.join(pending)} (DEC-038)")
    return [i["id"] for i in asked], sorted(not_run), _passwords([i["role"] for i in asked])


SETS: dict[str, Callable[[Sequence[str]], Plan]] = {
    "uat": _uat,
    "rbac": _rbac,
    **{name: _frozen(frozen) for name, frozen in FROZEN.items()},
    "natural": _natural,
    "heldout_v3": _heldout_v3,
}
# The configuration names heldout_v3_release.py grading reads (DEC-035).
CONFIG_NAMES = {"heldout_v3": [heldout_v3_release.BASELINE, heldout_v3_release.CANDIDATE]}


def validate(set_name: str, configs: Sequence[str], cases: Sequence[str]) -> Plan:
    if set_name not in SETS:
        raise BatchSetError(f"unknown set {set_name}; known: {' '.join(SETS)}")
    if cases and set_name != "uat":
        raise BatchSetError("case ids apply to the uat set only")
    wanted = CONFIG_NAMES.get(set_name)
    if wanted and list(configs) != wanted:
        raise BatchSetError(f"{set_name} needs the configurations {' '.join(wanted)}")
    ids, not_run, envs = SETS[set_name](cases)
    if not ids:
        raise BatchSetError(f"{set_name} has no question to ask")
    missing = [name for name in envs if not os.environ.get(name)]
    if missing:
        raise BatchSetError("set " + ", ".join(missing))
    return ids, not_run, envs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate")
    check.add_argument("set_name")
    check.add_argument("--configs", default="", help="space-separated configuration names")
    check.add_argument("cases", nargs="*")
    args = parser.parse_args(argv)
    try:
        ids, not_run, _ = validate(args.set_name, args.configs.split(), args.cases)
    except (BatchSetError, FileNotFoundError, KeyError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"set: {args.set_name}")
    print(f"questions: {len(ids)}")
    print(f"ids: {' '.join(ids)}")
    print(f"not run: {' '.join(not_run) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
