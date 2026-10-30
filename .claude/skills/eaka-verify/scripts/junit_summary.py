#!/usr/bin/env python3
"""Summarize pytest JUnit XML files: pass/fail/error/skip/xfail per test file.

Usage: python junit_summary.py report1.xml [report2.xml ...|dir]
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

COLS = ["passed", "failed", "error", "skipped", "xfail"]


def iter_xml(args: list[str]):
    for a in args:
        p = Path(a)
        if p.is_dir():
            yield from sorted(p.glob("*.xml"))
        elif p.is_file():
            yield p


def status_of(tc: ET.Element) -> str:
    if tc.find("failure") is not None:
        return "failed"
    if tc.find("error") is not None:
        return "error"
    sk = tc.find("skipped")
    if sk is not None:
        if "xfail" in (sk.get("type", "") + sk.get("message", "")).lower():
            return "xfail"
        return "skipped"
    return "passed"


def file_of(tc: ET.Element) -> str:
    if tc.get("file"):
        return tc.get("file")
    cls = tc.get("classname", "?")
    parts = cls.split(".")
    # tests.test_x.TestCls -> tests/test_x.py
    mods = [p for p in parts if not p[:1].isupper()]
    return "/".join(mods) + ".py" if mods else cls


def collect(paths) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(COLS, 0))
    for path in paths:
        for tc in ET.parse(path).getroot().iter("testcase"):
            table[file_of(tc)][status_of(tc)] += 1
    return table


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    table = collect(list(iter_xml(sys.argv[1:])))
    if not table:
        print("no testcases found")
        return 2
    width = max(len(f) for f in table) + 2
    print("file".ljust(width) + "".join(c.rjust(9) for c in COLS))
    total = dict.fromkeys(COLS, 0)
    for f in sorted(table):
        row = table[f]
        print(f.ljust(width) + "".join(str(row[c]).rjust(9) for c in COLS))
        for c in COLS:
            total[c] += row[c]
    print("TOTAL".ljust(width) + "".join(str(total[c]).rjust(9) for c in COLS))
    return 1 if total["failed"] or total["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
