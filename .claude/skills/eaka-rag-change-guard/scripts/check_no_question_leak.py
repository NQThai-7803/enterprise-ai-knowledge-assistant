#!/usr/bin/env python3
"""Detect hard-coded evaluation questions in newly added lines under app/.

Thin entry point for the guard; the logic and its tests live in scripts/eval/question_leak.py.
It compares hashed word 4-grams, so it reads neither artifacts/ nor docs/eval/.

Exit codes: 0 = clean, 1 = possible leak found, 2 = no usable question source or a usage/git error.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.eval.question_leak import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["check", *sys.argv[1:]]))
