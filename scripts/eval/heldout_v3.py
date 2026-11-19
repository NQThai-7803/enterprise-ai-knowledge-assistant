"""Held-out v3: import the team member's workbook word for word, freeze it, check it.

Never runs the RAG system.

usage (repo root, project venv):
  python scripts/eval/heldout_v3.py import <workbook.xlsx>   # writes heldout-v3.yaml and its lock
  python scripts/eval/heldout_v3.py check                     # writes heldout-v3-check.json
  python scripts/eval/heldout_v3.py derive-v3.1               # writes heldout-v3.1.yaml + lock

Held-out v3 was written by a member of the team, with its gold (DEC-030). It is never used to design
a fix and is run only at the measurement milestone. Both commands print only ids, counts and flags,
never question, answer or source text, so the session that runs them learns nothing it could design
from. The details for the owner go to heldout-v3-check.json.

`import` reads the sheet "Held-out" with the standard library (an .xlsx is zipped XML), keeps every
cell of the six gold columns as it is, reloads the YAML and refuses if any cell changed. `check`
refuses a YAML that differs from its lock. Its findings only report; they change nothing.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import zipfile
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import heldout_check, question_leak  # noqa: E402

DOCS = ROOT / "docs" / "eval"
HELDOUT = DOCS / "heldout-v3.yaml"
LOCK = DOCS / "heldout-v3.lock"
REPORT = DOCS / "heldout-v3-check.json"
SHEET = "Held-out"
COLUMNS = {  # workbook header -> YAML field
    "#": "number",
    "Nhóm": "group",
    "Câu hỏi": "question",
    "Tài khoản test": "test_account",
    "Đáp án kỳ vọng": "expected_answer",
    "Nguồn trích dẫn kỳ vọng": "expected_sources",
}
RESULT_COLUMNS = ("Kết quả thực tế", "Pass/Fail", "Ghi chú")
# Seeded accounts (app/scripts/seed_uat_data.py): admin has no department; manager and staff are in
# "UAT Knowledge Operations". No seeded account belongs to an HR or an engineering department.
ACCOUNTS = {"Bất kỳ": "staff.uat@example.test"}
CODE = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)*-\d{3}\b")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


class FrozenSetChangedError(RuntimeError):
    """The YAML differs from its lock, so nothing built on it can be compared."""


def _column(ref: str) -> int:
    number = 0
    for letter in re.match(r"[A-Z]+", ref).group(0):
        number = number * 26 + ord(letter) - 64
    return number - 1


def read_sheet(path: Path, name: str) -> list[list[str]]:
    """Every row of one sheet as text, cells in column order ('' for an empty cell)."""
    with zipfile.ZipFile(path) as book:
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in si.iter(f"{_NS}t")) for si in root]
        workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        target = {rel.get("Id"): rel.get("Target").lstrip("/") for rel in rels}
        sheet = next(s for s in workbook.iter(f"{_NS}sheet") if s.get("name") == name)
        part = target[sheet.get(_REL)]
        root = ElementTree.fromstring(book.read(part if part.startswith("xl/") else f"xl/{part}"))
    rows = []
    for row in root.iter(f"{_NS}row"):
        cells: dict[int, str] = {}
        for cell in row.iter(f"{_NS}c"):
            kind, value = cell.get("t"), cell.find(f"{_NS}v")
            if kind == "s":
                text = strings[int(value.text)]
            elif kind == "inlineStr":
                text = "".join(t.text or "" for t in cell.iter(f"{_NS}t"))
            else:
                text = value.text if value is not None and value.text is not None else ""
            cells[_column(cell.get("r"))] = text
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


def items_from_rows(rows: Sequence[Sequence[str]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """The gold items, and how many rows have something in the result columns."""
    start = next(i for i, row in enumerate(rows) if "Câu hỏi" in row)
    header = list(rows[start])
    missing = [name for name in (*COLUMNS, *RESULT_COLUMNS) if name not in header]
    if missing:
        raise ValueError(f"workbook lacks columns {missing}")
    at = {name: header.index(name) for name in (*COLUMNS, *RESULT_COLUMNS)}
    items, filled = [], dict.fromkeys(RESULT_COLUMNS, 0)
    for row in rows[start + 1 :]:
        cell = lambda name, row=row: row[at[name]] if at[name] < len(row) else ""  # noqa: E731
        if not any(cell(name).strip() for name in COLUMNS):
            continue
        number = int(float(cell("#")))
        item = {"id": f"HO3-{number:02d}"}
        item.update({field: cell(name) for name, field in COLUMNS.items() if field != "number"})
        item["number"] = number
        items.append(item)
        for name in RESULT_COLUMNS:
            filled[name] += bool(cell(name).strip())
    return items, filled


def render_yaml(items: Sequence[Mapping[str, Any]], source: Path, source_sha: str) -> str:
    import yaml

    document = {
        "version": "heldout_v3",
        "author": "a member of the project team (not the owner, not Claude)",
        "source_file": source.name,
        "source_sheet": SHEET,
        "source_sha256": source_sha,
        "converted_at": date.today().isoformat(),
        "rule": (
            "DEC-030: word for word from the workbook; never used to design a fix; "
            "run only at the measurement milestone with the owner's approval"
        ),
        "items": list(items),
    }
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=10**6)


def import_workbook(source: Path) -> int:
    import yaml

    data = source.read_bytes()
    items, filled = items_from_rows(read_sheet(source, SHEET))
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate # in the workbook")
    text = render_yaml(items, source, hashlib.sha256(data).hexdigest())
    if yaml.safe_load(text)["items"] != items:
        raise ValueError("YAML round trip changed a cell")
    HELDOUT.write_text(text, encoding="utf-8", newline="\n")
    lock = {
        "version": "heldout_v3",
        "file": "docs/eval/heldout-v3.yaml",
        "sha256": hashlib.sha256(HELDOUT.read_bytes()).hexdigest(),
        "frozen_at": date.today().isoformat(),
        "items": len(items),
        "approved_by": "questions and gold written by a team member; frozen as received (DEC-030)",
        "rule": "any edit needs v3.1 with a new lock",
    }
    LOCK.write_text(json.dumps(lock, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"items: {len(items)}; ids {ids[0]}..{ids[-1]}; result columns filled: {filled}")
    print(f"lock sha256: {lock['sha256']}")
    return 0


def verify_frozen(heldout: Path = HELDOUT, lock: Path = LOCK) -> list[dict[str, Any]]:
    import yaml

    expected = json.loads(lock.read_text(encoding="utf-8"))["sha256"]
    actual = hashlib.sha256(heldout.read_bytes()).hexdigest()
    if actual != expected:
        raise FrozenSetChangedError(f"heldout-v3.yaml sha256 {actual} != frozen {expected}")
    return yaml.safe_load(heldout.read_text(encoding="utf-8"))["items"]


def source_segments(text: str) -> list[tuple[str, str]]:
    """(document code, the reference written after it) for each code in the source column."""
    found = list(CODE.finditer(text))
    return [
        (m.group(0), text[m.end() : found[i + 1].start() if i + 1 < len(found) else len(text)])
        for i, m in enumerate(found)
    ]


def reference_found(reference: str, folded_doc: str) -> str:
    """'phrase' when the folded reference is in the document, 'words' when only its words are,
    'none' otherwise, 'empty' when there is nothing after the code."""
    words = heldout_check.fold(reference).split()
    if not words:
        return "empty"
    if " ".join(words) in folded_doc:
        return "phrase"
    return "words" if set(words) <= set(folded_doc.split()) else "none"


def check_item(item: Mapping[str, Any], docs: Mapping[str, str]) -> dict[str, Any]:
    account = ACCOUNTS.get(item["test_account"].strip())
    segments = source_segments(item["expected_sources"])
    refs = [
        {"document": code, "reference": ref.strip(" ,;:-–\n"), "found": "no document"}
        if code not in docs
        else {
            "document": code,
            "reference": ref.strip(" ,;:-–\n"),
            "found": reference_found(ref, docs[code]),
        }
        for code, ref in segments
    ]
    cited = " ".join(docs[code] for code, _ in segments if code in docs)
    numbers = sorted(set(NUMBER.findall(item["expected_answer"])))
    absent = [n for n in numbers if heldout_check.fold(n) not in cited]
    return {
        "documents_not_in_corpus": sorted({code for code, _ in segments if code not in docs}),
        "no_document_code": not segments,
        "account": account,
        "references": refs,
        "answer_numbers": len(numbers),
        "answer_numbers_not_in_cited_documents": absent,
    }


def overlaps(items: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per item and set: word 4-gram Jaccard against every fingerprinted set; character trigram and
    difflib against the sets whose text lives outside docs/eval."""
    payload = question_leak.load_fingerprints()
    texts = {
        "dev": heldout_check.load_uat(),
        **{
            name: {i["id"]: i["question"] for i in _yaml_items(path)}
            for name, path in (
                ("rbac", question_leak.RBAC_SOURCE),
                ("relevance", question_leak.RELEVANCE_SOURCE),
                ("false_refusal", question_leak.FALSE_REFUSAL_SOURCE),
                ("false_refusal_v2", question_leak.FALSE_REFUSAL_V2_SOURCE),
                ("compound_partial", question_leak.COMPOUND_SOURCE),
                ("natural_dev", question_leak.NATURAL_SOURCE),
            )
        },
    }
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        mine = set(question_leak.fingerprint(item["question"]))
        folded = heldout_check.fold(item["question"])
        grams = heldout_check.trigrams(folded)
        rows: dict[str, Any] = {}
        for name, source in payload["sources"].items():
            if name == "heldout_v3":
                continue
            word4 = max(
                ((heldout_check.jaccard(mine, set(h)), i) for i, h in source["items"].items()),
                default=(0.0, None),
            )
            row = {"word4_max": round(word4[0], 3), "word4_nearest": word4[1]}
            if name in texts:
                tri = max(
                    (heldout_check.jaccard(grams, heldout_check.trigrams(heldout_check.fold(t))), i)
                    for i, t in texts[name].items()
                )
                seq = max(
                    (difflib.SequenceMatcher(None, folded, heldout_check.fold(t)).ratio(), i)
                    for i, t in texts[name].items()
                )
                row.update(
                    trigram_max=round(tri[0], 3), trigram_nearest=tri[1],
                    difflib_max=round(seq[0], 3), difflib_nearest=seq[1],
                )  # fmt: skip
            rows[name] = row
        result[item["id"]] = rows
    return result


