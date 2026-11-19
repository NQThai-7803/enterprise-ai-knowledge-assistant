"""Held-out v3.1 measurement (DEC-035, updated by DEC-036 and DEC-038). Prepared 2026-11-18; not run
during development, and never on a developer machine: only by .github/workflows/heldout-v3.yml.

usage (inside that workflow):
  python scripts/eval/heldout_v3_release.py gate
  python scripts/eval/heldout_v3_release.py run --manifest <manifest.json> --output <results.json>
  python scripts/eval/heldout_v3_release.py grading <batch dir> <out dir>

- gate refuses unless docs/eval/heldout-v3.1.yaml matches its lock (DEC-038).
- run asks the items of one configuration once, through ci_batch.sh, which interleaves the two
  configurations over two runs. An item with status PENDING_AUTHOR_REVIEW is not asked and is
  listed under excluded_pending; one with status EXCLUDED, or whose test account maps to no seeded
  user, under not_run. `run`, and `gate --no-pending`, refuse while an item is still
  PENDING_AUTHOR_REVIEW (DEC-038: no "run first, complete later").
- An item expects a refusal when its expected sources name no document code. Otherwise it expects
  an answer that cites one of those documents and states the values of the expected answer with no
  conflicting one (value-aware grading, DEC-032).
- grading writes, for both configurations and both runs, the counts, the DEC-035 verdict and the
  owner's tables (grading.md, grading.csv; the label columns stay empty). Counts are also split into
  near_duplicate items and the rest, and each answer is flagged when it cites another document than
  the gold one with the gold's values (for DEC-037 policy 1, applied by the owner).
Nothing here prints question, answer or source text: only ids, counts and categories.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.diagnostics.summarize_ablation import categories  # noqa: E402
from scripts.eval import (  # noqa: E402
    heldout_check,
    heldout_v3,
    reranker_check,
    run_heldout,
    run_rbac_dev,
    value_grading,
)

BASELINE, CANDIDATE = "legacy", "s3t"  # the configuration names heldout-v3.yml passes to ci_batch
CATS = ("correct", "false_refusal", "false_answer", "wrong")
ROLE_OF = {email: role for role, email in run_heldout.ACCOUNTS.items()}


class GateRefusedError(RuntimeError):
    """The held-out v3 run may not start."""


def gate(
    heldout: Path = heldout_v3.HELDOUT_V31, lock: Path = heldout_v3.LOCK_V31
) -> dict[str, Any]:
    try:
        items = heldout_v3.verify_frozen(heldout, lock)
    except (heldout_v3.FrozenSetChangedError, FileNotFoundError) as exc:
        raise GateRefusedError(str(exc)) from exc
    return {**json.loads(lock.read_text(encoding="utf-8")), "items": items}


def plan(
    items: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    """Items to ask, each with its role; items not asked with the reason; PENDING items."""
    asked, not_run, pending = [], {}, []
    for item in items:
        if item.get("status") == heldout_v3.PENDING:
            pending.append(item["id"])
            continue
        if item.get("status") == heldout_v3.EXCLUDED:
            not_run[item["id"]] = "EXCLUDED: not confirmed by its author by 2026-11-21 (DEC-038)"
            continue
        email = heldout_v3.ACCOUNTS.get(str(item["test_account"]).strip())
        if email is None:
            not_run[item["id"]] = "test account maps to no seeded user (DEC-030)"
            continue
        asked.append({**item, "role": ROLE_OF[email], "language": "vi"})
    return asked, not_run, pending


def expected_codes(item: Mapping[str, Any]) -> list[str]:
    return sorted({code for code, _ in heldout_v3.source_segments(item["expected_sources"])})


def grade_case(
    case: Mapping[str, Any], item: Mapping[str, Any], codes: Mapping[str, str]
) -> dict[str, Any]:
    wanted = expected_codes(item)
    answered = case.get("status") == "ANSWERED"
    answer = case.get("answer") or ""
    cited = run_rbac_dev.cited_codes(case, codes)
    leaks = []
    if heldout_check.VISIBLE.get(item["role"]) != "all":
        leaks = [f"cites {code}" for code in cited if code in heldout_check.RESTRICTED]
    values = None
    if wanted:
        values = value_grading.check(answer, item["expected_answer"], item["question"])
        passed = answered and bool(set(wanted) & set(cited)) and values["ok"]
    else:
        passed = case.get("status") == "NO_ANSWER"
    return {
        "id": item["id"],
        "group": item.get("group"),
        "role": item["role"],
        "expect": "answer" if wanted else "refuse",
        "expected_codes": wanted,
        "status": case.get("status"),
        "execution_status": case.get("execution_status"),
        "cited_codes": cited,
        "latency_ms": case.get("latency_ms"),
        "answer": case.get("answer"),
        "passed": bool(passed) and not leaks,
        # DEC-037 policy 1 is the owner's call: another document than the gold one, same values.
        "other_source_same_values": bool(
            wanted and answered and cited and not set(wanted) & set(cited) and values["ok"]
        ),
        "false_answer": answered and not wanted,
        "leak_reasons": leaks,
        "values": values,
    }


def summarize(
    cases: Sequence[Mapping[str, Any]], not_run: Mapping[str, str], pending: Sequence[str] = ()
) -> dict[str, Any]:
    cats = categories("relevance", {"cases": list(cases)})
    return {
        **{cat: sorted(i for i, c in cats.items() if c == cat) for cat in (*CATS, "infra")},
        "leaks": sorted(c["id"] for c in cases if c["leak_reasons"]),
        "not_run": sorted(not_run),
        "excluded_pending": sorted(pending),
    }


def _same_sign_beyond_spread(base: Sequence[int], cand: Sequence[int]) -> int:
    """-1 when the candidate is lower in every run by more than the spread (DEC-027), +1 when
    higher, 0 otherwise."""
    diffs = [c - b for b, c in zip(base, cand, strict=True)]
    spread = max(max(base) - min(base), max(cand) - min(cand))
    if all(d < 0 for d in diffs) and min(map(abs, diffs)) > spread:
        return -1
    if all(d > 0 for d in diffs) and min(map(abs, diffs)) > spread:
        return 1
    return 0


def verdict(counts: Mapping[str, Mapping[str, Mapping[str, int]]]) -> dict[str, Any]:
    """DEC-035: leaks 0; lower false answers + wrong; then fewer false refusals; else the
    current default stays. counts[config][run] holds the per-category numbers."""
    runs = sorted(counts[BASELINE])
    side = {
        cfg: {
            "fa_w": [counts[cfg][r]["false_answer"] + counts[cfg][r]["wrong"] for r in runs],
            "false_refusal": [counts[cfg][r]["false_refusal"] for r in runs],
            "leaks": sum(counts[cfg][r]["leaks"] for r in runs),
            "infra": sum(counts[cfg][r]["infra"] for r in runs),
        }
        for cfg in (BASELINE, CANDIDATE)
    }
    out = {"runs": runs, **side}
    if side[CANDIDATE]["leaks"]:
        return {**out, "winner": BASELINE, "reason": "the candidate leaked"}
    if side[BASELINE]["leaks"]:
        return {**out, "winner": CANDIDATE, "reason": "the current default leaked"}
    for metric in ("fa_w", "false_refusal"):
        sign = _same_sign_beyond_spread(side[BASELINE][metric], side[CANDIDATE][metric])
        if sign:
            winner = CANDIDATE if sign < 0 else BASELINE
            return {**out, "winner": winner, "reason": f"{metric} differs in every run (DEC-027)"}
    return {**out, "winner": BASELINE, "reason": "tie on both counts: the current default stays"}


def load_runs(batch: Path) -> dict[str, dict[str, dict[str, Any]]]:
    runs: dict[str, dict[str, dict[str, Any]]] = {}
    for cfg in (BASELINE, CANDIDATE):
        for path in sorted((batch / cfg).glob("run*/results.json")):
            runs.setdefault(cfg, {})[path.parent.name] = json.loads(
                path.read_text(encoding="utf-8")
            )
    if set(runs) != {BASELINE, CANDIDATE} or len(runs[BASELINE]) != len(runs[CANDIDATE]):
        raise GateRefusedError("the batch lacks a configuration or a run")
    return runs


def build(
    runs: Mapping[str, Mapping[str, Mapping[str, Any]]], items: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], str, list[dict[str, Any]], str]:
    """counts and verdict, the owner's markdown, the CSV rows, and a text-free summary."""
    counts: dict[str, dict[str, dict[str, int]]] = {}
    cats: dict[tuple[str, str], dict[str, str]] = {}
    for cfg, by_run in runs.items():
        for run, result in by_run.items():
            cat = categories("relevance", result)
            cats[(cfg, run)] = cat
            counts.setdefault(cfg, {})[run] = {
                **{name: sum(v == name for v in cat.values()) for name in (*CATS, "infra")},
                "leaks": sum(bool(c["leak_reasons"]) for c in result["cases"]),
            }
    decision = verdict(counts)
    run_names = sorted(runs[BASELINE])
    first = next(iter(runs[BASELINE].values()))
    not_run = sorted(first["not_run"])
    pending = sorted(first.get("excluded_pending", []))
    near = {i["id"] for i in items if i.get("near_duplicate")}
    head = [
        "| Configuration | Run | Correct | False refusal | False answer | Wrong | Leaks | Infra |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cfg in (BASELINE, CANDIDATE):
        for run in run_names:
            n = counts[cfg][run]
            head.append(
                f"| {cfg} | {run} | {n['correct']} | {n['false_refusal']} | {n['false_answer']} | "
                f"{n['wrong']} | {n['leaks']} | {n['infra']} |"
            )
    split = [
        "| Configuration | Run | Group | Items | Correct | False refusal | False answer | Wrong |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for cfg in (BASELINE, CANDIDATE):
        for run in run_names:
            for group in ("near_duplicate", "other"):
                got = [c for i, c in cats[(cfg, run)].items() if (i in near) == (group != "other")]
                n = {name: got.count(name) for name in CATS}
                split.append(
                    f"| {cfg} | {run} | {group} | {len(got)} | {n['correct']} | "
                    f"{n['false_refusal']} | {n['false_answer']} | {n['wrong']} |"
                )
    summary = "\n".join(
        [
            "# Held-out v3.1 (DEC-035, DEC-038)",
            "",
            "Held-out v3.1 decides between the two configurations **and** measures them, so its "
            "figures are not an unbiased estimate of the chosen one.",
            "",
            *head,
            "",
            "Split as for held-out v2: near_duplicate items (near UAT or a dev set) and the rest.",
            "",
            *split,
            "",
            f"Not asked: {', '.join(not_run) or 'none'}. "
            f"Excluded, PENDING_AUTHOR_REVIEW: {', '.join(pending) or 'none'}.",
            "",
            f"**Verdict:** `{decision['winner']}` ({decision['reason']}).",
        ]
    )
    by_case = {
        (cfg, run): {c["id"]: c for c in runs[cfg][run]["cases"]}
        for cfg in runs
        for run in run_names
    }
    md = [summary, "", "Owner: label each item in grading.csv (PASS / PARTIAL / FAIL / LEAK).", ""]
    rows = []
    for item in items:
        if item["id"] in not_run or item["id"] in pending:
            continue
        near_tag = (
            f", near_duplicate: {item['near_duplicate']}" if item.get("near_duplicate") else ""
        )
        md += [
            "---",
            "",
            f"## {item['id']} (group {item.get('group')}, account `{item['test_account']}`"
            f"{near_tag})",
            "",
            f"**Question:** {item['question']}",
            "",
            f"**Expected answer:** {item['expected_answer']}",
            "",
            f"**Expected sources:** {item['expected_sources']}",
            "",
        ]
        for cfg in (BASELINE, CANDIDATE):
            row = {"id": item["id"], "near_duplicate": item.get("near_duplicate", "")}
            row["configuration"] = cfg
            for run in run_names:
                case = by_case[(cfg, run)][item["id"]]
                category = cats[(cfg, run)][item["id"]]
                same = int(bool(case.get("other_source_same_values")))
                row |= {
                    f"{run}_category": category,
                    f"{run}_status": case["status"],
                    f"{run}_cited": " ".join(case["cited_codes"]),
                    f"{run}_other_source_same_values": same,
                }
                values = case.get("values") or {}
                flag = "; **another source than the gold, same values**" if same else ""
                md += [
                    f"**{cfg}, {run}: {category}** ({case['status']}; cites "
                    f"{', '.join(case['cited_codes']) or 'nothing'}; values missing "
                    f"{values.get('missing', [])}, conflicting {values.get('conflicting', [])}"
                    f"{flag})",
                    "",
                    "> " + (case.get("answer") or "").replace("\n", "\n> "),
                    "",
                ]
            rows.append({**row, "label": "", "notes": ""})
        md += ["Owner: ", ""]
    return {"counts": counts, "verdict": decision}, "\n".join(md) + "\n", rows, summary + "\n"


def _password_roles(items: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    roles = {item["role"] for item in items}
    missing = [r for r in roles if not os.environ.get(f"EVAL_PASSWORD_{r.upper()}")]
    if missing:
        raise GateRefusedError("set " + ", ".join(f"EVAL_PASSWORD_{r.upper()}" for r in missing))
    return {r: os.environ[f"EVAL_PASSWORD_{r.upper()}"] for r in roles}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("gate").add_argument(
        "--no-pending", action="store_true", help="refuse while an item is PENDING (DEC-038)"
    )
    runner = sub.add_parser("run")
    reranker_check.add_arguments(runner)
    runner.add_argument("--manifest", type=Path, required=True)
    runner.add_argument("--output", type=Path, required=True)
    grading = sub.add_parser("grading")
    grading.add_argument("batch", type=Path)
    grading.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    try:
        lock = gate()
        pending_ids = [i["id"] for i in lock["items"] if i.get("status") == heldout_v3.PENDING]
        if pending_ids and (args.command == "run" or getattr(args, "no_pending", False)):
            raise GateRefusedError(
                f"still {heldout_v3.PENDING}: {', '.join(pending_ids)}; resolve them first "
                "with heldout_v3.py set-status (DEC-038)"
            )
        if args.command == "gate":
            print(f"held-out v3.1 frozen: {len(lock['items'])} items, sha256 {lock['sha256']}")
            return 0
        if args.command == "run":
            asked, not_run, pending = plan(lock["items"])
            base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
            passwords = _password_roles(asked)
            reranker = reranker_check.guard(args, base_url)
            codes = {
                d["id"]: d["code"]
                for d in json.loads(args.manifest.read_text(encoding="utf-8"))["documents"]
            }
            answers = args.output.with_name("answers.json")
            started_at = datetime.now(UTC).isoformat()
            code = run_heldout.run(
                output=answers,
                selected=set(),
                resume=False,
                base_url=base_url,
                passwords=passwords,
                frozen={"sha256": lock["sha256"], "version": lock["version"]},
                all_items=asked,
                label="heldout-v3",
            )
            raw = {c["id"]: c for c in json.loads(answers.read_text(encoding="utf-8"))["cases"]}
            cases = [grade_case(raw[item["id"]], item, codes) for item in asked]
            payload = {
                "version": "heldout_v3",
                "heldout_sha256": lock["sha256"],
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                **reranker,
                "not_run": not_run,
                "excluded_pending": pending,
                "summary": summarize(cases, not_run, pending),
                "cases": cases,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), "utf-8")
            counts = {k: len(v) for k, v in payload["summary"].items()}
            print(json.dumps(counts))  # ids and counts only
            return reranker_check.finish(args.output, reranker, base_url, code)
        if args.command == "grading":
            runs = load_runs(args.batch)
            for by_run in runs.values():
                if any(r["heldout_sha256"] != lock["sha256"] for r in by_run.values()):
                    raise GateRefusedError("a run was not made on the frozen held-out v3.1 file")
            result, md, rows, summary = build(runs, lock["items"])
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / "verdict.json").write_text(json.dumps(result, indent=1) + "\n", "utf-8")
            (args.out / "grading.md").write_text(md, encoding="utf-8")
            (args.out / "summary.md").write_text(summary, encoding="utf-8")
            with (args.out / "grading.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            print(f"verdict: {result['verdict']['winner']} ({result['verdict']['reason']})")
            return 0
    except (
        GateRefusedError,
        run_heldout.HeldoutHashMismatchError,
        reranker_check.RerankerModeRefusedError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
