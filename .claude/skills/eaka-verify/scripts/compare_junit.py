#!/usr/bin/env python3
"""Compare two sets of pytest JUnit XML results test-by-test.

Random parameter IDs (uuid, long hex, long digit runs) inside [...] are
normalized so the same test matches across runs.

Usage: python compare_junit.py OLD(dir|xml) NEW(dir|xml)
Exit code 1 if any test regressed (passed/xfail -> failed/error) or disappeared.
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from junit_summary import iter_xml, status_of  # noqa: E402

UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
HEX = re.compile(r"\b[0-9a-fA-F]{16,}\b")
DIGITS = re.compile(r"\d{6,}")
GOOD = {"passed", "xfail"}
BAD = {"failed", "error"}


def norm_name(name: str) -> str:
    m = re.match(r"^(.*?)(\[.*\])$", name)
    if not m:
        return name
    params = UUID.sub("<ID>", m.group(2))
    params = HEX.sub("<ID>", params)
    params = DIGITS.sub("<N>", params)
    return m.group(1) + params


def load(arg: str) -> dict[str, str]:
    res: dict[str, str] = {}
    for path in iter_xml([arg]):
        for tc in ET.parse(path).getroot().iter("testcase"):
            key = f"{tc.get('classname', '?')}::{norm_name(tc.get('name', '?'))}"
            st = status_of(tc)
            # if normalization merges several tests, keep the worst status
            if key not in res or st in BAD:
                res[key] = st
    return res


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    old, new = load(sys.argv[1]), load(sys.argv[2])
    regressed, fixed, changed, missing, added = [], [], [], [], []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if a is None:
            added.append((k, b))
        elif b is None:
            missing.append((k, a))
        elif a != b:
            if a in GOOD and b in BAD:
                regressed.append((k, a, b))
            elif a in BAD and b in GOOD:
                fixed.append((k, a, b))
            else:
                changed.append((k, a, b))

    print(f"old: {len(old)} tests | new: {len(new)} tests")
    for title, rows in [("REGRESSED", regressed), ("FIXED", fixed), ("CHANGED", changed)]:
        print(f"\n{title} ({len(rows)})")
        for k, a, b in rows:
            print(f"  {a:>8} -> {b:<8} {k}")
    print(f"\nMISSING in new ({len(missing)})")
    for k, a in missing:
        print(f"  (was {a}) {k}")
    print(f"\nNEW tests ({len(added)})")
    for k, b in added:
        print(f"  ({b}) {k}")
    return 1 if regressed or missing else 0


if __name__ == "__main__":
    sys.exit(main())
