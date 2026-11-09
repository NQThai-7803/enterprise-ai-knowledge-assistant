"""Compare code and question sets through hashed word 4-grams, without any question text.

usage (repo root, project venv):
  python scripts/eval/question_leak.py build    # needs artifacts/ and docs/eval/; prints counts
  python scripts/eval/question_leak.py check [--base HEAD | --staged] [--path app]
  python scripts/eval/question_leak.py overlap

`build` reads only the question of each dev and held-out item and writes
scripts/eval/question_fingerprints.json: salted hashes, never question or gold text. `check` and
`overlap` read only that file, so they need neither artifacts/ nor docs/eval/.

Exit codes: 0 clean, 1 match found, 2 no usable question source or a usage/git error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
import subprocess
import sys
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FINGERPRINTS = ROOT / "scripts" / "eval" / "question_fingerprints.json"
DEV_SOURCE = ROOT / "artifacts" / "rag-h5-1-stress-uat.py"
LOCK = ROOT / "docs" / "eval" / "heldout-v1.lock"
HELDOUT = ROOT / "docs" / "eval" / "heldout-v1.yaml"
LOCK_V2 = ROOT / "docs" / "eval" / "heldout-v2-questions.lock"
HELDOUT_V2 = ROOT / "docs" / "eval" / "heldout-v2-questions.yaml"
RBAC_SOURCE = ROOT / "tests" / "acceptance" / "rbac_dev_v1.yaml"
RELEVANCE_SOURCE = ROOT / "tests" / "acceptance" / "answer_relevance_dev_v1.yaml"
FALSE_REFUSAL_SOURCE = ROOT / "tests" / "acceptance" / "false_refusal_dev_v1.yaml"
FALSE_REFUSAL_LOCK = ROOT / "tests" / "acceptance" / "false_refusal_dev_v1.lock"
FALSE_REFUSAL_V2_SOURCE = ROOT / "tests" / "acceptance" / "false_refusal_dev_v2.yaml"
FALSE_REFUSAL_V2_LOCK = ROOT / "tests" / "acceptance" / "false_refusal_dev_v2.lock"
SALT = b"eaka-question-fingerprint-v1"
GRAM_SIZE = 4
EXPECTED_COUNTS = {
    "dev": 100,
    "heldout": 40,
    "rbac": 18,
    "relevance": 25,
    "heldout_v2": 20,
    "false_refusal": 20,
    "false_refusal_v2": 24,
}
OVERLAP_LIMIT = 0.60
ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
WORD = re.compile(r"\w+")


class QuestionSourceError(RuntimeError):
    """No usable question source: a check on it would prove nothing."""


def words(text: str) -> list[str]:
    """Fold case and diacritics, decoding \\uXXXX so escaped Vietnamese compares too."""
    decoded = ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), text)
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFD", decoded) if unicodedata.category(ch) != "Mn"
    )
    return WORD.findall(stripped.replace("đ", "d").replace("Đ", "D").casefold())


def _hash(gram: str) -> str:
    return hashlib.blake2b(gram.encode("utf-8"), digest_size=8, key=SALT).hexdigest()


def fingerprint(text: str) -> list[str]:
    tokens = words(text)
    if len(tokens) < GRAM_SIZE:
        return [_hash(" ".join(tokens))] if tokens else []
    grams = {" ".join(tokens[i : i + GRAM_SIZE]) for i in range(len(tokens) - GRAM_SIZE + 1)}
    return sorted(_hash(gram) for gram in grams)


def build_payload(
    dev: Iterable[tuple[str, str]],
    heldout: Iterable[tuple[str, str]],
    lock_sha256: str,
    rbac: Iterable[tuple[str, str]] = (),
    relevance: Iterable[tuple[str, str]] = (),
    heldout_v2: Iterable[tuple[str, str]] = (),
    lock_v2_sha256: str = "",
    false_refusal: Iterable[tuple[str, str]] = (),
    false_refusal_v2: Iterable[tuple[str, str]] = (),
) -> dict[str, Any]:
    dev_items = {case_id: fingerprint(question) for case_id, question in dev}
    heldout_items = {case_id: fingerprint(question) for case_id, question in heldout}
    rbac_items = {case_id: fingerprint(question) for case_id, question in rbac}
    relevance_items = {case_id: fingerprint(question) for case_id, question in relevance}
    v2_items = {case_id: fingerprint(question) for case_id, question in heldout_v2}
    false_refusal_items = {case_id: fingerprint(question) for case_id, question in false_refusal}
    fr_v2_items = {case_id: fingerprint(question) for case_id, question in false_refusal_v2}
    return {
        "version": 1,
        "gram_size": GRAM_SIZE,
        "sources": {
            "dev": {"count": len(dev_items), "items": dev_items},
            "heldout": {
                "count": len(heldout_items),
                "lock_sha256": lock_sha256,
                "items": heldout_items,
            },
            "rbac": {"count": len(rbac_items), "items": rbac_items},
            "relevance": {"count": len(relevance_items), "items": relevance_items},
            "false_refusal": {"count": len(false_refusal_items), "items": false_refusal_items},
            "false_refusal_v2": {"count": len(fr_v2_items), "items": fr_v2_items},
            "heldout_v2": {
                "count": len(v2_items),
                "lock_sha256": lock_v2_sha256,
                "items": v2_items,
            },
        },
    }


def load_fingerprints(
    path: Path = FINGERPRINTS,
    lock: Path = LOCK,
    expected: Mapping[str, int] = EXPECTED_COUNTS,
    lock_v2: Path = LOCK_V2,
) -> dict[str, Any]:
    """Return the fingerprints, or refuse when they cannot stand for the question sets."""
    if not path.is_file():
        raise QuestionSourceError(f"fingerprint file missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources = payload["sources"]
        counts = {name: len(sources[name]["items"]) for name in expected}
    except (ValueError, KeyError, TypeError) as exc:
        raise QuestionSourceError(f"fingerprint file unreadable: {exc}") from exc
    for name, count in expected.items():
        if counts[name] != count:
            raise QuestionSourceError(f"source {name} has {counts[name]} questions, not {count}")
        if not any(sources[name]["items"].values()):
            raise QuestionSourceError(f"source {name} has no fingerprints")
    if not lock.is_file():
        raise QuestionSourceError(f"held-out lock missing: {lock}")
    if json.loads(lock.read_text(encoding="utf-8"))["sha256"] != sources["heldout"]["lock_sha256"]:
        raise QuestionSourceError("fingerprints were built from another held-out file; rebuild")
    if "heldout_v2" in expected and (
        not lock_v2.is_file()
        or json.loads(lock_v2.read_text(encoding="utf-8"))["sha256"]
        != sources["heldout_v2"]["lock_sha256"]
    ):
        raise QuestionSourceError("fingerprints do not match the held-out v2 lock; rebuild")
    return payload


def find_hits(
    payload: Mapping[str, Any], lines: Iterable[tuple[str, int, str]]
) -> list[tuple[str, int, str, str]]:
    """Return (file, line, source, question id) for each added line sharing a question 4-gram."""
    index: dict[str, tuple[str, str]] = {}
    for source, data in payload["sources"].items():
        for case_id, hashes in data["items"].items():
            for value in hashes:
                index.setdefault(value, (source, case_id))
    hits = []
    for file, number, text in lines:
        tokens = words(text)
        # A question shorter than GRAM_SIZE is fingerprinted whole, so look for shorter runs too.
        grams = (
            " ".join(tokens[i : i + size])
            for size in range(GRAM_SIZE, 0, -1)
            for i in range(len(tokens) - size + 1)
        )
        for gram in grams:
            match = index.get(_hash(gram))
            if match:
                hits.append((file, number, *match))
                break
    return hits


def added_lines(root: Path, base: str, staged: bool, path: str) -> list[tuple[str, int, str]]:
    command = ["git", "-C", str(root), "diff", "--unified=0", "--no-color"]
    command += ["--cached"] if staged else [base]
    command += ["--", path]
    diff = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout
    result: list[tuple[str, int, str]] = []
    current, number = "?", 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            number = int(match.group(1)) if match else 0
        elif line.startswith("+"):
            result.append((current, number, line[1:]))
            number += 1
    return result


def max_overlap(payload: Mapping[str, Any]) -> tuple[float, str | None, str | None]:
    """Largest Jaccard similarity of any dev question with any held-out question."""
    best: tuple[float, str | None, str | None] = (0.0, None, None)
    sources = payload["sources"]
    development = {
        **sources["dev"]["items"],
        **sources.get("rbac", {}).get("items", {}),
        **sources.get("relevance", {}).get("items", {}),
        **sources.get("false_refusal", {}).get("items", {}),
        **sources.get("false_refusal_v2", {}).get("items", {}),
    }
    for dev_id, dev_hashes in development.items():
        left = set(dev_hashes)
        for heldout_id, heldout_hashes in sources["heldout"]["items"].items():
            right = set(heldout_hashes)
            union = left | right
            value = len(left & right) / len(union) if union else 0.0
            if value > best[0]:
                best = (value, dev_id, heldout_id)
    return best


def relevance_uat_overlap(payload: Mapping[str, Any]) -> tuple[float, str | None, str | None]:
    """Largest Jaccard similarity of a relevance dev question with a Q001-Q100 question."""
    best: tuple[float, str | None, str | None] = (0.0, None, None)
    sources = payload["sources"]
    for left_id, left_hashes in sources.get("relevance", {}).get("items", {}).items():
        left = set(left_hashes)
        for right_id, right_hashes in sources["dev"]["items"].items():
            right = set(right_hashes)
            union = left | right
            value = len(left & right) / len(union) if union else 0.0
            if value > best[0]:
                best = (value, left_id, right_id)
    return best


def source_overlap(
    payload: Mapping[str, Any], name: str, others: Iterable[str]
) -> dict[str, tuple[float, str | None, str | None]]:
    """Largest Jaccard similarity of one source with each of the others."""
    sources = payload["sources"]
    result = {}
    for other in others:
        best: tuple[float, str | None, str | None] = (0.0, None, None)
        for left_id, left_hashes in sources.get(name, {}).get("items", {}).items():
            left = set(left_hashes)
            for right_id, right_hashes in sources[other]["items"].items():
                union = left | set(right_hashes)
                value = len(left & set(right_hashes)) / len(union) if union else 0.0
                if value > best[0]:
                    best = (value, left_id, right_id)
        result[other] = best
    return result


def _build(output: Path) -> int:
    import yaml

    if not DEV_SOURCE.is_file() or not HELDOUT.is_file() or not LOCK.is_file():
        raise QuestionSourceError("build needs artifacts/ and docs/eval/ on this machine")
    lock_sha = json.loads(LOCK.read_text(encoding="utf-8"))["sha256"]
    if hashlib.sha256(HELDOUT.read_bytes()).hexdigest() != lock_sha:
        raise QuestionSourceError("held-out file does not match its lock")
    dev = [(row[0], row[2]) for row in runpy.run_path(str(DEV_SOURCE))["CORE"]]
    items = yaml.safe_load(HELDOUT.read_text(encoding="utf-8"))["items"]
    heldout = [(item["id"], item["question"]) for item in items]
    rbac_items = yaml.safe_load(RBAC_SOURCE.read_text(encoding="utf-8"))["items"]
    rbac = [(item["id"], item["question"]) for item in rbac_items]
    relevance_items = yaml.safe_load(RELEVANCE_SOURCE.read_text(encoding="utf-8"))["items"]
    relevance = [(item["id"], item["question"]) for item in relevance_items]
    if not HELDOUT_V2.is_file() or not LOCK_V2.is_file():
        raise QuestionSourceError("build needs the frozen held-out v2 questions")
    lock_v2_sha = json.loads(LOCK_V2.read_text(encoding="utf-8"))["sha256"]
    if hashlib.sha256(HELDOUT_V2.read_bytes()).hexdigest() != lock_v2_sha:
        raise QuestionSourceError("held-out v2 questions do not match their lock")
    v2_items = yaml.safe_load(HELDOUT_V2.read_text(encoding="utf-8"))["items"]
    v2 = [(item["id"], item["question"]) for item in v2_items]
    fr_lock_sha = json.loads(FALSE_REFUSAL_LOCK.read_text(encoding="utf-8"))["sha256"]
    if hashlib.sha256(FALSE_REFUSAL_SOURCE.read_bytes()).hexdigest() != fr_lock_sha:
        raise QuestionSourceError("false-refusal dev set does not match its lock")
    fr_items = yaml.safe_load(FALSE_REFUSAL_SOURCE.read_text(encoding="utf-8"))["items"]
    false_refusal = [(item["id"], item["question"]) for item in fr_items]
    fr_v2_lock_sha = json.loads(FALSE_REFUSAL_V2_LOCK.read_text(encoding="utf-8"))["sha256"]
    if hashlib.sha256(FALSE_REFUSAL_V2_SOURCE.read_bytes()).hexdigest() != fr_v2_lock_sha:
        raise QuestionSourceError("false-refusal dev v2 does not match its lock")
    fr_v2_items = yaml.safe_load(FALSE_REFUSAL_V2_SOURCE.read_text(encoding="utf-8"))["items"]
    false_refusal_v2 = [(item["id"], item["question"]) for item in fr_v2_items]
    payload = build_payload(
        dev, heldout, lock_sha, rbac, relevance, v2, lock_v2_sha, false_refusal, false_refusal_v2
    )
    output.write_text(json.dumps(payload, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"dev: {len(dev)}; held-out: {len(heldout)}; rbac dev: {len(rbac)}; "
        f"relevance dev: {len(relevance)}; held-out v2: {len(v2)}; "
        f"false-refusal dev: {len(false_refusal)}; false-refusal dev v2: {len(false_refusal_v2)}"
    )
    return 0


def _check(args: argparse.Namespace) -> int:
    payload = load_fingerprints()
    lines = added_lines(Path(args.root).resolve(), args.base, args.staged, args.path)
    hits = find_hits(payload, lines)
    counts = {name: data["count"] for name, data in payload["sources"].items()}
    print(f"checked {len(lines)} added line(s) against {counts}")
    if not hits:
        print("OK: no question 4-gram found in added lines")
        return 0
    print(f"POSSIBLE LEAK: {len(hits)} line(s)")
    for file, number, source, case_id in hits:
        print(f"  {file}:{number}: shares a 4-gram with {source} {case_id}")
    return 1


def _overlap() -> int:
    payload = load_fingerprints()
    value, dev_id, heldout_id = max_overlap(payload)
    print(f"max dev/held-out Jaccard: {value:.3f} ({dev_id}, {heldout_id}); limit {OVERLAP_LIMIT}")
    uat_value, relevance_id, uat_id = relevance_uat_overlap(payload)
    print(f"max relevance/Q001-Q100 Jaccard: {uat_value:.3f} ({relevance_id}, {uat_id})")
    # Reported only: the owner reviews these numbers, they block nothing.
    others = ("dev", "heldout", "relevance", "rbac", "false_refusal", "false_refusal_v2")
    for other, (found, left, right) in source_overlap(payload, "heldout_v2", others).items():
        print(f"held-out v2/{other} word 4-gram Jaccard: {found:.3f} ({left}, {right})")
    return 1 if max(value, uat_value) >= OVERLAP_LIMIT else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    build = sub.add_parser("build")
    build.add_argument("--output", type=Path, default=FINGERPRINTS)
    check = sub.add_parser("check")
    check.add_argument("--root", default=str(ROOT))
    check.add_argument("--base", default="HEAD")
    check.add_argument("--staged", action="store_true")
    check.add_argument("--path", default="app")
    sub.add_parser("overlap")
    args = parser.parse_args(argv)
    try:
        if args.mode == "build":
            return _build(args.output)
        return _check(args) if args.mode == "check" else _overlap()
    except QuestionSourceError as exc:
        print(f"[error] {exc}", file=sys.stderr)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[error] git diff failed: {exc}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
