"""Run a synthetic-document dev set against its own isolated stack.

usage (repo root, host venv, stack up):
  EVAL_PASSWORD_ADMIN=... EVAL_PASSWORD_STAFF=... \
  python scripts/eval/run_answer_relevance_dev.py --output <dir>/results.json [--setup-only]
      [--set answer_relevance_dev_v1|false_refusal_dev_v1]

answer_relevance_dev_v1 runs on eaka-relevance-dev. false_refusal_dev_v1 needs a stack of its own:
its documents must not join another set's corpus. An item's `fact_alternatives` are other accepted
forms of its `fact` ("07 ngày" / "7 ngày"); the answer must hold one of them.

Refuses to run unless the SHA256 of the set matches its lock. Builds PDFs from the set, uploads them
through the API and asks every question as staff. A `refuse` question passes on NO_ANSWER; an
`answer` question passes when it answers, cites the document and states the fact. Graded by proxy:
an honest "the documents do not say" that is returned as ANSWERED counts as a false answer here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import branch_counters, reranker_check, run_rbac_dev  # noqa: E402

SETS = (
    "answer_relevance_dev_v1",
    "false_refusal_dev_v1",
    "false_refusal_dev_v2",
    "compound_partial_dev_v1",
)
# DEC-021: the fixed sentence for a part of a two-part question that could not be verified.
UNVERIFIED_MARKER = "chưa xác minh được"
SOURCE = ROOT / "tests" / "acceptance" / "answer_relevance_dev_v1.yaml"
LOCK = ROOT / "tests" / "acceptance" / "answer_relevance_dev_v1.lock"
ROLE = "staff"
ANSWERED = "ANSWERED"


class SetChangedError(RuntimeError):
    """The set differs from the frozen hash, so its scores cannot be compared."""


def verify_frozen(source: Path = SOURCE, lock: Path = LOCK) -> dict[str, Any]:
    if not lock.is_file():
        raise SetChangedError(f"lock file missing: {lock}")
    expected = json.loads(lock.read_text(encoding="utf-8"))
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != expected["sha256"]:
        raise SetChangedError(f"{source.name} sha256 {actual} != frozen {expected['sha256']}")
    return expected


def states_fact(item: Mapping[str, Any], answer: str) -> bool:
    """The answer holds the item's fact or one of its accepted alternative forms.

    No digit may touch the form, so "1 lần" does not match "11 lần" nor "7 ngày" "17 ngày".
    Each of the item's `also_facts` (a question asking two things) must be there too.
    """
    folded = run_rbac_dev._fold(answer)
    return all(
        any(
            re.search(rf"(?<![\d.,]){re.escape(run_rbac_dev._fold(form))}(?!\d)", folded)
            for form in (fact["fact"], *fact.get("fact_alternatives", ()))
        )
        for fact in (item, *item.get("also_facts", ()))
    )


def grade_case(
    case: Mapping[str, Any], item: Mapping[str, Any], codes: Mapping[str, str]
) -> dict[str, Any]:
    cited = run_rbac_dev.cited_codes(case, codes)
    answered = case.get("status") == ANSWERED
    answer = case.get("answer") or ""
    says_unverified = run_rbac_dev._fold(UNVERIFIED_MARKER) in run_rbac_dev._fold(answer)
    if item["expect"] == "refuse":
        passed = case.get("status") == "NO_ANSWER"
    else:
        passed = answered and item["document"] in cited and states_fact(item, answer)
        if item["expect"] == "partial":  # one part stated, the other must be named unverified
            passed = passed and says_unverified
    return {
        "id": item["id"],
        "group": item["group"],
        "expect": item["expect"],
        "status": case.get("status"),
        "execution_status": case.get("execution_status"),
        "cited_codes": cited,
        "latency_ms": case.get("latency_ms"),
        "answer": case.get("answer"),
        "passed": passed,
        "false_answer": answered
        and (item["expect"] == "refuse" or (item["expect"] == "partial" and not says_unverified)),
    }


def summarize(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(cases)
    return {
        "false_answer": sorted(row["id"] for row in rows if row["false_answer"]),
        "correct": sorted(row["id"] for row in rows if row["passed"]),
        "lost_answers": sorted(
            row["id"] for row in rows if row["expect"] != "refuse" and not row["passed"]
        ),
        "infra_error": sorted(
            row["id"] for row in rows if row["execution_status"] == "INFRA_ERROR"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    reranker_check.add_arguments(parser)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--setup-only", action="store_true", help="upload documents, ask nothing")
    parser.add_argument("--set", choices=SETS, default=SETS[0], dest="set_name")
    args = parser.parse_args(argv)
    passwords = {}
    for role in ("admin", ROLE):
        value = os.environ.get(f"EVAL_PASSWORD_{role.upper()}")
        if not value:
            parser.error(f"set EVAL_PASSWORD_{role.upper()}")
        passwords[role] = value
    base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
    source = ROOT / "tests" / "acceptance" / f"{args.set_name}.yaml"
    try:
        lock = verify_frozen(source, source.with_suffix(".lock"))
        reranker = reranker_check.guard(args, base_url)
    except (SetChangedError, reranker_check.RerankerModeRefusedError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    data = run_rbac_dev.load_set(source)
    admin = run_rbac_dev._Admin(base_url, passwords["admin"])
    ids: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as folder:
        for document in data["documents"]:
            ids[document["code"]] = admin.ensure_document(
                document, Path(folder), "", version=data["version"]
            )
    if args.setup_only:
        print(f"documents ready: {sorted(ids)}")
        return 0
    codes = {document_id: code for code, document_id in ids.items()}
    ask = run_rbac_dev._asker(base_url, passwords)
    started_at = datetime.now(UTC).isoformat()
    counters_start = branch_counters.read(base_url)
    cases = [grade_case(ask(ROLE, item["question"]), item, codes) for item in data["items"]]
    payload = {
        "version": data["version"],
        "set_sha256": lock["sha256"],
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        **reranker,
        "branch_counters": branch_counters.delta(counters_start, branch_counters.read(base_url)),
        "summary": summarize(cases),
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"cases: {len(cases)}; false answers: {len(payload['summary']['false_answer'])}; "
        f"correct: {len(payload['summary']['correct'])}"
    )
    return reranker_check.finish(args.output, reranker, base_url, 0)


if __name__ == "__main__":
    raise SystemExit(main())
