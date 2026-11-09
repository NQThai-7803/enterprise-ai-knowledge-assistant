"""Write the input of heldout_trace.py for a frozen relevance-style dev set. Run on the host.

usage: python scripts/diagnostics/prepare_dev_trace_input.py \\
           --set false_refusal_dev_v1|answer_relevance_dev_v1 --output <file>
       python scripts/diagnostics/prepare_dev_trace_input.py \\
           --heldout-v1 HO-001 HO-004 ... --manifest <corpus V2 runtime manifest> --output <file>

Needs EVAL_PASSWORD_ADMIN and the stack the dev runner uses (RAG_ACCEPTANCE_BASE_URL); uploads
the set's documents only if they are missing, exactly as run_answer_relevance_dev.py does. The
gold chunk of an item is a chunk of its document holding its fact. The output holds question
text, so keep it out of the repository.

--heldout-v1 traces the named held-out v1 cases as a diagnostic (DEC-008), with their own role,
gold citations and source excerpts, on a stack loaded with corpus V2 (the manifest written by
bootstrap_corpus_v2.py gives the document ids). Held-out v2 is never read (DEC-012).
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


HELDOUT_V1 = ROOT / "docs" / "eval" / "heldout-v1.yaml"


def heldout_v1_items(items: list[Mapping[str, Any]], ids: list[str]) -> list[dict[str, Any]]:
    """heldout_trace.py items for the named held-out v1 cases, with their own role and gold."""
    by_id = {item["id"]: item for item in items}
    missing = [case_id for case_id in ids if case_id not in by_id]
    if missing:
        raise SystemExit(f"not in held-out v1: {missing}")
    return [
        {
            "id": case_id,
            "role": by_id[case_id]["role"],
            "group": by_id[case_id].get("group"),
            "gold_status": by_id[case_id]["gold_status"],
            "question": by_id[case_id]["question"],
            "gold_citations": by_id[case_id].get("gold_citations", []),
            "excerpts": by_id[case_id].get("source_excerpt", []),
        }
        for case_id in ids
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--set", choices=run_answer_relevance_dev.SETS)
    mode.add_argument("--heldout-v1", nargs="+", metavar="HO-NNN")
    parser.add_argument("--manifest", type=Path, help="corpus V2 runtime manifest (--heldout-v1)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.heldout_v1:
        if args.manifest is None:
            parser.error("--heldout-v1 needs --manifest")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        payload = {
            "codes": {doc["id"]: doc["code"] for doc in manifest["documents"]},
            "items": heldout_v1_items(run_rbac_dev.load_set(HELDOUT_V1)["items"], args.heldout_v1),
        }
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(payload['items'])} held-out v1 items")
        return 0
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
