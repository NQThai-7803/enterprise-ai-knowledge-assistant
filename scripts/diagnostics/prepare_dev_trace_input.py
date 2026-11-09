"""Write the input of heldout_trace.py for a frozen relevance-style dev set. Run on the host.

usage: python scripts/diagnostics/prepare_dev_trace_input.py \\
           --set false_refusal_dev_v1|answer_relevance_dev_v1 --output <file>

Needs EVAL_PASSWORD_ADMIN and the stack the dev runner uses (RAG_ACCEPTANCE_BASE_URL); uploads
the set's documents only if they are missing, exactly as run_answer_relevance_dev.py does. The
gold chunk of an item is a chunk of its document holding its fact. The output holds question
text, so keep it out of the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import run_answer_relevance_dev, run_rbac_dev  # noqa: E402

ALL_PAGES = list(range(1, 100))  # shortcut: the set's documents are a few pages; widen if one grows


def trace_items(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """heldout_trace.py items: the runner's role, and the fact as the gold excerpt."""
    items = []
    for item in data["items"]:
        document = item.get("document") if item.get("fact") else None  # refuse items have neither
        items.append(
            {
                "id": item["id"],
                "role": run_answer_relevance_dev.ROLE,
                "group": item.get("group"),
                "gold_status": item["expect"],
                "question": item["question"],
                "excerpts": [{"document": document, "text": item["fact"]}] if document else [],
                "gold_citations": [{"document": document, "pages": ALL_PAGES}] if document else [],
            }
        )
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=run_answer_relevance_dev.SETS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / "tests" / "acceptance" / f"{args.set}.yaml"
    run_answer_relevance_dev.verify_frozen(source, source.with_suffix(".lock"))
    data = run_rbac_dev.load_set(source)
    base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
    admin = run_rbac_dev._Admin(base_url, os.environ["EVAL_PASSWORD_ADMIN"])
    with tempfile.TemporaryDirectory() as folder:
        codes = {
            admin.ensure_document(document, Path(folder), "", version=data["version"]): document[
                "code"
            ]
            for document in data["documents"]
        }
    args.output.write_text(
        json.dumps({"codes": codes, "items": trace_items(data)}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{len(data['items'])} items, documents {sorted(codes.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
