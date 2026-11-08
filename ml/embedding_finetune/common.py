"""Shared helpers for the embedding fine-tune pipeline. Nothing here is imported by app/.

Data rule (DEC-015): training queries are synthetic, generated from chunks. No question of the UAT
set, held-out v1/v2, RBAC dev, answer_relevance_dev_v1 or false_refusal_dev_v1 may be used. The
check reads only scripts/eval/question_fingerprints.json (salted 4-gram hashes of every one of
those sets), never their text, and refuses any query that shares a 4-gram with one of them.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unicodedata
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import question_leak  # noqa: E402

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "
BASE_MODEL = "intfloat/multilingual-e5-small"
DIMENSIONS = 384
IN_CONTAINER = Path(__file__).with_name("in_container.py")
_DOCKER_ENV = {**os.environ, "MSYS_NO_PATHCONV": "1"}


class DataRuleError(RuntimeError):
    """A training query matches a protected question set (DEC-015)."""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unaccent(text: str) -> str:
    """Drop Vietnamese diacritics, keep case and spacing ("Nghỉ phép" -> "Nghi phep")."""
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    )


def protected_hits(queries: Iterable[str]) -> list[tuple[str, str, str]]:
    """(query, source, case id) for each query sharing a 4-gram with a protected set.

    Raises question_leak.QuestionSourceError when the fingerprints cannot stand for the sets,
    so a missing or stale file never reads as "no match".
    """
    payload = question_leak.load_fingerprints()
    texts = list(queries)
    hits = question_leak.find_hits(payload, (("query", n, q) for n, q in enumerate(texts)))
    return [(texts[number], source, case_id) for _, number, source, case_id in hits]


def check_data_rule(queries: Iterable[str]) -> None:
    hits = protected_hits(queries)
    if hits:
        sample = ", ".join(f"{source} {case_id}" for _, source, case_id in hits[:5])
        raise DataRuleError(f"{len(hits)} training queries match protected sets: {sample}")


def ollama_chat(
    messages: list[dict[str, str]],
    *,
    model: str,
    base_url: str,
    seed: int,
    temperature: float,
    json_format: bool = True,
    timeout: float = 300.0,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"seed": seed, "temperature": temperature, "num_ctx": 8192},
    }
    if json_format:
        payload["format"] = "json"
    request = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())["message"]["content"]


def run_in_container(container: str, command: str, payload: Any) -> Any:
    """Run in_container.py inside the API container with a JSON payload; return its JSON."""
    steps = [
        ["docker", "cp", str(IN_CONTAINER), f"{container}:/tmp/eaka_ft_in_container.py"],
    ]
    for step in steps:
        subprocess.run(step, check=True, env=_DOCKER_ENV, capture_output=True)
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "-w",
            "/app",
            "-e",
            "PYTHONPATH=/app",
            container,
            "python",
            "/tmp/eaka_ft_in_container.py",
            command,
        ],  # fmt: skip
        input=json.dumps(payload).encode(),
        check=True,
        env=_DOCKER_ENV,
        capture_output=True,
    )
    return json.loads(result.stdout.decode())


def iter_batches(rows: list[Any], size: int) -> Iterator[list[Any]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]
