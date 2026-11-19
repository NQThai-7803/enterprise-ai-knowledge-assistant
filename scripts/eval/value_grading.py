"""Value-aware grading (DEC-032): an answer counts as right only when it states every value of its
reference and gives no other value in the same unit.

Values are numbers with their unit, amounts of money, clock times and dates, each written one way.
Numbers go through `canonical_number_unit_pairs`, the claim validator's normalization (FIX 3c F):
"02 ngày" = "2 ngày", "1.200.000 đ" = "1,2 triệu đồng". Clock times are "9:30" whatever the
spelling ("09:30", "9h30"), dates are "2026-08-01", and a number word before a unit is a digit
("ba ngày" = "3 ngày").

- **Required**: every value of the reference, also one the question holds ("nghỉ 2 ngày thì báo
  trước mấy ngày": "02 ngày" is still the answer).
- **Missing**: a required value the answer does not state. A unit missing on one side still
  matches ("10" = "10 ngày").
- **Conflicting**: a value of the answer whose unit is a unit of the reference but which is neither
  a reference value nor one of the question's. A threshold ("từ 05 ngày trở lên", "trên 5 năm")
  says when a rule applies, not what it gives, so its value is no conflict.

Not values: citation markers, codes (ND-HR-004, N3), article and section numbers ("Điều 5",
"mục 3.2", but not "mức 900.000"), list numbering. The word after a number is its unit only when
it is a unit in `UNITS`.

usage:
  python scripts/eval/value_grading.py <answer> <reference> [<question>]
  python scripts/eval/value_grading.py regrade <set> <results.json> <out.json>
      <set>: uat, natural, rbac, relevance, false_refusal, false_refusal_v2, compound
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.claim_evidence_validation_service import (  # noqa: E402
    canonical_number_unit_pairs,
)

Value = tuple[str, str]

UNITS = {
    "ngay": "ngay", "tuan": "tuan", "thang": "thang", "quy": "quy", "nam": "nam",
    "gio": "gio", "tieng": "gio", "phut": "phut", "giay": "giay", "lan": "lan",
    "buoi": "buoi", "ca": "ca", "ky": "ky", "dot": "dot", "nguoi": "nguoi", "nhan": "nguoi",
    "dong": "dong", "usd": "usd", "%": "%", "diem": "diem", "bac": "bac", "km": "km",
    "kg": "kg", "tan": "tan", "lit": "lit", "cuon": "cuon", "may": "may", "chiec": "chiec",
    "days": "ngay", "day": "ngay", "weeks": "tuan", "months": "thang", "years": "nam",
    "hours": "gio", "hour": "gio", "minutes": "phut", "times": "lan", "tons": "tan",
}  # fmt: skip
_WORDS = {
    "mot": "1", "hai": "2", "ba": "3", "bon": "4", "nam": "5", "sau": "6", "bay": "7",
    "tam": "8", "chin": "9", "muoi": "10",
}  # fmt: skip
_HYPHENS = str.maketrans(dict.fromkeys("­‐‑‒–—", "-"))
_MARKERS = re.compile(r"\[(?:source_)?\d+\]|\bsource_\d+\b")
_CODES = re.compile(r"\b[a-z]{2,}(?:-[a-z0-9]+)*-\d+[a-z0-9]*\b|\b[a-z]+\d+\b")
_SCALE_OR_UNIT = rf"(?:nghin|ngan|trieu|ty|{'|'.join(map(re.escape, UNITS))})"
_ARTICLES = re.compile(  # "muc" is also "mức" (level): a section-like number with no unit after
    r"\b(?:dieu|muc|khoan|chuong|phu luc|phan|trang|phien ban|version)\s+"
    rf"\d{{1,2}}(?:\.\d{{1,2}})*(?![\d.,])(?!\s*{_SCALE_OR_UNIT}\b)"
)
_THRESHOLDS = re.compile(
    r"\btu\s+\d[\d.,]*[^.;\n]{0,40}?\btro\s+(?:len|xuong)\b|\b(?:tren|duoi|qua|hon|vuot)\s+\d[\d.,]*"
)
_LIST_NUMBERS = re.compile(r"(?m)^\s*\d+[.)]\s+")
_DATES = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})/(\d{4})(?![\d/])")
_TIMES = re.compile(
    r"(?<![\d.,:])(\d{1,2})\s*(?::|h|gio)\s*(\d{2})(?![\d])|(?<![\d.,:])(\d{1,2})h\b"
)
_RANGE_SCALE = re.compile(
    r"(?<![\d.,])(\d+(?:[.,]\d+)?)(\s*(?:-|den|toi)\s*\d+(?:[.,]\d+)?\s*)(nghin|ngan|trieu|ty)\b"
)
_NUMBER_WORDS = re.compile(rf"\b({'|'.join(_WORDS)})\s+(?=({'|'.join(UNITS)})\b)")


def fold(text: str) -> str:
    """Lowercase, no diacritics, đ as d, one kind of dash, single spaces."""
    text = (text or "").translate(_HYPHENS)
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[ \t]+", " ", stripped.casefold())


def values(text: str) -> tuple[Value, ...]:
    """Every value of a text as (value, unit); unit "" when the next word is not a unit."""
    folded = _LIST_NUMBERS.sub(" ", fold(text)).replace("phan tram", "%").replace("percent", "%")
    for pattern in (_MARKERS, _CODES, _ARTICLES):
        folded = pattern.sub(" ", folded)
    found: list[Value] = []

    def date(match: re.Match[str]) -> str:
        day, month, year = (int(g) for g in match.groups())
        found.append((f"{year}-{month:02d}-{day:02d}", "date"))
        return " "

    def time(match: re.Match[str]) -> str:
        hour, minute = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), "0")
        if int(hour) > 24 or int(minute) > 59:
            return match.group(0)
        found.append((f"{int(hour)}:{int(minute):02d}", "time"))
        return " "

    folded = _TIMES.sub(time, _DATES.sub(date, folded))
    folded = _RANGE_SCALE.sub(r"\1 \3\2\3", folded)  # "3 - 15 triệu": 3 is millions too
    folded = _NUMBER_WORDS.sub(lambda m: _WORDS[m.group(1)] + " ", folded)
    found += [(value, UNITS.get(unit, "")) for value, unit in canonical_number_unit_pairs(folded)]
    return tuple(found)


def _states(stated: set[Value], wanted: Value) -> bool:
    value, unit = wanted
    if unit == "time":  # "18:00" is also "18 giờ"
        times = {v for v, u in stated if u == "time"}
        return value in times | {f"{v}:00" for v, u in stated if u == "gio" and v.isdigit()}
    return any(v == value and (u == unit or not u or not unit) for v, u in stated if u != "time")


def check(answer: str, references: str | Iterable[str], question: str = "") -> dict[str, Any]:
    """Required, missing and conflicting values of an answer against its reference text(s)."""
    texts = [references] if isinstance(references, str) else list(references)
    reference = {pair for text in texts for pair in values(text)}
    given = {value for value, _ in values(question)}
    stated = set(values(answer))
    unconditional = set(values(_THRESHOLDS.sub(" ", fold(answer))))
    required = sorted(reference)
    known = {value for value, _ in reference} | given
    units = {unit for _, unit in reference if unit}
    missing = [pair for pair in required if not _states(stated, pair)]
    conflicting = sorted(p for p in unconditional if p[1] in units and p[0] not in known)
    return {
        "required": required,
        "missing": missing,
        "conflicting": conflicting,
        "ok": not missing and not conflicting,
    }


def says(form: str, text: str) -> bool:
    """The folded text holds the form with no digit touching it ("1 lần" is not in "11 lần")."""
    pattern = re.escape(" ".join(fold(form).split()))
    return re.search(rf"(?<![\d.,]){pattern}(?!\d)", " ".join(fold(text).split())) is not None


def fact_forms(item: Mapping[str, Any]) -> list[str]:
    """Every accepted form of a synthetic-set item's facts (`fact`, alternatives, also_facts)."""
    return [
        form
        for fact in (item, *item.get("also_facts", ()))
        for form in (fact["fact"], *fact.get("fact_alternatives", ()))
    ]


