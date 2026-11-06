"""Run the answer relevance dev set against the isolated stack eaka-relevance-dev.

usage (repo root, host venv, stack up):
  EVAL_PASSWORD_ADMIN=... EVAL_PASSWORD_STAFF=... \
  python scripts/eval/run_answer_relevance_dev.py --output <dir>/results.json [--setup-only]

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


def grade_case(
    case: Mapping[str, Any], item: Mapping[str, Any], codes: Mapping[str, str]
) -> dict[str, Any]:
    cited = run_rbac_dev.cited_codes(case, codes)
    answered = case.get("status") == ANSWERED
    if item["expect"] == "refuse":
        passed = case.get("status") == "NO_ANSWER"
    else:
        passed = (
            answered
            and item["document"] in cited
            and run_rbac_dev._fold(item["fact"]) in run_rbac_dev._fold(case.get("answer") or "")
        )
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
        "false_answer": item["expect"] == "refuse" and answered,
    }


def summarize(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(cases)
    return {
        "false_answer": sorted(row["id"] for row in rows if row["false_answer"]),
        "correct": sorted(row["id"] for row in rows if row["passed"]),
        "lost_answers": sorted(
            row["id"] for row in rows if row["expect"] == "answer" and not row["passed"]
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
    args = parser.parse_args(argv)
    passwords = {}
    for role in ("admin", ROLE):
        value = os.environ.get(f"EVAL_PASSWORD_{role.upper()}")
        if not value:
            parser.error(f"set EVAL_PASSWORD_{role.upper()}")
        passwords[role] = value
    base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
    try:
        lock = verify_frozen()
        reranker = reranker_check.guard(args, base_url)
    except (SetChangedError, reranker_check.RerankerModeRefusedError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    data = run_rbac_dev.load_set(SOURCE)
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