def _yaml_items(path: Path) -> list[dict[str, Any]]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"]


def check() -> int:
    items = verify_frozen()
    pages, problems = heldout_check.load_pages()
    docs = {code: heldout_check.fold(" ".join(texts)) for code, texts in pages.items()}
    findings = {item["id"]: check_item(item, docs) for item in items}
    numbers = overlaps(items)
    surface = {
        item_id: sorted(
            name
            for name, row in rows.items()
            if max(row["word4_max"], row.get("trigram_max", 0), row.get("difflib_max", 0))
            >= heldout_check.SURFACE_THRESHOLD
        )
        for item_id, rows in numbers.items()
    }
    report = {"pdf_problems": problems, "items": findings, "overlap": numbers}
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    # Ids, counts and flags only: no question, answer or source text reaches this output.
    for item_id, found in findings.items():
        flags = []
        if found["documents_not_in_corpus"]:
            flags.append(f"not in corpus V2: {found['documents_not_in_corpus']}")
        if found["no_document_code"]:
            flags.append("no document code")
        if not found["account"]:
            flags.append("no seeded account")
        weak = [
            r["document"] + ":" + r["found"]
            for r in found["references"]
            if r["found"] in ("none", "words")
        ]
        if weak:
            flags.append(f"reference not found as written: {weak}")
        if found["answer_numbers_not_in_cited_documents"]:
            flags.append(
                f"{len(found['answer_numbers_not_in_cited_documents'])} of "
                f"{found['answer_numbers']} answer numbers not in the cited documents"
            )
        if surface[item_id]:
            flags.append(f"surface overlap >= 0.60 with {surface[item_id]}")
        print(f"{item_id}: {'; '.join(flags) or 'ok'}")
    top = {
        name: max((rows[name]["word4_max"], i) for i, rows in numbers.items() if name in rows)
        for name in next(iter(numbers.values()))
    }
    print("largest word 4-gram Jaccard per set:", {k: (v[0], v[1]) for k, v in top.items()})
    print(f"pdf problems: {problems or 'none'}; details in {REPORT.relative_to(ROOT)}")
    return 0


