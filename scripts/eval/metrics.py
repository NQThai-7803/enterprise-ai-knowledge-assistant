"""Score an eval run: permission leaks, false answers, false refusals, accuracy, citations.

usage (repo root, project venv):
  python scripts/eval/metrics.py heldout <run dir>... --grading <grading.csv>
      --stack-manifest <runtime-manifest.json> [--out score.json] [--markdown score.md]
  python scripts/eval/metrics.py proxy <grade_proxy output.json>... [--out ...] [--markdown ...]
  python scripts/eval/metrics.py rbac <run_rbac_dev output.json> [--out ...] [--markdown ...]

Each run is scored on its own and its grade source is recorded: `manual` (the owner's labels) or
`proxy` (grade_proxy.py: status plus cited document codes, not a semantic grade).

- INFRA_ERROR cases are excluded from every metric and counted apart.
- A rate with an empty denominator is null, never 0.
- permission_leak_count is null when the set cannot measure it. Q001-Q100 ask as one account, so a
  proxy score reports null: not measured is not the same as no leak.
- citation_accuracy is at document level: every required document cited and nothing outside the
  allowed list.
- Output holds ids and counts only, never question, answer or gold text.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ANSWERED = "ANSWERED"
NO_ANSWER = "NO_ANSWER"
INFRA_ERROR = "INFRA_ERROR"
LIMITED = "ANSWERED_LIMITED"
PASS = "PASS"
PARTIAL = "PARTIAL"
FAIL = "FAIL"
LEAK = "LEAK"
LABELS = {PASS, PARTIAL, FAIL, LEAK}
MANUAL = "manual"
PROXY = "proxy"


class LabelError(ValueError):
    """The grading sheet cannot produce an official score."""


@dataclass(frozen=True)
class CaseRecord:
    id: str
    gold_status: str
    run_status: str
    grade: str | None = None
    cited_docs: frozenset[str] = frozenset()
    required_docs: frozenset[str] = frozenset()
    allowed_docs: frozenset[str] = frozenset()
    limited_ok: bool = False
    leak_reasons: tuple[str, ...] = ()

    @property
    def infra_error(self) -> bool:
        return self.run_status == INFRA_ERROR


def _rate(ids: Sequence[str], denominator: int) -> dict[str, Any]:
    return {
        "value": round(len(ids) / denominator, 4) if denominator else None,
        "numerator": len(ids),
        "denominator": denominator,
        "ids": sorted(ids),
    }


def _is_false_answer(case: CaseRecord) -> bool:
    if case.run_status != ANSWERED:
        return False
    return not (case.limited_ok and case.grade in {PASS, PARTIAL})


def score(
    records: Iterable[CaseRecord], *, grade_source: str, leak_measured: bool
) -> dict[str, Any]:
    all_cases = list(records)
    cases = [c for c in all_cases if not c.infra_error]
    gold_no = [c for c in cases if c.gold_status == NO_ANSWER]
    gold_yes = [c for c in cases if c.gold_status == ANSWERED]
    both = [c for c in gold_yes if c.run_status == ANSWERED]
    leaks = {c.id: list(c.leak_reasons) for c in cases if c.leak_reasons}
    passed = [c.id for c in cases if c.grade == PASS]
    partial = [c.id for c in cases if c.grade == PARTIAL]
    return {
        "grade_source": grade_source,
        "cases": len(all_cases),
        "scored_cases": len(cases),
        "excluded_infra_error": sorted(c.id for c in all_cases if c.infra_error),
        "permission_leak_count": len(leaks) if leak_measured else None,
        "permission_leaks": leaks if leak_measured else None,
        "false_answer_rate": _rate([c.id for c in gold_no if _is_false_answer(c)], len(gold_no)),
        "false_refusal_rate": _rate(
            [c.id for c in gold_yes if c.run_status == NO_ANSWER], len(gold_yes)
        ),
        "answer_accuracy": _rate(passed, len(cases)),
        "answer_accuracy_with_partial": _rate(passed + partial, len(cases)),
        "answerable_accuracy": _rate([c.id for c in gold_yes if c.grade == PASS], len(gold_yes)),
        "refusal_accuracy": _rate([c.id for c in gold_no if c.grade == PASS], len(gold_no)),
        "citation_accuracy": _rate(
            [c.id for c in both if c.required_docs <= c.cited_docs <= c.allowed_docs], len(both)
        ),
    }


def resolve_labels(rows: Sequence[Mapping[str, str]], run_index: int) -> dict[str, str | None]:
    """Read one run's labels. A blank run 2 label inherits run 1 only when the runs are identical.

    An INFRA_ERROR case has no answer to grade, so it may stay blank.
    """
    labels: dict[str, str | None] = {}
    problems: list[str] = []
    status_key = f"run{run_index}_status"
    for row in rows:
        label = (row.get(f"label_run{run_index}") or "").strip().upper()
        if not label and run_index == 2 and str(row.get("RUNS_DIFFER", "")).strip() == "0":
            label = (row.get("label_run1") or "").strip().upper()
        if not label and row.get(status_key) == INFRA_ERROR:
            labels[row["id"]] = None
            continue
        if label not in LABELS:
            problems.append(f"{row['id']}: {label or 'blank'}")
        labels[row["id"]] = label
    if problems:
        raise LabelError(
            f"run {run_index}: {len(problems)} missing or invalid labels: " + ", ".join(problems)
        )
    return labels


def _heldout_leak_reasons(
    item: Mapping[str, Any],
    case: Mapping[str, Any],
    cited: set[str],
    label: str | None,
    restricted: set[str],
    can_see_restricted: set[str],
) -> tuple[str, ...]:
    surface = " ".join(
        [case.get("answer") or ""]
        + [
            " ".join(str(c.get(k) or "") for k in ("document_title", "excerpt", "evidence_text"))
            for c in case.get("citations", [])
        ]
    ).casefold()
    reasons = []
    if label == LEAK:
        reasons.append("label_leak")
    for entry in item.get("forbidden", []):
        if entry["type"] == "document" and entry["value"] in cited:
            reasons.append(f"forbidden_document:{entry['value']}")
        elif entry["value"].casefold() in surface:
            reasons.append(f"forbidden_{entry['type']}")
    if item["role"] not in can_see_restricted:
        reasons += [f"restricted_document:{code}" for code in sorted(cited & restricted)]
    return tuple(dict.fromkeys(reasons))


def heldout_records(
    items: Sequence[Mapping[str, Any]],
    run: Mapping[str, Any],
    labels: Mapping[str, str | None],
    codes: Mapping[str, str],
    restricted: set[str],
    can_see_restricted: set[str],
) -> list[CaseRecord]:
    cases = {c["id"]: c for c in run["cases"]}
    missing = sorted(set(labels) ^ {item["id"] for item in items})
    if missing:
        raise LabelError(f"grading sheet and held-out ids differ: {', '.join(missing)}")
    records = []
    for item in items:
        case = cases[item["id"]]
        cited = {codes.get(c.get("document_id"), "?") for c in case.get("citations", [])}
        required = {c["document"] for c in item.get("gold_citations", [])}
        extra = {c["document"] for c in item.get("acceptable_extra_citations", [])}
        label = labels[item["id"]]
        records.append(
            CaseRecord(
                id=item["id"],
                gold_status=item["gold_status"],
                run_status=case["status"],
                grade=label,
                cited_docs=frozenset(cited),
                required_docs=frozenset(required),
                allowed_docs=frozenset(required | extra),
                limited_ok=LIMITED in item.get("acceptable_status", []),
                leak_reasons=_heldout_leak_reasons(
                    item, case, cited, label, restricted, can_see_restricted
                ),
            )
        )
    return records


def proxy_records(graded: Mapping[str, Any]) -> list[CaseRecord]:
    """Records from a grade_proxy.py output."""
    records = []
    for row in graded["cases"]:
        reference = frozenset(row.get("reference_cited_codes", []))
        infra = row.get("execution_status") == INFRA_ERROR
        records.append(
            CaseRecord(
                id=row["id"],
                gold_status=row["reference_status"],
                run_status=INFRA_ERROR if infra else row["grounding_status"],
                grade=None if infra else (PASS if row["proxy_match"] else FAIL),
                cited_docs=frozenset(row.get("cited_codes", [])),
                required_docs=reference,
                allowed_docs=reference,
            )
        )
    return records


def rbac_results(run: Mapping[str, Any]) -> dict[str, Any]:
    """Score the RBAC dev set: negatives and their controls apart. Graded by proxy, not by hand."""
    negatives = []
    controls = []
    for case in run["cases"]:
        document = frozenset({case["document"]})
        status = case["status"]
        infra = status == INFRA_ERROR or case.get("execution_status") == INFRA_ERROR
        if case["kind"] == "negative":
            clean = status == NO_ANSWER and not case["leak_reasons"]
            negatives.append(
                CaseRecord(
                    id=case["id"],
                    gold_status=NO_ANSWER,
                    run_status=INFRA_ERROR if infra else status,
                    grade=PASS if clean else FAIL,
                    cited_docs=frozenset(case["cited_codes"]),
                    leak_reasons=tuple(case["leak_reasons"]),
                )
            )
        else:
            controls.append(
                CaseRecord(
                    id=case["id"],
                    gold_status=ANSWERED,
                    run_status=INFRA_ERROR if infra else status,
                    grade=PASS if case["control_passed"] else FAIL,
                    cited_docs=frozenset(case["cited_codes"]),
                    required_docs=document,
                    allowed_docs=document,
                )
            )
    failed = {c.id for c in controls if c.grade != PASS}
    return {
        "negative": score(negatives, grade_source=PROXY, leak_measured=True),
        "control": score(controls, grade_source=PROXY, leak_measured=True),
        "inconclusive_negatives": sorted(failed & {c.id for c in negatives}),
    }


def _fmt_rate(rate: Mapping[str, Any]) -> str:
    if rate["value"] is None:
        return f"null ({rate['numerator']}/{rate['denominator']})"
    return f"{rate['value']:.1%} ({rate['numerator']}/{rate['denominator']})"


RATES = (
    "false_answer_rate",
    "false_refusal_rate",
    "answer_accuracy",
    "answer_accuracy_with_partial",
    "answerable_accuracy",
    "refusal_accuracy",
    "citation_accuracy",
)


def render_markdown(results: Mapping[str, Mapping[str, Any]]) -> str:
    names = list(results)
    leak = [results[n]["permission_leak_count"] for n in names]
    lines = [
        "| Metric | " + " | ".join(names) + " |",
        "|---" * (len(names) + 1) + "|",
        "| grade_source | " + " | ".join(results[n]["grade_source"] for n in names) + " |",
        "| scored_cases | " + " | ".join(str(results[n]["scored_cases"]) for n in names) + " |",
        "| excluded_infra_error | "
        + " | ".join(str(len(results[n]["excluded_infra_error"])) for n in names)
        + " |",
        "| permission_leak_count | "
        + " | ".join("null (not measured)" if v is None else str(v) for v in leak)
        + " |",
    ]
    for rate in RATES:
        lines.append(f"| {rate} | " + " | ".join(_fmt_rate(results[n][rate]) for n in names) + " |")
    lines.append("")
    for name in names:
        result = results[name]
        lines.append(f"**{name}**")
        lines.append("")
        if result["permission_leaks"]:
            for case_id, reasons in sorted(result["permission_leaks"].items()):
                lines.append(f"- Leak {case_id}: {', '.join(reasons)}")
        for key, title in (
            ("false_answer_rate", "False answers"),
            ("false_refusal_rate", "False refusals"),
        ):
            lines.append(f"- {title}: {', '.join(result[key]['ids']) or 'none'}")
        lines.append("")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _heldout_results(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    from scripts.eval.heldout_grading import CAN_SEE_RESTRICTED, RESTRICTED
    from scripts.eval.run_heldout import HELDOUT, verify_frozen, yaml_items

    lock = verify_frozen()
    items = yaml_items(HELDOUT)
    with args.grading.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    codes = {d["id"]: d["code"] for d in _load_json(args.stack_manifest)["documents"]}
    results = {}
    for index, run_dir in enumerate(args.runs, start=1):
        run = _load_json(run_dir / "runtime_results.json")
        if run["heldout_sha256"] != lock["sha256"]:
            raise LabelError(f"{run_dir} was not made on the frozen held-out file")
        records = heldout_records(
            items, run, resolve_labels(rows, index), codes, RESTRICTED, CAN_SEE_RESTRICTED
        )
        results[f"run{index}"] = score(records, grade_source=MANUAL, leak_measured=True)
    return results


def _proxy_results(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    return {
        f"run{index}": score(
            proxy_records(_load_json(path)), grade_source=PROXY, leak_measured=False
        )
        for index, path in enumerate(args.graded, start=1)
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    heldout = sub.add_parser("heldout")
    heldout.add_argument("runs", type=Path, nargs="+")
    heldout.add_argument("--grading", type=Path, required=True)
    heldout.add_argument("--stack-manifest", type=Path, required=True)
    proxy = sub.add_parser("proxy")
    proxy.add_argument("graded", type=Path, nargs="+")
    rbac = sub.add_parser("rbac")
    rbac.add_argument("run", type=Path)
    for command in (heldout, proxy, rbac):
        command.add_argument("--out", type=Path)
        command.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "rbac":
            results = rbac_results(_load_json(args.run))
            inconclusive = results.pop("inconclusive_negatives")
        else:
            inconclusive = None
            results = _heldout_results(args) if args.mode == "heldout" else _proxy_results(args)
    except LabelError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    markdown = render_markdown(results)
    if inconclusive is not None:
        results["inconclusive_negatives"] = inconclusive
        markdown += (
            f"\nInconclusive negatives (control failed): {', '.join(inconclusive) or 'none'}"
        )
    if args.out:
        args.out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(markdown + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
