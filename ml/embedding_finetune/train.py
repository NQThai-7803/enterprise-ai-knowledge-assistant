"""Fine-tune multilingual-e5-small with MultipleNegativesRankingLoss on mined triples.

usage: python ml/embedding_finetune/train.py --triples triples.jsonl --chunks chunks.jsonl \\
           --out artifacts/embedding-finetune/model-<tag> [--epochs 1 --batch-size 16 --lr 2e-5]
           [--max-pairs N --max-seq-length 256 --device cpu|cuda]

Refuses to start when any training question shares a word 4-gram with a protected question set
(DEC-015). Anchors get the "query: " prefix and passages "passage: ", as in the app. Each anchor
is trained against its positive, its first hard negative and the other passages of the batch.
Writes the model, plus training_config.json with the arguments, library versions and the SHA256
of both input files. The output is never loaded by app/; see docs/design/embedding-finetune.md.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.embedding_finetune import common


def examples(
    triples: list[dict[str, Any]], chunks: dict[str, dict[str, Any]]
) -> list[tuple[str, str, str]]:
    """(anchor, positive, negative) texts with e5 prefixes; rows with no negative are left out."""
    out = []
    for row in triples:
        if not row.get("negative_chunk_ids"):
            continue
        out.append(
            (
                common.QUERY_PREFIX + row["query"],
                common.PASSAGE_PREFIX + chunks[row["positive_chunk_id"]]["text"],
                common.PASSAGE_PREFIX + chunks[row["negative_chunk_ids"][0]]["text"],
            )
        )
    return out


def train(args: argparse.Namespace) -> dict[str, Any]:
    import sentence_transformers
    import torch
    from sentence_transformers import SentenceTransformer, losses
    from sentence_transformers.util import batch_to_device

    triples = common.read_jsonl(args.triples)
    common.check_data_rule(row["query"] for row in triples)
    chunks = {chunk["chunk_id"]: chunk for chunk in common.read_jsonl(args.chunks)}
    rng = random.Random(args.seed)
    data = examples(triples, chunks)
    rng.shuffle(data)
    if args.max_pairs:
        data = data[: args.max_pairs]
    if len(data) < args.batch_size:
        raise SystemExit(f"only {len(data)} examples, fewer than one batch of {args.batch_size}")

    torch.manual_seed(args.seed)
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = SentenceTransformer(args.base, device=device)
    if model.get_sentence_embedding_dimension() != common.DIMENSIONS:
        raise SystemExit(f"{args.base} is not {common.DIMENSIONS}-dimensional")
    if args.max_seq_length:
        model.max_seq_length = args.max_seq_length
    loss_fn = losses.MultipleNegativesRankingLoss(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    model.train()
    losses_per_epoch = []
    started = datetime.now(UTC).isoformat()
    for _ in range(args.epochs):
        rng.shuffle(data)
        total, steps = 0.0, 0
        for batch in common.iter_batches(data, args.batch_size):
            if len(batch) < 2:  # in-batch negatives need at least two anchors
                continue
            columns = list(zip(*batch, strict=True))
            features = [batch_to_device(model.tokenize(list(col)), device) for col in columns]
            loss = loss_fn(features, None)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss)
            steps += 1
        losses_per_epoch.append(round(total / max(steps, 1), 4))
    args.out.mkdir(parents=True, exist_ok=True)
    model.save(str(args.out))
    config = {
        "base_model": args.base,
        "dimensions": common.DIMENSIONS,
        "query_prefix": common.QUERY_PREFIX,
        "passage_prefix": common.PASSAGE_PREFIX,
        "loss": "MultipleNegativesRankingLoss (positive + 1 hard negative + in-batch)",
        "examples": len(data),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "max_seq_length": model.max_seq_length,
        "seed": args.seed,
        "device": device,
        "mean_loss_per_epoch": losses_per_epoch,
        "triples": str(args.triples),
        "triples_sha256": common.sha256_file(args.triples),
        "chunks_sha256": common.sha256_file(args.chunks),
        "data_rule": "DEC-015 checked: no training query matches a protected question set",
        "versions": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "sentence_transformers": sentence_transformers.__version__,
        },
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    (args.out / "training_config.json").write_text(
        json.dumps(config, indent=1) + "\n", encoding="utf-8"
    )
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triples", type=Path, required=True)
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base", default=common.BASE_MODEL)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-pairs", type=int)
    parser.add_argument("--max-seq-length", type=int)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()
    try:
        config = train(args)
    except common.DataRuleError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: config[k] for k in ("examples", "device", "mean_loss_per_epoch")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
