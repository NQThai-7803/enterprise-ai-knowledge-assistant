"""Diagnose a held-out v3.1 run without printing text: ids, counts, status codes, document codes and
right/wrong flags only (run 44575927833: legacy 0/16, s3t 3/16, identical runs).

usage (repo root, project venv; on the owner's machine):
  python scripts/eval/heldout_v3_diag.py table <decrypted dir>
  python scripts/eval/heldout_v3_diag.py access [--manifest uat/corpus-v2/manifest.json]

- table: one row per (configuration, run, item) from <dir>/<config>/run*/results.json (graded) and
  answers.json (raw), the folders of private-results.tar.gz.age, then the fail-reason counts.
  Columns: HTTP status, latency, answer route, answer status (ANSWERED / REFUSED / ERROR), chunks
  retrieved, citation count, cited codes, gold codes, "cites a gold document", "the grader found
  every gold value", fail reason codes. run_heldout.py records neither the answer route
  ("unrecorded") nor any evidence-gate or validator decision: the API response it keeps has none.
- access: for each item asked, its role, each gold document and whether that account may see it
  (corpus V2 manifest: visibility, owner, grants), and whether the document is DRAFT, which
  RAG_DRAFT_DOCUMENT_POLICY=exclude (the default) keeps out of retrieval and citations.
Every printed field is checked against a pattern and replaced by <redacted> when it does not fit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORPUS = ROOT / "uat" / "corpus-v2" / "manifest.json"
NAME = re.compile(r"[A-Za-z0-9_.:+-]{1,96}")  # one id, configuration, run, status, route, reason
CODE = re.compile(r"[A-Z0-9?][A-Z0-9?_.-]{0,63}")  # a document code, one of several
STATUS = {"ANSWERED": "ANSWERED", "NO_ANSWER": "REFUSED"}
COLUMNS = (
    "config", "run", "id", "http", "latency_ms", "route", "answer_status", "retrieved_count",
    "citations",
    "cited_codes", "gold_codes", "cites_gold", "values_found", "fail_reason",
)  # fmt: skip


def _safe(value: Any) -> str:
    """A field fit to print: a number, one name, or document codes; never free text."""
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "Y" if value else "N"
    if isinstance(value, int | float):
        return str(value)
    words = str(value).split()
    if not words:
        return "-"
    if len(words) == 1 and NAME.fullmatch(words[0]) or all(CODE.fullmatch(w) for w in words):
        return " ".join(words)
    return "<redacted>"


def fail_reasons(case: Mapping[str, Any]) -> list[str]:
    """Why the grader failed a case (heldout_v3_release.grade_case), as codes; [] when it passed."""
    if case.get("execution_status") not in (None, "OK"):
        return [str(case["execution_status"])]  # INFRA_ERROR, HTTP_ERROR
    answered = case.get("status") == "ANSWERED"
    if case.get("expect") == "refuse":
        return ["FALSE_ANSWER"] if answered else []
    if not answered:
        return ["REFUSED"]
    reasons = []
    if not case.get("cited_codes"):
        reasons.append("NO_CITATION")
    elif not set(case.get("expected_codes", [])) & set(case["cited_codes"]):
        reasons.append("NOT_GOLD_DOCUMENT")
        if case.get("other_source_same_values"):
            reasons.append("OTHER_SOURCE_SAME_VALUES")  # DEC-037 policy 1, the owner's call
    values = case.get("values") or {}
    if values.get("missing"):
        reasons.append(f"VALUES_MISSING_{len(values['missing'])}_OF_{len(values['required'])}")
    if values.get("conflicting"):
        reasons.append(f"VALUES_CONFLICTING_{len(values['conflicting'])}")
    if case.get("leak_reasons"):
        reasons.append("LEAK")
    if not reasons and not case.get("passed"):
        reasons.append("FAILED_OTHER")
    return reasons


def row(config: str, run: str, case: Mapping[str, Any], raw: Mapping[str, Any]) -> dict[str, str]:
    values = case.get("values")
    status = case.get("status")
    if case.get("execution_status") not in (None, "OK"):
        status = "ERROR"
    reasons = fail_reasons(case)
    return {
        "config": config,
        "run": run,
        "id": case["id"],
        "http": raw.get("http", "?"),
        "latency_ms": case.get("latency_ms"),
        "route": raw.get("answer_route") or "unrecorded",
        "answer_status": STATUS.get(status, status),
        "retrieved_count": raw.get("retrieved", "?"),
        "citations": len(raw["citations"]) if "citations" in raw else "?",
        "cited_codes": " ".join(case.get("cited_codes", [])),
        "gold_codes": " ".join(case.get("expected_codes", [])),
        "cites_gold": bool(set(case.get("expected_codes", [])) & set(case.get("cited_codes", []))),
        "values_found": None if values is None else not values.get("missing"),
        "fail_reason": "+".join(reasons) or "PASS",
    }


def table(folder: Path) -> list[dict[str, str]]:
    rows = []
    for path in sorted(folder.glob("*/run*/results.json")):
        config, run = path.parent.parent.name, path.parent.name
        answers = path.with_name("answers.json")
        raw = {}
        if answers.is_file():
            raw = {c["id"]: c for c in json.loads(answers.read_text(encoding="utf-8"))["cases"]}
        for case in json.loads(path.read_text(encoding="utf-8"))["cases"]:
            rows.append(row(config, run, case, raw.get(case["id"], {})))
    return rows


def access(manifest: Path = CORPUS) -> tuple[list[dict[str, Any]], list[str]]:
    """(id, role, gold code, may the account see it, is it DRAFT) per gold document of each item
    asked, and the ids not asked. Reads the frozen held-out file through the release gate."""
    from scripts.eval import heldout_v3_release, run_heldout

    asked, not_run, pending = heldout_v3_release.plan(heldout_v3_release.gate()["items"])
    docs = {d["code"]: d for d in json.loads(manifest.read_text(encoding="utf-8"))["documents"]}
    rows = []
    for item in asked:
        email = run_heldout.ACCOUNTS[item["role"]]
        codes = heldout_v3_release.expected_codes(item)
        if not codes:  # expects a refusal: no gold document
            rows.append({"id": item["id"], "role": item["role"], "gold_code": "NONE"})
        for code in codes:
            doc = docs.get(code)
            can_view: bool | str = "NOT_IN_CORPUS"
            if doc is not None:  # corpus V2 holds ORGANIZATION and PRIVATE documents only
                grants = {grant["user"] for grant in doc.get("required_grants", [])}
                can_view = doc["visibility"] == "ORGANIZATION" or email in grants | {doc["owner"]}
            rows.append(
                {
                    "id": item["id"],
                    "role": item["role"],
                    "gold_code": code,
                    "can_view": can_view,
                    "draft_excluded": doc and doc.get("lifecycle_status") == "DRAFT",
                }
            )
    return rows, sorted([*not_run, *pending])


def _markdown(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(_safe(r.get(c)) for c in columns) + " |" for r in rows]
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("table").add_argument("folder", type=Path)
    sub.add_parser("access").add_argument("--manifest", type=Path, default=CORPUS)
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.command == "table":
        rows = table(args.folder)
        if not rows:
            print(f"no */run*/results.json under {args.folder}", file=sys.stderr)
            return 2
        print("\n".join(_markdown(rows, COLUMNS)))
        counts = Counter((r["config"], r["run"], r["fail_reason"]) for r in rows)
        print("\n| config | run | fail_reason | items |\n|---|---|---|---|")
        for (config, run, reason), n in sorted(counts.items()):
            print(f"| {_safe(config)} | {_safe(run)} | {_safe(reason)} | {n} |")
        return 0
    rows, skipped = access(args.manifest)
    print("\n".join(_markdown(rows, ("id", "role", "gold_code", "can_view", "draft_excluded"))))
    print(f"\nnot asked: {_safe(' '.join(skipped))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
