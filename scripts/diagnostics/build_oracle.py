"""Write the gold map of a dev set for the PROMPT 6 oracle ablation. Run on the host.

usage: python scripts/diagnostics/build_oracle.py \
           --set uat|natural|rbac|relevance|false_refusal|false_refusal_v2|compound --output <file>

Maps each question, as the runner asks it, to its gold: [{"document", "pages"|"facts"}].
UAT uses eval-data/uat/retrieval-gold.json (the document and page each reviewed answer cited,
checked against eval-data/uat/gold.lock); natural_dev_v1 the documents and pages of each item's
gold and acceptable citations (its locked gold); the other sets each answerable item's document
and fact (with its accepted forms). Items that must be refused have no gold. Dev sets only; no
held-out set is read.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import run_rbac_dev  # noqa: E402
from scripts.eval.grade_proxy import check_lock  # noqa: E402

SOURCES = {
    "rbac": "rbac_dev_v1",
    "relevance": "answer_relevance_dev_v1",
    "false_refusal": "false_refusal_dev_v1",
    "false_refusal_v2": "false_refusal_dev_v2",
    "compound": "compound_partial_dev_v1",
}


def uat_oracle(questions: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, list[dict]]:
    by_id = {item["id"]: item["question"] for item in questions["items"]}
    oracle = {}
    for case_id, pairs in gold["items"].items():
        pages: dict[str, list[int]] = defaultdict(list)
        for document, page in pairs:
            pages[document].append(page)
        oracle[by_id[case_id]] = [{"document": d, "pages": sorted(p)} for d, p in pages.items()]
    return oracle


def natural_oracle(questions: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, list[dict]]:
    by_id = {item["id"]: item["question"] for item in questions["items"]}
    oracle = {}
    for item in gold["items"]:
        pages: dict[str, set[int]] = defaultdict(set)
        for entry in (*item.get("gold_citations", ()), *item.get("acceptable_extra_citations", ())):
            pages[entry["document"]].update(entry["pages"])
        if pages:
            oracle[by_id[item["id"]]] = [
                {"document": d, "pages": sorted(p)} for d, p in sorted(pages.items())
            ]
    return oracle


def fact_oracle(data: Mapping[str, Any]) -> dict[str, list[dict]]:
    oracle = {}
    for item in data["items"]:
        # A half-answerable (partial) item's gold is the document and fact of its stated part.
        if item.get("expect", "answer") not in ("answer", "partial") or not item.get("fact"):
            continue
        facts = [item["fact"], *item.get("fact_alternatives", ())]
        for extra in item.get("also_facts", ()):
            facts += [extra["fact"], *extra.get("fact_alternatives", ())]
        oracle[item["question"]] = [{"document": item["document"], "facts": facts}]
    return oracle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=("uat", "natural", *SOURCES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.set == "uat":
        uat = ROOT / "eval-data" / "uat"
        check_lock(uat / "retrieval-gold.json")
        oracle = uat_oracle(
            json.loads((uat / "questions.json").read_text(encoding="utf-8")),
            json.loads((uat / "retrieval-gold.json").read_text(encoding="utf-8")),
        )
    elif args.set == "natural":
        import yaml

        from scripts.eval import natural_dev_check

        natural_dev_check.verify_gold()
        oracle = natural_oracle(
            yaml.safe_load(natural_dev_check.QUESTIONS.read_text(encoding="utf-8")),
            yaml.safe_load(natural_dev_check.GOLD.read_text(encoding="utf-8")),
        )
    else:
        source = ROOT / "tests" / "acceptance" / f"{SOURCES[args.set]}.yaml"
        oracle = fact_oracle(run_rbac_dev.load_set(source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(oracle, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"oracle {args.set}: {len(oracle)} questions with gold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
