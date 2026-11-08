"""Mine hard negatives with the app's current hybrid retrieval, inside the eval stack.

usage (repo root, eval stack with corpus V2 up):
  python ml/embedding_finetune/mine_negatives.py --container eaka-p3d-uat-api-1 \\
      --queries augmented.jsonl --chunks chunks.jsonl --out triples.jsonl [--top-k 20 --per-query 3]

For each question (every form), the hybrid retrieval of the running API ranks chunks as the admin
account. A negative is a ranked chunk that is not the positive, has a different text, and is not
next to the positive in the same document (overlapping chunks can hold the same answer). Rows
with no negative keep an empty list; train.py then relies on in-batch negatives for them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.embedding_finetune import common


def pick_negatives(
    ranked: list[str], positive: str, chunks: dict[str, dict[str, Any]], limit: int
) -> list[str]:
    pos = chunks[positive]
    out = []
    for chunk_id in ranked:
        chunk = chunks.get(chunk_id)
        if chunk is None or chunk_id == positive or chunk["text"] == pos["text"]:
            continue
        same_doc = chunk["document_code"] == pos["document_code"]
        if same_doc and abs(chunk["chunk_index"] - pos["chunk_index"]) <= 1:
            continue
        out.append(chunk_id)
        if len(out) == limit:
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--account", default="admin.uat@example.test")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--per-query", type=int, default=3)
    parser.add_argument("--batch", type=int, default=50, help="queries per container call")
    args = parser.parse_args()
    rows = common.read_jsonl(args.queries)
    chunks = {chunk["chunk_id"]: chunk for chunk in common.read_jsonl(args.chunks)}
    missing = {row["positive_chunk_id"] for row in rows} - set(chunks)
    if missing:
        print(f"REFUSED: {len(missing)} positives not in {args.chunks}", file=sys.stderr)
        return 2
    ranked: dict[str, list[str]] = {}
    texts = list(dict.fromkeys(row["query"] for row in rows))
    for batch in common.iter_batches(texts, args.batch):
        payload = {"account": args.account, "queries": batch, "top_k": args.top_k}
        for result in common.run_in_container(args.container, "retrieve", payload):
            ranked[result["query"]] = result["chunk_ids"]
    out = []
    positive_rank_hits = 0
    for row in rows:
        order = ranked[row["query"]]
        positive_rank_hits += row["positive_chunk_id"] in order[:10]
        negatives = pick_negatives(order, row["positive_chunk_id"], chunks, args.per_query)
        out.append({**row, "negative_chunk_ids": negatives})
    common.write_jsonl(args.out, out)
    print(
        json.dumps(
            {
                "rows": len(out),
                "with_negatives": sum(bool(row["negative_chunk_ids"]) for row in out),
                "positive_in_hybrid_top10": positive_rank_hits,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
