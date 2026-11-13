"""Write the gold map of a dev set for the PROMPT 6 oracle ablation. Run on the host.

usage: python scripts/diagnostics/build_oracle.py \
           --set uat|rbac|relevance|false_refusal|false_refusal_v2 --output <file>

Maps each question, as the runner asks it, to its gold: [{"document", "pages"|"facts"}].
UAT uses eval-data/uat/retrieval-gold.json (the document and page each reviewed answer cited);
the other sets use each answerable item's document and fact (with its accepted forms). Items
that must be refused have no gold. Dev sets only; no held-out set is read.
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

SOURCES = {
    "rbac": "rbac_dev_v1",
    "relevance": "answer_relevance_dev_v1",
    "false_refusal": "false_refusal_dev_v1",
    "false_refusal_v2": "false_refusal_dev_v2",
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


def fact_oracle(data: Mapping[str, Any]) -> dict[str, list[dict]]:
    oracle = {}
    for item in data["items"]:
        if item.get("expect", "answer") != "answer" or not item.get("fact"):
            continue
        facts = [item["fact"], *item.get("fact_alternatives", ())]
        for extra in item.get("also_facts", ()):
            facts += [extra["fact"], *extra.get("fact_alternatives", ())]
        oracle[item["question"]] = [{"document": item["document"], "facts": facts}]
    return oracle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=("uat", *SOURCES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.set == "uat":
        uat = ROOT / "eval-data" / "uat"
        oracle = uat_oracle(
            json.loads((uat / "questions.json").read_text(encoding="utf-8")),
            json.loads((uat / "retrieval-gold.json").read_text(encoding="utf-8")),
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
