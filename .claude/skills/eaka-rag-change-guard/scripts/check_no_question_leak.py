#!/usr/bin/env python3
"""Detect hard-coded evaluation questions in newly added lines under app/.

Collects question strings from tests/acceptance, uat/, eval/ (json, jsonl,
yaml, csv, txt) and checks whether any added line in app/ (from git diff)
contains one of them (or a long string literal that is part of one).

Exit codes: 0 = clean, 1 = possible leak found, 2 = usage/git error.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

QUESTION_KEYS = {"question", "query", "prompt", "q", "input", "user_question", "cau_hoi"}
SOURCE_DIRS = ["tests/acceptance", "uat", "eval"]
TEXT_EXT = {".json", ".jsonl", ".yaml", ".yml", ".csv", ".txt"}
STRING_LIT = re.compile(r"""(?:'''|\"\"\"|'|")(.+?)(?:'''|\"\"\"|'|")""")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _walk(obj, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and str(k).lower() in QUESTION_KEYS:
                out.append(v)
            else:
                _walk(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, out)


def load_questions(root: Path) -> list[str]:
    found: list[str] = []
    for d in SOURCE_DIRS:
        base = root / d
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in TEXT_EXT:
                continue
            try:
                raw = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            ext = f.suffix.lower()
            try:
                if ext == ".json":
                    _walk(json.loads(raw), found)
                elif ext == ".jsonl":
                    for line in raw.splitlines():
                        if line.strip():
                            _walk(json.loads(line), found)
                elif ext in {".yaml", ".yml"}:
                    try:
                        import yaml  # type: ignore
                    except ImportError:
                        print(f"[warn] PyYAML missing, skip {f}", file=sys.stderr)
                        continue
                    _walk(yaml.safe_load(raw), found)
                elif ext == ".csv":
                    for row in csv.DictReader(raw.splitlines()):
                        for k, v in row.items():
                            if k and k.strip().lower() in QUESTION_KEYS and v:
                                found.append(v)
                elif ext == ".txt":
                    found.extend(line for line in raw.splitlines() if line.strip())
            except (json.JSONDecodeError, ValueError) as exc:
                print(f"[warn] cannot parse {f}: {exc}", file=sys.stderr)
    return found


def added_lines(root: Path, base: str, staged: bool, path: str) -> list[tuple[str, int, str]]:
    cmd = ["git", "-C", str(root), "diff", "--unified=0", "--no-color"]
    cmd += ["--cached"] if staged else [base]
    cmd += ["--", path]
    try:
        diff = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[error] git diff failed: {exc}", file=sys.stderr)
        sys.exit(2)
    result, cur_file, lineno = [], "?", 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            cur_file = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            result.append((cur_file, lineno, line[1:]))
            lineno += 1
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repo root")
    ap.add_argument(
        "--base", default="HEAD", help="git ref to diff against (ignored with --staged)"
    )
    ap.add_argument("--staged", action="store_true", help="check staged changes")
    ap.add_argument("--path", default="app", help="path to check (default: app)")
    ap.add_argument("--min-len", type=int, default=20, help="min normalized length to compare")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    questions = {normalize(q) for q in load_questions(root)}
    questions = {q for q in questions if len(q) >= args.min_len}
    if not questions:
        print("[warn] no questions found in " + ", ".join(SOURCE_DIRS))
        return 0

    hits = []
    for file, no, text in added_lines(root, args.base, args.staged, args.path):
        norm_line = normalize(text)
        literals = [normalize(s) for s in STRING_LIT.findall(text)]
        literals = [s for s in literals if len(s) >= args.min_len]
        for q in questions:
            if q in norm_line or any(lit in q for lit in literals):
                hits.append((file, no, text.strip(), q))
                break

    print(f"checked against {len(questions)} questions")
    if not hits:
        print("OK: no hard-coded question found in added lines")
        return 0
    print(f"POSSIBLE LEAK: {len(hits)} line(s)")
    for file, no, text, q in hits:
        print(f"  {file}:{no}: {text[:120]}\n      ~ question: {q[:120]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
