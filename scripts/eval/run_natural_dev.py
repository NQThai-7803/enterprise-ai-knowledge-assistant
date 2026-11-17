"""Ask natural_dev_v1 (owner-written questions over corpus V2) as its role and grade it by proxy.

usage (repo root, eval stack up with corpus V2 loaded):
  EVAL_PASSWORD_STAFF=... python scripts/eval/run_natural_dev.py \
      --manifest <runtime-manifest.json> --output <dir>/results.json

Refuses unless the questions match natural_dev_v1.lock, the gold matches the owner's
natural_dev_v1_gold.lock and the proxy keys (natural_dev_v1_proxy.yaml) name that gold. One
session per item; an INFRA_ERROR is retried once (run_heldout.run). The raw answers go to
answers.json beside the output.

Proxy grade per item (the keys are explained in the proxy file):
- leak: a citation of a document the role may not see, or a forbidden value in the answer or a
  citation;
- an ANSWERED item passes when it answers, cites a gold or acceptable document, states every fact
  group and hits no `wrong` form;
- an ANSWERED_LIMITED item passes the same way and must also say what the documents do not state;
  answered without that, it is a false answer (an over-claim), or wrong when a `wrong` form shows.
The categories are then those of the other dev sets (scripts/diagnostics/summarize_ablation.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import (  # noqa: E402
    branch_counters,
    heldout_check,
    heldout_v2_check,
    natural_dev_check,
    reranker_check,
    run_heldout,
    run_rbac_dev,
)

PROXY = natural_dev_check.SET_DIR / "natural_dev_v1_proxy.yaml"
LIMITED = "ANSWERED_LIMITED"


class NaturalRefusedError(RuntimeError):
    """The questions, gold or proxy keys do not hold, so the run may not start."""


def verified_inputs(
    questions: Path = natural_dev_check.QUESTIONS,
    questions_lock: Path = natural_dev_check.LOCK,
    gold: Path = natural_dev_check.GOLD,
    gold_lock: Path = natural_dev_check.GOLD_LOCK,
    proxy: Path = PROXY,
) -> dict[str, Any]:
    """The frozen questions, the approved gold items and the proxy keys, all checked."""
    try:
        frozen = heldout_v2_check.verify_frozen(questions, questions_lock)
        gold_lock_data = natural_dev_check.verify_gold(gold, gold_lock)
    except (heldout_v2_check.FrozenSetChangedError, natural_dev_check.GoldNotLockedError) as exc:
        raise NaturalRefusedError(str(exc)) from exc
    keys = heldout_v2_check._yaml(proxy)
    if keys.get("gold_sha256") != gold_lock_data["sha256"]:
        raise NaturalRefusedError("the proxy keys were written for another gold")
    items = heldout_v2_check._yaml(gold)["items"]
    if sorted(keys["items"]) != sorted(item["id"] for item in items):
        raise NaturalRefusedError("the proxy keys do not cover exactly the gold items")
    return {
        "frozen": frozen,
        "gold_lock": gold_lock_data,
        "proxy_sha256": hashlib.sha256(proxy.read_bytes()).hexdigest(),
        "items": items,
        "keys": keys,
    }


def _says(form: str, folded: str) -> bool:
    """The folded answer holds the form with no digit touching it."""
    pattern = re.escape(run_rbac_dev._fold(form))
    return re.search(rf"(?<![\d.,]){pattern}(?!\d)", folded) is not None


def grade_case(
    case: Mapping[str, Any],
    item: Mapping[str, Any],
    keys: Mapping[str, Any],
    limit_forms: Sequence[str],
    codes: Mapping[str, str],
) -> dict[str, Any]:
    cited = run_rbac_dev.cited_codes(case, codes)
    answer = case.get("answer") or ""
    folded = run_rbac_dev._fold(answer)
    answered = case.get("status") == "ANSWERED"
    limited = item["gold_status"] == LIMITED
    surface = run_rbac_dev._fold(
        " ".join(
            [answer]
            + [
                str(c.get(k) or "")
                for c in case.get("citations", [])
                for k in ("excerpt", "evidence_text")
            ]
        )
    )
    leak_reasons = []
    if heldout_check.VISIBLE.get(item["role"]) != "all":  # staff sees ORGANIZATION documents
        leak_reasons += [f"cites {code}" for code in cited if code in heldout_check.RESTRICTED]
    leak_reasons += [
        f"forbidden value of {entry['document']}"
        for entry in item.get("forbidden", [])
        if run_rbac_dev._fold(entry["value"]) in surface
    ]
    allowed = {c["document"] for c in item.get("gold_citations", [])} | {
        c["document"] for c in item.get("acceptable_extra_citations", [])
    }
    facts = all(any(_says(f, folded) for f in group) for group in keys.get("facts", []))
    wrong_hit = any(_says(f, folded) for f in keys.get("wrong", []))
    limit_said = any(_says(f, folded) for f in (*keys.get("limits", []), *limit_forms))
    cites_gold = bool(allowed & set(cited))
    if limited:
        passed = answered and cites_gold and facts and limit_said
        false_answer = answered and not limit_said and not wrong_hit
    else:
        passed = answered and cites_gold and facts and not wrong_hit
        false_answer = False
    return {
        "id": item["id"],
        "group": item.get("near_uat_group"),
        "gold_status": item["gold_status"],
        "expect": "partial" if limited else "answer",
        "status": case.get("status"),
        "execution_status": case.get("execution_status"),
        "cited_codes": cited,
        "latency_ms": case.get("latency_ms"),
        "answer": case.get("answer"),
        "passed": bool(passed),
        "false_answer": bool(false_answer),
        "leak_reasons": leak_reasons,
        "proxy": {
            "facts": facts,
            "wrong_hit": wrong_hit,
            "limit_said": limit_said,
            "cites_gold": cites_gold,
        },
    }


def summarize(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(cases)
    return {
        "correct": sorted(r["id"] for r in rows if r["passed"]),
        "false_answer": sorted(r["id"] for r in rows if r["false_answer"]),
        "lost_answers": sorted(r["id"] for r in rows if not r["passed"]),
        "leaks": sorted(r["id"] for r in rows if r["leak_reasons"]),
        "infra_error": sorted(r["id"] for r in rows if r["execution_status"] == "INFRA_ERROR"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    reranker_check.add_arguments(parser)
    parser.add_argument("--manifest", type=Path, required=True, help="runtime-manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
    try:
        inputs = verified_inputs()
        roles = {item["role"] for item in inputs["items"]}
        missing = [r for r in roles if not os.environ.get(f"EVAL_PASSWORD_{r.upper()}")]
        if missing:
            raise NaturalRefusedError(
                "set " + ", ".join(f"EVAL_PASSWORD_{r.upper()}" for r in missing)
            )
        reranker = reranker_check.guard(args, base_url)
    except (NaturalRefusedError, reranker_check.RerankerModeRefusedError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    codes = {
        d["id"]: d["code"]
        for d in json.loads(args.manifest.read_text(encoding="utf-8"))["documents"]
    }
    passwords = {r: os.environ[f"EVAL_PASSWORD_{r.upper()}"] for r in roles}
    answers = args.output.with_name("answers.json")
    started_at = datetime.now(UTC).isoformat()
    counters_start = branch_counters.read(base_url)
    code = run_heldout.run(
        output=answers,
        selected=set(),
        resume=False,
        base_url=base_url,
        passwords=passwords,
        frozen=inputs["frozen"],
        all_items=inputs["items"],
        label="natural-dev-v1",
    )
    raw = {c["id"]: c for c in json.loads(answers.read_text(encoding="utf-8"))["cases"]}
    keys = inputs["keys"]
    cases = [
        grade_case(raw[item["id"]], item, keys["items"][item["id"]], keys["limit_forms"], codes)
        for item in inputs["items"]
    ]
    payload = {
        "version": "natural_dev_v1",
        "set_sha256": inputs["frozen"]["sha256"],
        "gold_sha256": inputs["gold_lock"]["sha256"],
        "proxy_sha256": inputs["proxy_sha256"],
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        **reranker,
        "branch_counters": branch_counters.delta(counters_start, branch_counters.read(base_url)),
        "summary": summarize(cases),
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = payload["summary"]
    print(
        f"cases: {len(cases)}; false answers: {len(summary['false_answer'])}; "
        f"correct: {len(summary['correct'])}; leaks: {len(summary['leaks'])}"
    )
    return reranker_check.finish(args.output, reranker, base_url, code)


if __name__ == "__main__":
    raise SystemExit(main())
