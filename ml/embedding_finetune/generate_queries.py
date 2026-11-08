"""Generate 3-5 synthetic questions per chunk of corpus V2 with the local Ollama model.

usage (repo root, eval stack with corpus V2 up, Ollama up):
  python ml/embedding_finetune/generate_queries.py --container eaka-p3d-uat-api-1 \\
      --chunks-out artifacts/embedding-finetune/chunks.jsonl \\
      --out artifacts/embedding-finetune/queries.jsonl [--limit 10]
  python ml/embedding_finetune/generate_queries.py --chunks artifacts/.../chunks.jsonl --out ...

Writes one row per question: query_id, query, positive_chunk_id (the chunk it was written from),
document_code, form "vi", model and seed. Questions that share a word 4-gram with any protected
question set (DEC-015) are dropped and counted, never written. The chunk text is passed to the
model as data in the user message.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.embedding_finetune import common

SYSTEM = (
    "Bạn viết câu hỏi tiếng Việt để kiểm tra hệ thống tìm kiếm tài liệu nội bộ. "
    "Chỉ dùng thông tin trong đoạn văn được cung cấp. Mỗi câu hỏi phải trả lời được "
    "bằng đoạn văn đó, tự nhiên như nhân viên hỏi, không chép nguyên câu trong đoạn văn. "
    'Trả về JSON dạng {"questions": ["...", "..."]}.'
)


def prompt(text: str, count: int) -> list[dict[str, str]]:
    user = (
        f"Viết đúng {count} câu hỏi khác nhau cho đoạn văn sau.\n\n<doan_van>\n{text}\n</doan_van>"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_questions(content: str) -> list[str]:
    """Questions from the model's JSON reply; anything malformed yields none."""
    try:
        questions = json.loads(content).get("questions", [])
    except (ValueError, AttributeError):
        return []
    seen: dict[str, None] = {}
    for question in questions:
        if isinstance(question, str) and len(question.split()) >= 4:
            seen.setdefault(" ".join(question.split()), None)
    return list(seen)


def generate(
    chunks: list[dict[str, Any]], *, model: str, base_url: str, seed: int
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    stats = {"chunks": 0, "generated": 0, "dropped_protected": 0, "empty_chunks": 0}
    for chunk in chunks:
        stats["chunks"] += 1
        count = rng.randint(3, 5)
        reply = common.ollama_chat(
            prompt(chunk["text"], count), model=model, base_url=base_url, seed=seed, temperature=0.7
        )
        questions = parse_questions(reply)[:count]
        if not questions:
            stats["empty_chunks"] += 1
        protected = {query for query, _, _ in common.protected_hits(questions)}
        stats["dropped_protected"] += len(protected)
        for number, question in enumerate(q for q in questions if q not in protected):
            stats["generated"] += 1
            rows.append(
                {
                    "query_id": f"{chunk['chunk_id']}:{number}",
                    "query": question,
                    "positive_chunk_id": chunk["chunk_id"],
                    "document_code": chunk["document_code"],
                    "form": "vi",
                    "model": model,
                    "seed": seed,
                }
            )
    return rows, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--container", help="API container of a stack holding corpus V2")
    source.add_argument("--chunks", type=Path, help="chunks.jsonl exported earlier")
    parser.add_argument("--chunks-out", type=Path, help="with --container: where to save chunks")
    parser.add_argument("--account", default="admin.uat@example.test")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, help="only the first N chunks (smoke runs)")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--ollama", default="http://127.0.0.1:11434")
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()
    if args.container:
        chunks = common.run_in_container(args.container, "chunks", {"account": args.account})
        if args.chunks_out:
            common.write_jsonl(args.chunks_out, chunks)
    else:
        chunks = common.read_jsonl(args.chunks)
    if not chunks:
        print("REFUSED: no chunks; is corpus V2 loaded?", file=sys.stderr)
        return 2
    selected = chunks[: args.limit] if args.limit else chunks
    rows, stats = generate(selected, model=args.model, base_url=args.ollama, seed=args.seed)
    common.write_jsonl(args.out, rows)
    print(json.dumps({**stats, "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
