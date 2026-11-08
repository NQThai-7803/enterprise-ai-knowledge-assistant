"""Recall@1/5/10 and MRR@10 of embedding models on dev questions, by question form.

usage:
  python ml/embedding_finetune/eval_retrieval.py --chunks chunks.jsonl \\
      --models intfloat/multilingual-e5-small [artifacts/.../model-x ...] --out result.json
      [--english english.jsonl]   # optional: {"id": "Q001", "question": "..."} per line
  python ml/embedding_finetune/eval_retrieval.py --build-gold   # once, needs artifacts/

Questions: eval-data/uat/questions.json (UAT Q001-Q100, a dev set; never a held-out set). Gold:
eval-data/uat/retrieval-gold.json, the document and page each question's reviewed answer cited
(built from the manually reviewed grade in artifacts/). A gold chunk is a chunk of that document
that covers that page. Forms: "vi" as written, "vi_unaccented" with every diacritic removed, and
"en" when --english is given. Retrieval here is the embedding alone (exact cosine over all
chunks, "query: "/"passage: " prefixes), to compare models; it is not the app's hybrid ranking.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.embedding_finetune import common

QUESTIONS = common.ROOT / "eval-data" / "uat" / "questions.json"
GOLD = common.ROOT / "eval-data" / "uat" / "retrieval-gold.json"
GRADE = (
    common.ROOT / "artifacts" / "task-035-3b-20261013" / "case-level-semantic-citation-grade.json"
)
V2_RUNTIME = common.ROOT / "artifacts" / "uat-corpus-v2" / "runtime-manifest.json"
KS = (1, 5, 10)


def build_gold(grade: Path = GRADE, runtime: Path = V2_RUNTIME) -> dict[str, Any]:
    codes = {
        doc["id"]: doc["code"]
        for doc in json.loads(runtime.read_text(encoding="utf-8-sig"))["documents"]
    }
    gold: dict[str, Any] = {}
    for case in json.loads(grade.read_text(encoding="utf-8"))["cases"]:
        if case["applicability"] != "SUPPORTED_BY_V2" or not case.get("citation_ids"):
            continue
        gold[case["id"]] = sorted(
            {(codes[c["document_id"]], c["page_number"]) for c in case["citation_ids"]}
        )
    return {
        "source": "artifacts/task-035-3b-20261013/case-level-semantic-citation-grade.json",
        "rule": "SUPPORTED_BY_V2 cases; each [document_code, page] a reviewed answer cited",
        "items": {case_id: [list(pair) for pair in pairs] for case_id, pairs in gold.items()},
    }


def gold_chunks(pairs: Sequence[Sequence[Any]], chunks: Sequence[Mapping[str, Any]]) -> set[str]:
    wanted = {(code, int(page)) for code, page in pairs}
    return {
        chunk["chunk_id"]
        for chunk in chunks
        if any((chunk["document_code"], page) in wanted for page in chunk["page_numbers"])
    }


def score(ranked: Sequence[Sequence[str]], gold: Sequence[set[str]]) -> dict[str, float]:
    """Recall@k (any gold chunk in the top k) and MRR@10 over aligned query lists."""
    n = len(ranked)
    result: dict[str, float] = {"n": n}
    for k in KS:
        result[f"recall@{k}"] = (
            round(sum(bool(set(r[:k]) & g) for r, g in zip(ranked, gold, strict=True)) / n, 4)
            if n
            else 0.0
        )
    rr = []
    for r, g in zip(ranked, gold, strict=True):
        rank = next((i for i, chunk_id in enumerate(r[:10], start=1) if chunk_id in g), None)
        rr.append(1 / rank if rank else 0.0)
    result["mrr@10"] = round(sum(rr) / n, 4) if n else 0.0
    return result


def ranker(model_name: str, chunks: list[dict[str, Any]]) -> Any:
    """Load a model, encode every chunk once, and return a function ranking query lists."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device="cpu")
    passages = model.encode(
        [common.PASSAGE_PREFIX + c["text"] for c in chunks],
        normalize_embeddings=True,
        batch_size=16,
    )

    def rank(queries: list[str]) -> list[list[str]]:
        asked = model.encode(
            [common.QUERY_PREFIX + q for q in queries], normalize_embeddings=True, batch_size=32
        )
        order = (asked @ passages.T).argsort(axis=1)[:, ::-1][:, :10]
        return [[chunks[i]["chunk_id"] for i in row] for row in order]

    return rank


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-gold", action="store_true")
    parser.add_argument("--chunks", type=Path)
    parser.add_argument("--models", nargs="+", default=[common.BASE_MODEL])
    parser.add_argument("--english", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.build_gold:
        payload = build_gold()
        text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
        GOLD.write_text(text, encoding="utf-8", newline="\n")
        print(f"{len(payload['items'])} questions with gold -> {GOLD}")
        return 0
    if not args.chunks or not args.out:
        parser.error("--chunks and --out are required")
    chunks = common.read_jsonl(args.chunks)
    gold_items = json.loads(GOLD.read_text(encoding="utf-8"))["items"]
    questions = {
        item["id"]: item["question"]
        for item in json.loads(QUESTIONS.read_text(encoding="utf-8"))["items"]
    }
    ids = [case_id for case_id in questions if gold_chunks(gold_items.get(case_id, []), chunks)]
    gold = [gold_chunks(gold_items[case_id], chunks) for case_id in ids]
    forms = {
        "vi": [questions[i] for i in ids],
        "vi_unaccented": [common.unaccent(questions[i]) for i in ids],
    }
    if args.english:
        english = {row["id"]: row["question"] for row in common.read_jsonl(args.english)}
        forms["en"] = [english[i] for i in ids if i in english]
    results: dict[str, Any] = {
        "questions": len(ids),
        "skipped_without_gold_chunk": len(questions) - len(ids),
        "chunks": len(chunks),
        "chunks_sha256": common.sha256_file(args.chunks),
        "models": {},
    }
    for model_name in args.models:
        rank = ranker(model_name, chunks)
        per_form = {}
        for form, queries in forms.items():
            form_gold = (
                gold
                if form != "en"
                else [g for i, g in zip(ids, gold, strict=True) if i in english]
            )
            per_form[form] = score(rank(queries), form_gold)
        results["models"][model_name] = per_form
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for model_name, per_form in results["models"].items():
        for form, metrics in per_form.items():
            print(model_name, form, json.dumps(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
