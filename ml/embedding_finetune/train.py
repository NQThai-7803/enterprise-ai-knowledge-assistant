"""Fine-tune multilingual-e5-small with CachedMultipleNegativesRankingLoss on mined triples.

usage: python ml/embedding_finetune/train.py --triples triples.jsonl --chunks chunks.jsonl \\
           --out artifacts/embedding-finetune/model-<tag> [--epochs 1 --batch-size 128 --lr 2e-5]
           [--mini-batch-size 16 --max-pairs N --max-seq-length 256 --device cpu|cuda]
           [--fp16 | --no-fp16] [--gradient-checkpointing]

Refuses to start when any training question shares a word 4-gram with a protected question set
(DEC-015). Anchors get the "query: " prefix and passages "passage: ", as in the app. Each anchor
is trained against its positive, its first hard negative and the other passages of the batch.
`--batch-size` is the effective batch (the in-batch negatives); `--mini-batch-size` is what sits
in memory at once. On CUDA, fp16 is on by default; a non-finite loss under fp16 (GTX 16xx cards
can produce one) stops the run, which restarts from the base model in fp32 and records why.
Writes the model, plus training_config.json with the arguments, device, GPU, library versions
and the SHA256 of both input files and of the examples used. The output is never loaded by app/;
see docs/design/embedding-finetune.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.embedding_finetune import common

LIBRARIES = ("torch", "sentence-transformers", "transformers", "tokenizers", "numpy")


class NonFiniteLoss(RuntimeError):
    def __init__(self, epoch: int, step: int) -> None:
        super().__init__(f"non-finite loss at epoch {epoch} step {step}")
        self.epoch, self.step = epoch, step


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


def examples_sha256(data: list[tuple[str, str, str]]) -> str:
    """Hash of the exact examples trained on, in order (seeded shuffle, then --max-pairs)."""
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode("utf-8")).hexdigest()


def fit_with_fp16_fallback(attempt: Callable[[bool], Any], fp16: bool) -> tuple[Any, str | None]:
    """Run attempt(fp16). A non-finite loss under fp16 reruns it in fp32 and returns the reason."""
    try:
        return attempt(fp16), None
    except NonFiniteLoss as exc:
        if not fp16:
            raise
        reason = f"{exc} under fp16; restarted from the base model in fp32"
        print(reason, file=sys.stderr)
        return attempt(False), reason


def train(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.sentence_transformer.losses import (
        CachedMultipleNegativesRankingLoss,
    )
    from sentence_transformers.util import batch_to_device
    from transformers import set_seed

    triples = common.read_jsonl(args.triples)
    common.check_data_rule(row["query"] for row in triples)
    chunks = {chunk["chunk_id"]: chunk for chunk in common.read_jsonl(args.chunks)}
    data = examples(triples, chunks)
    random.Random(args.seed).shuffle(data)
    if args.max_pairs:
        data = data[: args.max_pairs]
    if len(data) < args.batch_size:
        raise SystemExit(f"only {len(data)} examples, fewer than one batch of {args.batch_size}")

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    fp16 = device == "cuda" if args.fp16 is None else args.fp16
    if fp16 and device != "cuda":
        raise SystemExit("--fp16 needs --device cuda")

    def attempt(use_fp16: bool) -> tuple[Any, list[float]]:
        set_seed(args.seed)  # python, numpy, torch and CUDA; the fp32 rerun starts identically
        rng = random.Random(args.seed)
        rows = list(data)  # shuffled per epoch; `data` keeps the order that examples_sha256 hashes
        model = SentenceTransformer(args.base, device=device)
        if model.get_embedding_dimension() != common.DIMENSIONS:
            raise SystemExit(f"{args.base} is not {common.DIMENSIONS}-dimensional")
        model.max_seq_length = args.max_seq_length
        if args.gradient_checkpointing:
            model.gradient_checkpointing_enable({"use_reentrant": False})
        if use_fp16:
            # The cached loss re-runs the forward inside backward, outside any `with autocast`
            # block, so autocast wraps the forward itself (as accelerate does).
            model.forward = torch.autocast(device_type="cuda", dtype=torch.float16)(model.forward)
        loss_fn = CachedMultipleNegativesRankingLoss(model, mini_batch_size=args.mini_batch_size)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
        scaler = torch.amp.GradScaler(device, enabled=use_fp16)
        model.train()
        losses_per_epoch = []
        for epoch in range(args.epochs):
            rng.shuffle(rows)
            total, steps = 0.0, 0
            for batch in common.iter_batches(rows, args.batch_size):
                if len(batch) < 2:  # in-batch negatives need at least two anchors
                    continue
                columns = list(zip(*batch, strict=True))
                features = [batch_to_device(model.tokenize(list(col)), device) for col in columns]
                loss = loss_fn(features, None)
                value = float(loss)
                if not math.isfinite(value):
                    raise NonFiniteLoss(epoch, steps)
                optimizer.zero_grad()
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                total += value
                steps += 1
            losses_per_epoch.append(round(total / max(steps, 1), 4))
        if use_fp16:
            del model.forward  # back to the class forward before saving
        return model, losses_per_epoch

    started = datetime.now(UTC).isoformat()
    try:
        (model, losses_per_epoch), fp16_fallback = fit_with_fp16_fallback(attempt, fp16)
    except torch.cuda.OutOfMemoryError as exc:
        raise SystemExit(
            f"CUDA out of memory with --mini-batch-size {args.mini_batch_size}: lower it "
            "(16, then 8) or add --gradient-checkpointing"
        ) from exc
    except NonFiniteLoss as exc:
        raise SystemExit(f"{exc} in fp32: check the data and --lr") from exc
    args.out.mkdir(parents=True, exist_ok=True)
    model.save(str(args.out))
    config = {
        "base_model": args.base,
        "dimensions": common.DIMENSIONS,
        "query_prefix": common.QUERY_PREFIX,
        "passage_prefix": common.PASSAGE_PREFIX,
        "loss": "CachedMultipleNegativesRankingLoss (positive + 1 hard negative + in-batch)",
        "examples": len(data),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "mini_batch_size": args.mini_batch_size,
        "lr": args.lr,
        "max_seq_length": model.max_seq_length,
        "seed": args.seed,
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "cuda": torch.version.cuda if device == "cuda" else None,
        "fp16": fp16 and fp16_fallback is None,
        "fp16_fallback": fp16_fallback,
        "gradient_checkpointing": args.gradient_checkpointing,
        "mean_loss_per_epoch": losses_per_epoch,
        "triples": str(args.triples),
        "triples_sha256": common.sha256_file(args.triples),
        "chunks_sha256": common.sha256_file(args.chunks),
        "examples_sha256": examples_sha256(data),
        "data_rule": "DEC-015 checked: no training query matches a protected question set",
        "versions": {"python": platform.python_version(), **{n: version(n) for n in LIBRARIES}},
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
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--mini-batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-pairs", type=int)
    parser.add_argument("--max-seq-length", type=int, default=256)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--fp16", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()
    try:
        config = train(args)
    except common.DataRuleError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    keys = ("examples", "device", "gpu", "fp16", "fp16_fallback", "mean_loss_per_epoch")
    print(json.dumps({k: config[k] for k in keys}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
