"""Add question variants: no diacritics, some diacritics, a light typo, and (optional) English.

usage: python ml/embedding_finetune/augment.py --queries queries.jsonl --out augmented.jsonl
           [--english --ollama http://127.0.0.1:11434]

Keeps every original row (form "vi") and adds, per question:
  vi_unaccented  every diacritic removed ("Nghỉ phép" -> "Nghi phep")
  vi_partial     diacritics removed from about half of the words
  vi_typo        one word with two inner letters swapped or one letter dropped
  en             an English translation by the local model (only with --english)
Variants keep the positive chunk of their original. Randomness is seeded per query id, so a
rerun gives the same file. English variants go through the DEC-015 check like the rest.
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

TRANSLATE = (
    "Translate the user's Vietnamese question into natural English. "
    'Keep names and numbers. Reply as JSON {"english": "..."}.'
)


def _rng(seed: int, query_id: str, form: str) -> random.Random:
    return random.Random(f"{seed}:{query_id}:{form}")


def partial_unaccent(text: str, rng: random.Random) -> str:
    words = text.split(" ")
    accented = [i for i, word in enumerate(words) if common.unaccent(word) != word]
    for index in rng.sample(accented, k=len(accented) // 2) if len(accented) > 1 else []:
        words[index] = common.unaccent(words[index])
    return " ".join(words)


def typo(text: str, rng: random.Random) -> str:
    words = text.split(" ")
    candidates = [i for i, word in enumerate(words) if len(word) >= 4 and word.isalpha()]
    if not candidates:
        return text
    index = rng.choice(candidates)
    word = words[index]
    position = rng.randrange(1, len(word) - 2)
    if rng.random() < 0.5:
        word = word[:position] + word[position + 1] + word[position] + word[position + 2 :]
    else:
        word = word[:position] + word[position + 1 :]
    words[index] = word
    return " ".join(words)


def variants(row: dict[str, Any], seed: int) -> list[dict[str, Any]]:
    text, query_id = row["query"], row["query_id"]
    forms = {
        "vi_unaccented": common.unaccent(text),
        "vi_partial": partial_unaccent(text, _rng(seed, query_id, "vi_partial")),
        "vi_typo": typo(text, _rng(seed, query_id, "vi_typo")),
    }
    return [
        {
            **row,
            "query_id": f"{query_id}:{form}",
            "query": value,
            "form": form,
            "variant_of": query_id,
        }
        for form, value in forms.items()
        if value != text
    ]


def english(row: dict[str, Any], *, model: str, base_url: str, seed: int) -> dict[str, Any] | None:
    reply = common.ollama_chat(
        [{"role": "system", "content": TRANSLATE}, {"role": "user", "content": row["query"]}],
        model=model,
        base_url=base_url,
        seed=seed,
        temperature=0.0,
    )
    try:
        value = " ".join(str(json.loads(reply).get("english", "")).split())
    except (ValueError, AttributeError):
        return None
    if len(value.split()) < 3:
        return None
    return {
        **row,
        "query_id": f"{row['query_id']}:en",
        "query": value,
        "form": "en",
        "variant_of": row["query_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--english", action="store_true")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--ollama", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    originals = [row for row in common.read_jsonl(args.queries) if row["form"] == "vi"]
    rows: list[dict[str, Any]] = []
    for row in originals:
        rows.append(row)
        rows.extend(variants(row, args.seed))
        if args.english:
            translated = english(row, model=args.model, base_url=args.ollama, seed=args.seed)
            if translated:
                rows.append(translated)
    protected = {query for query, _, _ in common.protected_hits(row["query"] for row in rows)}
    kept = [row for row in rows if row["query"] not in protected]
    common.write_jsonl(args.out, kept)
    counts: dict[str, int] = {}
    for row in kept:
        counts[row["form"]] = counts.get(row["form"], 0) + 1
    print(json.dumps({"rows": len(kept), "dropped_protected": len(rows) - len(kept), **counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
