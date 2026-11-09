"""Calibrate RAG_QUESTION_EVIDENCE_MIN_SIMILARITY (FIX 3a M1b) on the relevance-style dev sets.

usage: python scripts/eval/calibrate_question_evidence_similarity.py --out <file.json>
           [--sets answer_relevance_dev_v1 false_refusal_dev_v1] [--cache data/models]

Uses the app's e5 provider and the app's sentence split. For an item that must be answered,
the score is the cosine between the question and the best document sentence holding its fact
(the sentence a correct answer rests on). For an item that must be refused, it is the highest
cosine between the question and any sentence of the set's documents: the closest sentence a
wrong answer could copy. Proposed threshold: the highest value, rounded down to 0.01, that
keeps every answer item at or above it. Prints the counts on each side; reads no held-out set.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.embeddings.sentence_transformer_provider import (  # noqa: E402
    SentenceTransformerEmbeddingProvider,
)
from app.retrieval.question_analysis import fold_text  # noqa: E402
from scripts.eval import run_answer_relevance_dev, run_rbac_dev  # noqa: E402

SENTENCE_SPLIT = r"(?<=[.!?;])\s+|\n+"  # the split of supporting_sentence()


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(SENTENCE_SPLIT, text) if len(s.strip()) >= 8]


def threshold(answer_scores: list[float]) -> float:
    return int(min(answer_scores) * 100) / 100


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sets", nargs="+", default=list(run_answer_relevance_dev.SETS))
    parser.add_argument("--cache", default=str(ROOT / "data" / "models"))
    args = parser.parse_args()
    provider = SentenceTransformerEmbeddingProvider(
        model_name="intfloat/multilingual-e5-small",
        model_revision="",
        dimensions=384,
        device="cpu",
        batch_size=16,
        normalize=True,
        query_prefix="query: ",
        passage_prefix="passage: ",
        local_files_only=True,
        cache_folder=args.cache,
    )
    rows = []
    for name in args.sets:
        source = ROOT / "tests" / "acceptance" / f"{name}.yaml"
        run_answer_relevance_dev.verify_frozen(source, source.with_suffix(".lock"))
        data = run_rbac_dev.load_set(source)
        by_code = {d["code"]: sentences(d["text"]) for d in data["documents"]}
        every = [s for doc in by_code.values() for s in doc]
        vectors = dict(zip(every, provider.embed_passages(every).vectors, strict=True))
        for item in data["items"]:
            query = provider.embed_query(item["question"]).values
            if item["expect"] == "answer":
                facts = [item["fact"], *item.get("fact_alternatives", [])]
                pool = [
                    s
                    for s in by_code[item["document"]]
                    if any(fold_text(f) in fold_text(s) for f in facts)
                ]
            else:
                pool = every
            if not pool:
                raise SystemExit(f"{item['id']}: no sentence of {item['document']} holds its fact")
            score = max(
                sum(a * b for a, b in zip(query, vectors[s].values, strict=True)) for s in pool
            )
            rows.append({"set": name, "id": item["id"], "expect": item["expect"], "cosine": score})
    answers = [r["cosine"] for r in rows if r["expect"] == "answer"]
    refusals = [r["cosine"] for r in rows if r["expect"] == "refuse"]
    value = threshold(answers)
    summary = {
        "threshold": value,
        "answer": {"n": len(answers), "min": min(answers), "max": max(answers)},
        "refuse": {
            "n": len(refusals),
            "min": min(refusals),
            "max": max(refusals),
            "below_threshold": sum(s < value for s in refusals),
        },
        "rows": sorted(rows, key=lambda r: r["cosine"]),
    }
    args.out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("threshold", "answer", "refuse")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