# Held-out v3.1 (DEC-038, owner's decisions of 2026-11-18): v3 without the items whose source
# document is not in corpus V2, with a value check on the items whose references were weak.
HELDOUT_V31 = DOCS / "heldout-v3.1.yaml"
LOCK_V31 = DOCS / "heldout-v3.1.lock"
REMOVED = {"HO3-09", "HO3-13", "HO3-20"}
VALUE_CHECKED = ("HO3-03", "HO3-05", "HO3-07", "HO3-08", "HO3-10", "HO3-11", "HO3-16", "HO3-17",
                 "HO3-18")  # fmt: skip
PENDING_BY_DEFAULT = {"HO3-08", "HO3-11"}
NEAR_DUPLICATE = {"HO3-02": "UAT", "HO3-03": "UAT", "HO3-19": "UAT", "HO3-06": "rbac_dev"}
ACTIVE = "ACTIVE"  # the only status a run asks
PENDING = "PENDING_AUTHOR_REVIEW"
EXCLUDED = "EXCLUDED"  # DEC-038: dropped by the owner (gold not confirmed against its source)


def gold_values_found(item: Mapping[str, Any], docs: Mapping[str, str]) -> dict[str, Any]:
    """Whether the cited documents are in the corpus, and how many of the expected answer's values
    (numbers, times, dates, %) occur in their text. Counts only."""
    from scripts.eval import value_grading

    codes = sorted({code for code, _ in source_segments(item["expected_sources"])})
    text = " ".join(docs[code] for code in codes if code in docs)
    result = value_grading.check(text, item["expected_answer"])
    total = len(result["required"])
    return {
        "in_corpus": bool(codes) and all(code in docs for code in codes),
        "found": total - len(result["missing"]),
        "total": total,
    }