# The dev sets state their facts as text forms and keep that check for presence (it covers names
# and places too); the values add the conflict check. UAT has a free-text reference: both checks.
ACCEPTANCE = ROOT / "tests" / "acceptance"
SET_FILES = {
    "relevance": "answer_relevance_dev_v1", "false_refusal": "false_refusal_dev_v1",
    "false_refusal_v2": "false_refusal_dev_v2", "compound": "compound_partial_dev_v1",
}  # fmt: skip


def _yaml(name: str) -> Any:
    import yaml

    return yaml.safe_load((ACCEPTANCE / f"{name}.yaml").read_text(encoding="utf-8"))


def _gate(case: dict[str, Any], key: str, checked: dict[str, Any], ok: bool) -> dict[str, Any]:
    before = case.get(f"{key}_before_values", case.get(key))
    return {**case, key: bool(before) and ok, f"{key}_before_values": before, "values": checked}


def regrade(set_name: str, results: dict[str, Any]) -> dict[str, Any]:
    """The stored results of a run, graded again with the values (no new run). Idempotent: the
    flag before the values is kept as `<flag>_before_values` and is where a regrade starts."""
    cases = results["cases"]
    if set_name == "uat":
        graded = []
        for case in cases:
            answer, reference = case.get("answer") or "", case.get("reference_answer") or ""
            checked = check(answer, reference, case.get("question") or "")
            match = case["proxy_match"]
            value_match = None if match is None else bool(match) and checked["ok"]
            graded.append({**case, "values": checked, "value_match": value_match})
    elif set_name == "natural":
        questions = {item["id"]: item["question"] for item in _yaml("natural_dev_v1")["items"]}
        keys = _yaml("natural_dev_v1_proxy")["items"]
        graded = []
        for case in cases:
            forms = [form for group in keys[case["id"]].get("facts", []) for form in group]
            checked = check(case.get("answer") or "", forms, questions[case["id"]])
            graded.append(_gate(case, "passed", checked, not checked["conflicting"]))
    elif set_name == "rbac":
        items = {item["id"]: item for item in _yaml("rbac_dev_v1")["items"]}
        graded = []
        for case in cases:
            if case["kind"] != "control":
                graded.append(case)
                continue
            item, answer = items[case["id"]], case.get("answer") or ""
            checked = check(answer, item["fact"], item["question"])
            ok = says(item["fact"], answer) and not checked["conflicting"]
            graded.append(_gate(case, "control_passed", checked, ok))
    else:
        items = {item["id"]: item for item in _yaml(SET_FILES[set_name])["items"]}
        graded = []
        for case in cases:
            item = items[case["id"]]
            if item["expect"] == "refuse":
                graded.append(case)
                continue
            checked = check(case.get("answer") or "", fact_forms(item), item["question"])
            graded.append(_gate(case, "passed", checked, not checked["conflicting"]))
    return {**results, "cases": graded, "value_grading": "DEC-032"}


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if argv and argv[0] == "regrade":
        set_name, source, target = argv[1:4]
        results = json.loads(Path(source).read_text(encoding="utf-8-sig"))
        Path(target).write_text(
            json.dumps(regrade(set_name, results), ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return 0
    print(json.dumps(check(*argv[:3]), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
