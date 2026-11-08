"""Check held-out v2 batch 1 and render the owner's gold review. Never runs the RAG system.

usage (repo root, project venv):
  python scripts/eval/heldout_v2_check.py check [--e5-scores scores.json]
  python scripts/eval/heldout_v2_check.py e5-input <folder>     # one file per comparison set

check refuses a question file that differs from its lock, and gold whose questions or ids differ
from it. It verifies every source_excerpt on its PDF page and writes heldout-v2-review.md and
heldout-v2-check.json. Overlap numbers are reported only; they reject nothing.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import heldout_check, question_leak  # noqa: E402

DOCS = ROOT / "docs" / "eval"
QUESTIONS = DOCS / "heldout-v2-questions.yaml"
LOCK = DOCS / "heldout-v2-questions.lock"
GOLD = DOCS / "heldout-v2-gold.yaml"
REVIEW = DOCS / "heldout-v2-review.md"
REPORT = DOCS / "heldout-v2-check.json"
STATUSES = heldout_check.STATUSES
RESTRICTED = heldout_check.RESTRICTED
REFERENCE_SETS = ("uat", "heldout_v1", "relevance", "rbac")


class FrozenSetChangedError(RuntimeError):
    """The question file differs from its lock, so nothing built on it can be compared."""


def _yaml(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def verify_frozen(source: Path = QUESTIONS, lock: Path = LOCK) -> dict[str, Any]:
    if not lock.is_file():
        raise FrozenSetChangedError(f"lock file missing: {lock}")
    expected = json.loads(lock.read_text(encoding="utf-8"))
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != expected["sha256"]:
        raise FrozenSetChangedError(f"{source.name} sha256 {actual} != frozen {expected['sha256']}")
    return expected


def gold_problems(items: Sequence[Mapping[str, Any]], frozen: Mapping[str, str]) -> list[str]:
    problems = []
    if [item["id"] for item in items] != list(frozen):
        problems.append("gold ids differ from the frozen questions")
    for item in items:
        where = item["id"]
        if item["question"] != frozen.get(where):
            problems.append(f"{where}: question differs from the frozen text")
        status = item["gold_status"]
        if status not in STATUSES:
            problems.append(f"{where}: bad gold_status")
        needs_answer = status != "NO_ANSWER"
        needs_missing = status != "ANSWERED"
        if bool(item["gold_answer"]) != needs_answer:
            problems.append(f"{where}: gold_answer does not match {status}")
        if bool(item["gold_citations"]) != needs_answer:
            problems.append(f"{where}: gold_citations do not match {status}")
        if bool(item.get("missing_points")) != needs_missing:
            problems.append(f"{where}: missing_points do not match {status}")
        if (
            status == "ANSWERED_LIMITED" or "ANSWERED_LIMITED" in item.get("acceptable_status", ())
        ) and not (item.get("limited_pass") and item.get("fail_examples")):
            problems.append(f"{where}: ANSWERED_LIMITED needs limited_pass and fail_examples")
        cited = item["gold_citations"] + item.get("acceptable_extra_citations", [])
        if {entry["document"] for entry in cited} & RESTRICTED:
            problems.append(f"{where}: gold cites a restricted document")
        if not item["forbidden"]:
            problems.append(f"{where}: staff item without forbidden list")
        if not item["source_excerpt"]:
            problems.append(f"{where}: no source excerpt")
    return problems


def overlap(question: str, others: Mapping[str, str]) -> dict[str, Any]:
    """Largest similarity of one question to a set: character 3-gram, difflib, word 4-gram."""
    folded = heldout_check.fold(question)
    grams = heldout_check.trigrams(folded)
    words = set(question_leak.fingerprint(question))
    rows = [
        (
            case_id,
            heldout_check.jaccard(grams, heldout_check.trigrams(heldout_check.fold(text))),
            difflib.SequenceMatcher(None, folded, heldout_check.fold(text)).ratio(),
            heldout_check.jaccard(words, set(question_leak.fingerprint(text))),
        )
        for case_id, text in others.items()
    ]
    tri = max(rows, key=lambda row: row[1])
    seq = max(rows, key=lambda row: row[2])
    four = max(rows, key=lambda row: row[3])
    return {
        "trigram_max": round(tri[1], 3),
        "trigram_nearest": tri[0],
        "difflib_max": round(seq[2], 3),
        "difflib_nearest": seq[0],
        "word4_max": round(four[3], 3),
        "word4_nearest": four[0],
    }


def reference_sets() -> dict[str, dict[str, str]]:
    def questions(path: Path) -> dict[str, str]:
        return {item["id"]: item["question"] for item in _yaml(path)["items"]}

    return {
        "uat": heldout_check.load_uat(),
        "heldout_v1": questions(heldout_check.HELDOUT),
        "relevance": questions(question_leak.RELEVANCE_SOURCE),
        "rbac": questions(question_leak.RBAC_SOURCE),
    }


def _citations(entries: Sequence[Mapping[str, Any]]) -> str:
    return "; ".join(f"{e['document']} tr. {', '.join(map(str, e['pages']))}" for e in entries)


def _overlap_table(
    items: Sequence[Mapping[str, Any]], numbers: Mapping[str, Mapping[str, Any]], e5: Mapping
) -> list[str]:
    lines = [
        "| id | bộ | 3-gram ký tự | difflib | 4-gram từ | e5 cosine |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in items:
        for name in REFERENCE_SETS:
            row = numbers[item["id"]][name]
            cosine = e5.get(name, {}).get(item["id"])
            shown = f"{cosine['cosine_max']} ({cosine['nearest']})" if cosine else "chưa chạy"
            lines.append(
                f"| {item['id']} | {name} | {row['trigram_max']} ({row['trigram_nearest']}) | "
                f"{row['difflib_max']} ({row['difflib_nearest']}) | "
                f"{row['word4_max']} ({row['word4_nearest']}) | {shown} |"
            )
    return lines


def _overlap_summary(numbers: Mapping[str, Mapping[str, Any]], e5: Mapping) -> list[str]:
    """Questions at the v1 review thresholds: 0.60 on surface text, 0.90 on e5."""
    lines = []
    for name in REFERENCE_SETS:
        surface = [
            item_id
            for item_id, row in numbers.items()
            if max(row[name]["trigram_max"], row[name]["difflib_max"], row[name]["word4_max"])
            >= heldout_check.SURFACE_THRESHOLD
        ]
        close = [
            item_id
            for item_id, row in e5.get(name, {}).items()
            if row["cosine_max"] >= heldout_check.E5_THRESHOLD
        ]
        lines.append(
            f"- {name}: bề mặt từ 0,60 trở lên: {', '.join(surface) or 'không có'}; "
            f"e5 từ 0,90 trở lên: {', '.join(close) or 'không có'}"
        )
    return lines


def render_review(
    items: Sequence[Mapping[str, Any]],
    excerpts: Mapping[str, Sequence[Mapping[str, Any]]],
    absent: Mapping[str, Mapping[str, int]],
    numbers: Mapping[str, Mapping[str, Any]],
    e5: Mapping,
    app_hits: Mapping[str, Sequence[str]],
    problems: Sequence[str],
    lock_sha: str,
) -> str:
    total = sum(len(rows) for rows in excerpts.values())
    verified = sum(row["verified"] for rows in excerpts.values() for row in rows)
    decisions = [item["id"] for item in items if item.get("owner_decision")]
    lines = [
        "# Held-out v2, đợt 1: gold chờ duyệt",
        "",
        "Trạng thái: **BẢN NHÁP, chờ chủ dự án duyệt.** Tạo bằng "
        "`scripts/eval/heldout_v2_check.py check` từ `docs/eval/heldout-v2-gold.yaml`; muốn sửa "
        "thì sửa YAML rồi chạy lại. Gold chỉ soạn từ PDF, không chạy hệ thống trên bộ này.",
        "",
        f"Câu hỏi đã đóng băng: SHA256 `{lock_sha}`. Gold chưa đóng băng; sẽ khóa sau khi duyệt.",
        "",
        "Cách duyệt: với mỗi câu, đánh dấu **DUYỆT**, hoặc **SỬA** và ghi nội dung cần đổi.",
        "",
        "## Kiểm tra",
        "",
        f"- Lỗi cấu trúc: {'; '.join(problems) if problems else 'không có'}",
        f"- Đoạn trích khớp đúng trang PDF: {verified}/{total}",
        f"- Câu trùng 4-gram trong `app/`: {dict(app_hits) if app_hits else 'không có'}",
        f"- Câu cần bạn quyết định: {', '.join(decisions) if decisions else 'không có'}",
        "",
    ]
    for item in items:
        lines += [
            f"## {item['id']}: {item['gold_status']}",
            "",
            f"**Câu hỏi:** {item['question']}",
            "",
            "**Ý bắt buộc:**",
        ]
        lines += [f"{n}. {point}" for n, point in enumerate(item["gold_answer"], start=1)] or [
            "- Không có; tài liệu không trả lời được."
        ]
        if item.get("missing_points"):
            lines += ["", "**Tài liệu không nêu:**"]
            lines += [f"- {point}" for point in item["missing_points"]]
        if item.get("gold_optional"):
            lines += ["", "**Ý không bắt buộc:**"]
            lines += [f"- {point}" for point in item["gold_optional"]]
        lines += ["", f"**Citation:** {_citations(item['gold_citations']) or 'không có'}"]
        if item.get("acceptable_extra_citations"):
            lines.append(
                f"**Citation chấp nhận thêm:** {_citations(item['acceptable_extra_citations'])}"
            )
        lines += ["", "**Đoạn trích:**"]
        for row in excerpts[item["id"]]:
            mark = "khớp" if row["verified"] else "KHÔNG KHỚP"
            lines.append(f'- {row["document"]} tr. {row["page"]} ({mark}): "{row["text"]}"')
        if item.get("acceptable_status"):
            lines += ["", f"**Trạng thái chấp nhận thêm:** {', '.join(item['acceptable_status'])}"]
        if item.get("limited_pass"):
            lines += ["", f"**Điều kiện đạt:** {item['limited_pass']}"]
        if item.get("fail_examples"):
            lines += ["", "**Ví dụ không đạt:**"]
            lines += [f"- {example}" for example in item["fail_examples"]]
        if absent.get(item["id"]):
            shown = ", ".join(f"'{key}': {count}" for key, count in absent[item["id"]].items())
            lines += ["", f"**Từ khóa phải vắng, số lần gặp trong tài liệu:** {shown}"]
        if item.get("owner_decision"):
            lines += ["", f"**CẦN BẠN QUYẾT ĐỊNH:** {item['owner_decision']}"]
        if item.get("notes"):
            lines += ["", f"**Ghi chú:** {item['notes']}"]
        lines += ["", "- [ ] DUYỆT", "- [ ] SỬA:", ""]
    lines += [
        "## Kiểm trùng, chỉ báo số liệu",
        "",
        "Số lớn nhất của mỗi câu so với từng bộ, kèm câu gần nhất. Không loại câu nào theo số này.",
        "",
        *_overlap_summary(numbers, e5),
        "",
        *_overlap_table(items, numbers, e5),
        "",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check").add_argument("--e5-scores", type=Path)
    sub.add_parser("e5-input").add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    try:
        lock = verify_frozen()
    except FrozenSetChangedError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    frozen = {item["id"]: item["question"] for item in _yaml(QUESTIONS)["items"]}
    references = reference_sets()
    if args.command == "e5-input":
        args.folder.mkdir(parents=True, exist_ok=True)
        for name in REFERENCE_SETS:
            payload = {"heldout": frozen, "uat": references[name]}
            (args.folder / f"{name}.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        return 0
    items = _yaml(GOLD)["items"]
    problems = gold_problems(items, frozen)
    pages, pdf_problems = heldout_check.load_pages()
    problems += pdf_problems
    excerpts = heldout_check.check_excerpts(items, pages)
    absent = heldout_check.check_absent(items, pages)
    numbers = {
        item_id: {name: overlap(question, references[name]) for name in REFERENCE_SETS}
        for item_id, question in frozen.items()
    }
    e5 = json.loads(args.e5_scores.read_text(encoding="utf-8")) if args.e5_scores else {}
    app_hits = heldout_check.app_fourgram_hits(items)
    REVIEW.write_text(
        render_review(items, excerpts, absent, numbers, e5, app_hits, problems, lock["sha256"]),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "items": len(items),
        "problems": problems,
        "excerpts_not_found": [
            {"id": i, **row} for i, rows in excerpts.items() for row in rows if not row["verified"]
        ],
        "absent_keyword_hits": {i: v for i, v in absent.items() if any(v.values())},
        "app_fourgram_hits": app_hits,
        "overlap": numbers,
        "e5": e5 or "NOT RUN",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key not in ("overlap", "e5")},
            ensure_ascii=False,
            indent=1,
        )
    )
    return 1 if problems or report["excerpts_not_found"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