def derive_v31(items: Sequence[Mapping[str, Any]], docs: Mapping[str, str]) -> tuple[list, dict]:
    """The v3.1 items (gold fields untouched; `status` and `near_duplicate` added) and the value
    check of VALUE_CHECKED."""
    checks = {i["id"]: gold_values_found(i, docs) for i in items if i["id"] in VALUE_CHECKED}
    out = []
    for item in items:
        if item["id"] in REMOVED:
            continue
        status = "ACTIVE"
        if item["id"] in checks:
            check_row = checks[item["id"]]
            complete = check_row["found"] == check_row["total"]
            if not complete or (item["id"] in PENDING_BY_DEFAULT and not check_row["total"]):
                status = PENDING
        new = {**item, "status": status}
        if item["id"] in NEAR_DUPLICATE:
            new["near_duplicate"] = NEAR_DUPLICATE[item["id"]]
        out.append(new)
    return out, checks


def write_v31() -> int:
    import yaml

    items = verify_frozen()
    pages, problems = heldout_check.load_pages()
    if problems:
        raise ValueError(f"corpus PDFs differ from the manifest: {problems}")
    docs = {code: " ".join(texts) for code, texts in pages.items()}
    v31, checks = derive_v31(items, docs)
    v3_lock = json.loads(LOCK.read_text(encoding="utf-8"))
    document = {
        "version": "heldout_v3_1",
        "derived_from": {"file": "docs/eval/heldout-v3.yaml", "sha256": v3_lock["sha256"]},
        "rule": (
            "DEC-038: v3 minus the items whose source document is not in corpus V2; questions "
            "and gold word for word; status PENDING_AUTHOR_REVIEW items are not run until the "
            "owner clears them in a commit of their own that updates this lock"
        ),
        "removed": sorted(REMOVED),
        "items": v31,
    }
    text = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=10**6)
    reloaded = [
        {k: v for k, v in i.items() if k not in ("status", "near_duplicate")}
        for i in yaml.safe_load(text)["items"]
    ]
    if reloaded != [i for i in items if i["id"] not in REMOVED]:
        raise ValueError("a gold field changed in v3.1")
    HELDOUT_V31.write_text(text, encoding="utf-8", newline="\n")
    lock = {
        "version": "heldout_v3_1",
        "file": "docs/eval/heldout-v3.1.yaml",
        "sha256": hashlib.sha256(HELDOUT_V31.read_bytes()).hexdigest(),
        "frozen_at": date.today().isoformat(),
        "items": len(v31),
        "approved_by": "owner's decisions of 2026-11-18 (DEC-038); gold unchanged from v3",
        "rule": "clearing a PENDING item or any edit needs a commit of its own and a new lock",
    }
    LOCK_V31.write_text(json.dumps(lock, indent=1) + "\n", encoding="utf-8", newline="\n")
    # Ids, counts and flags only.
    print("ID | document in corpus | values found / total | status")
    for item_id, row in sorted(checks.items()):
        status = next(i["status"] for i in v31 if i["id"] == item_id)
        corpus = "yes" if row["in_corpus"] else "no"
        print(f"{item_id} | {corpus} | {row['found']}/{row['total']} | {status}")
    counts = {s: sum(i["status"] == s for i in v31) for s in ("ACTIVE", PENDING)}
    print(f"removed: {sorted(REMOVED)}; items: {len(v31)}; {counts}")
    print(f"near_duplicate: {sorted(NEAR_DUPLICATE)}; lock sha256: {lock['sha256']}")
    return 0


def verify_v31() -> list[dict[str, Any]]:
    return verify_frozen(HELDOUT_V31, LOCK_V31)


def set_status(
    status: str, ids: Sequence[str], heldout: Path = HELDOUT_V31, lock: Path = LOCK_V31
) -> int:
    """DEC-038: resolve PENDING items, ACTIVE once the author confirms, EXCLUDED after the deadline;
    only their status changes, and the lock is rewritten. Prints ids and counts only."""
    import yaml

    if status not in ("ACTIVE", EXCLUDED) or not ids:
        raise ValueError(f"set-status takes ACTIVE or {EXCLUDED} and at least one id")
    verify_frozen(heldout, lock)
    text = heldout.read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    by_id = {item["id"]: item for item in document["items"]}
    for item_id in ids:
        if by_id.get(item_id, {}).get("status") != PENDING:
            raise ValueError(f"{item_id} is not {PENDING}")
        by_id[item_id]["status"] = status
    new = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=10**6)

    def rest(dumped: str) -> list[dict[str, Any]]:
        items = yaml.safe_load(dumped)["items"]
        return [{k: v for k, v in i.items() if k != "status"} for i in items]

    if rest(new) != rest(text) or yaml.safe_load(new).keys() != document.keys():
        raise ValueError("a field other than status would change")
    heldout.write_text(new, encoding="utf-8", newline="\n")
    record = json.loads(lock.read_text(encoding="utf-8"))
    record["sha256"] = hashlib.sha256(heldout.read_bytes()).hexdigest()
    record.setdefault("status_changes", []).append(
        {"ids": sorted(ids), "status": status, "on": date.today().isoformat()}
    )
    lock.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    states = ("ACTIVE", PENDING, EXCLUDED)
    counts = {s: sum(i["status"] == s for i in document["items"]) for s in states}
    print(f"{', '.join(sorted(ids))} -> {status}; {counts}; lock sha256: {record['sha256']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("import").add_argument("workbook", type=Path)
    sub.add_parser("check")
    sub.add_parser("derive-v3.1")
    resolve = sub.add_parser("set-status", help="resolve PENDING v3.1 items (DEC-038)")
    resolve.add_argument("status", choices=("ACTIVE", EXCLUDED))
    resolve.add_argument("ids", nargs="+")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.command == "derive-v3.1":
            return write_v31()
        if args.command == "set-status":
            # The fingerprints carry the v3.1 lock hash, so they are rebuilt with it.
            return set_status(args.status, args.ids) or question_leak.main(["build"])
        return import_workbook(args.workbook) if args.command == "import" else check()
    except (FrozenSetChangedError, question_leak.QuestionSourceError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
