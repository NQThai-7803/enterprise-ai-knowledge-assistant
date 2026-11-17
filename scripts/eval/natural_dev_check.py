"""Check natural_dev_v1 and render the owner's gold review. Never runs the RAG system.

usage (repo root, project venv):
  python scripts/eval/natural_dev_check.py [--e5-model-cache data/models]
      [--lock-gold "<owner>"]

Refuses a question file that differs from its lock, and gold whose ids or questions differ from
it. Verifies every source_excerpt on its PDF page (corpus V2) and writes natural_dev_v1_review.md
and natural_dev_v1_check.json next to the set. Overlap with UAT Q001-Q100, held-out v1/v2 and
the dev sets is reported as numbers and nearest ids only (never another set's text) and rejects
nothing; the review thresholds are surface >= 0.60 and e5 >= 0.90 (DEC-026 intake procedure).
--lock-gold writes natural_dev_v1_gold.lock once the owner has approved the gold: it refuses gold
with problems, excerpts not found on their page or an open owner_decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import heldout_check, heldout_v2_check, question_leak  # noqa: E402

SET_DIR = ROOT / "tests" / "acceptance"
QUESTIONS = SET_DIR / "natural_dev_v1.yaml"
LOCK = SET_DIR / "natural_dev_v1.lock"
GOLD = SET_DIR / "natural_dev_v1_gold.yaml"
REVIEW = SET_DIR / "natural_dev_v1_review.md"
REPORT = SET_DIR / "natural_dev_v1_check.json"
GOLD_LOCK = SET_DIR / "natural_dev_v1_gold.lock"
STATUSES = heldout_check.STATUSES
RESTRICTED = heldout_check.RESTRICTED


def _questions(path: Path) -> dict[str, str]:
    return {item["id"]: item["question"] for item in heldout_v2_check._yaml(path)["items"]}


def reference_sets() -> dict[str, dict[str, str]]:
    """Every set the natural questions are compared with; read for the comparison only."""
    return {
        "uat": heldout_check.load_uat(),
        "heldout_v1": _questions(heldout_check.HELDOUT),
        "heldout_v2": _questions(heldout_v2_check.QUESTIONS),
        "relevance": _questions(question_leak.RELEVANCE_SOURCE),
        "rbac": _questions(question_leak.RBAC_SOURCE),
        "false_refusal": _questions(question_leak.FALSE_REFUSAL_SOURCE),
        "false_refusal_v2": _questions(question_leak.FALSE_REFUSAL_V2_SOURCE),
        "compound": _questions(question_leak.COMPOUND_SOURCE),
    }


def gold_problems(items: Sequence[Mapping[str, Any]], frozen: Mapping[str, str]) -> list[str]:
    problems = []
    if [item["id"] for item in items] != list(frozen):
        problems.append("gold ids differ from the frozen questions")
    for item in items:
        where, status = item["id"], item["gold_status"]
        if item["question"] != frozen.get(where):
            problems.append(f"{where}: question differs from the frozen text")
        if status not in STATUSES:
            problems.append(f"{where}: bad gold_status")
        answered = status != "NO_ANSWER"
        if bool(item.get("gold_answer")) != answered or bool(item.get("gold_citations")) != (
            answered
        ):
            problems.append(f"{where}: gold_answer/gold_citations do not match {status}")
        if bool(item.get("missing_points")) != (status != "ANSWERED"):
            problems.append(f"{where}: missing_points do not match {status}")
        if status == "ANSWERED_LIMITED" and not (
            item.get("limited_pass") and item.get("fail_examples")
        ):
            problems.append(f"{where}: ANSWERED_LIMITED needs limited_pass and fail_examples")
        cited = item.get("gold_citations", []) + item.get("acceptable_extra_citations", [])
        if {entry["document"] for entry in cited} & RESTRICTED:
            problems.append(f"{where}: gold cites a restricted document")
        if not item.get("forbidden"):
            problems.append(f"{where}: staff item without forbidden list")
        if not item.get("source_excerpt"):
            problems.append(f"{where}: no source excerpt")
    return problems


class GoldNotLockedError(RuntimeError):
    """The gold is not approved and locked, or differs from its lock."""


def lock_gold(
    approved_by: str, refusals: Sequence[str], gold: Path = GOLD, gold_lock: Path = GOLD_LOCK
) -> dict[str, Any]:
    """Write the gold lock; refuses without approved_by, with refusals or an open decision."""
    items = heldout_v2_check._yaml(gold)["items"]
    reasons = list(refusals) + [
        f"{i['id']}: owner_decision open" for i in items if i.get("owner_decision")
    ]
    if not approved_by.strip():
        reasons.append("approved_by is required")
    if reasons:
        raise GoldNotLockedError("; ".join(reasons))
    payload = {
        "version": "natural_dev_v1_gold",
        "file": gold.name,
        "sha256": hashlib.sha256(gold.read_bytes()).hexdigest(),
        "items": len(items),
        "approved_by": approved_by.strip(),
        "locked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rule": "any edit needs a new approval and a new lock",
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    gold_lock.write_text(text, encoding="utf-8", newline="\n")  # LF on every OS
    return payload


def verify_gold(gold: Path = GOLD, gold_lock: Path = GOLD_LOCK) -> dict[str, Any]:
    """The gold lock, once the gold matches it byte for byte and names its approver."""
    if not gold_lock.is_file():
        raise GoldNotLockedError(f"{gold_lock.name} missing: the gold is not approved yet")
    lock = json.loads(gold_lock.read_text(encoding="utf-8"))
    if hashlib.sha256(gold.read_bytes()).hexdigest() != lock.get("sha256"):
        raise GoldNotLockedError("the gold differs from its lock; a new approval is needed")
    if not str(lock.get("approved_by") or "").strip():
        raise GoldNotLockedError("the gold lock has no approved_by")
    return lock


def e5_nearest(
    questions: Mapping[str, str], others: Mapping[str, Mapping[str, str]], cache: str
) -> dict[str, dict[str, dict[str, Any]]]:
    """Per reference set: each question's highest e5 cosine and the nearest id (no text)."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        "intfloat/multilingual-e5-small", device="cpu", cache_folder=cache, local_files_only=True
    )

    def embed(texts: list[str]) -> Any:
        return model.encode([f"query: {t}" for t in texts], normalize_embeddings=True)

    ids = list(questions)
    mine = embed([questions[i] for i in ids])
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for name, texts in others.items():
        other_ids = list(texts)
        sims = mine @ embed([texts[i] for i in other_ids]).T
        result[name] = {
            item_id: {
                "cosine_max": round(float(sims[row].max()), 4),
                "nearest": other_ids[int(sims[row].argmax())],
            }
            for row, item_id in enumerate(ids)
        }
    return result


def flagged(
    numbers: Mapping[str, Mapping[str, Mapping[str, Any]]], e5: Mapping[str, Any]
) -> dict[str, list[str]]:
    """Questions at the review thresholds, per reference set."""
    out: dict[str, list[str]] = {}
    for item_id, per_set in numbers.items():
        for name, row in per_set.items():
            surface = max(row["trigram_max"], row["difflib_max"], row["word4_max"])
            cosine = e5.get(name, {}).get(item_id, {}).get("cosine_max", 0.0)
            if surface >= heldout_check.SURFACE_THRESHOLD or cosine >= heldout_check.E5_THRESHOLD:
                out.setdefault(item_id, []).append(
                    f"{name}: bề mặt {surface} ({row['trigram_nearest']}), e5 "
                    f"{cosine or 'chưa chạy'} ({e5.get(name, {}).get(item_id, {}).get('nearest')})"
                )
    return out


def _cites(entries: Sequence[Mapping[str, Any]]) -> str:
    return "; ".join(f"{e['document']} tr. {', '.join(map(str, e['pages']))}" for e in entries)


def render_review(
    items: Sequence[Mapping[str, Any]],
    excerpts: Mapping[str, Sequence[Mapping[str, Any]]],
    numbers: Mapping[str, Any],
    e5: Mapping[str, Any],
    problems: Sequence[str],
    app_hits: Mapping[str, Sequence[str]],
    lock_sha: str,
) -> str:
    total = sum(len(rows) for rows in excerpts.values())
    verified = sum(row["verified"] for rows in excerpts.values() for row in rows)
    near = flagged(numbers, e5)
    decisions = [item["id"] for item in items if item.get("owner_decision")]
    lines = [
        "# natural_dev_v1: gold chờ duyệt",
        "",
        "Trạng thái: **BẢN NHÁP, chờ chủ dự án duyệt.** Tạo bằng "
        "`scripts/eval/natural_dev_check.py` từ `tests/acceptance/natural_dev_v1_gold.yaml`; "
        "muốn sửa thì sửa YAML rồi chạy lại.",
        "",
        "Gold chỉ soạn từ PDF của corpus V2; chưa chạy hệ thống trên bộ này.",
        "",
        f"Câu hỏi đã đóng băng nguyên văn: SHA256 `{lock_sha}`. Gold sẽ khóa sau khi duyệt.",
        "",
        "Cách duyệt: với mỗi câu, đánh dấu **DUYỆT**, hoặc **SỬA** và ghi nội dung cần đổi.",
        "",
        "## Kiểm tra",
        "",
        f"- Lỗi cấu trúc: {'; '.join(problems) if problems else 'không có'}",
        f"- Đoạn trích khớp đúng trang PDF: {verified}/{total}",
        f"- Câu trùng 4-gram trong `app/`: {dict(app_hits) if app_hits else 'không có'}",
        f"- Câu cần bạn quyết định: {', '.join(decisions) if decisions else 'không có'}",
        "- Câu gần một câu của bộ khác (bề mặt >= 0,60 hoặc e5 >= 0,90): "
        + (", ".join(near) if near else "không có"),
        "",
    ]
    for item in items:
        lines += [f"## {item['id']}: {item['gold_status']}", "", f"**Câu hỏi:** {item['question']}"]
        lines += ["", "**Ý bắt buộc:**"]
        lines += [f"{n}. {p}" for n, p in enumerate(item.get("gold_answer", []), 1)] or [
            "- Không có."
        ]
        for key, title in (
            ("missing_points", "Tài liệu không nêu (phần của câu hỏi)"),
            ("not_stated", "Tài liệu không nói"),
            ("gold_optional", "Ý không bắt buộc"),
        ):
            if item.get(key):
                lines += ["", f"**{title}:**", *[f"- {p}" for p in item[key]]]
        lines += ["", f"**Citation:** {_cites(item.get('gold_citations', [])) or 'không có'}"]
        if item.get("acceptable_extra_citations"):
            lines.append(
                f"**Citation chấp nhận thêm:** {_cites(item['acceptable_extra_citations'])}"
            )
        lines += ["", "**Đoạn trích:**"]
        for row in excerpts[item["id"]]:
            mark = "khớp" if row["verified"] else "KHÔNG KHỚP"
            lines.append(f'- {row["document"]} tr. {row["page"]} ({mark}): "{row["text"]}"')
        if item.get("limited_pass"):
            lines += ["", f"**Điều kiện đạt:** {item['limited_pass']}"]
        if item.get("fail_examples"):
            lines += ["", "**Ví dụ không đạt:**", *[f"- {e}" for e in item["fail_examples"]]]
        if near.get(item["id"]):
            lines += ["", "**Gần câu của bộ khác:** " + "; ".join(near[item["id"]])]
        if item.get("owner_decision"):
            lines += ["", f"**CẦN BẠN QUYẾT ĐỊNH:** {item['owner_decision']}"]
        if item.get("notes"):
            lines += ["", f"**Ghi chú:** {item['notes']}"]
        lines += ["", "- [ ] DUYỆT", "- [ ] SỬA:", ""]
    lines += [
        "## Kiểm trùng, chỉ báo số liệu",
        "",
        "Số lớn nhất của mỗi câu so với từng bộ, kèm id gần nhất. Không loại câu nào theo số này.",
        "",
        "| id | bộ | 3-gram ký tự | difflib | 4-gram từ | e5 cosine |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item_id, per_set in numbers.items():
        for name, row in per_set.items():
            cosine = e5.get(name, {}).get(item_id)
            shown = f"{cosine['cosine_max']} ({cosine['nearest']})" if cosine else "chưa chạy"
            lines.append(
                f"| {item_id} | {name} | {row['trigram_max']} ({row['trigram_nearest']}) | "
                f"{row['difflib_max']} ({row['difflib_nearest']}) | "
                f"{row['word4_max']} ({row['word4_nearest']}) | {shown} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e5-model-cache", help="folder holding multilingual-e5-small")
    parser.add_argument("--lock-gold", metavar="APPROVED_BY", help="lock the approved gold")
    args = parser.parse_args(argv)
    try:
        lock = heldout_v2_check.verify_frozen(QUESTIONS, LOCK)
    except heldout_v2_check.FrozenSetChangedError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    frozen = _questions(QUESTIONS)
    items = heldout_v2_check._yaml(GOLD)["items"]
    problems = gold_problems(items, frozen)
    pages, pdf_problems = heldout_check.load_pages()
    problems += pdf_problems
    excerpts = heldout_check.check_excerpts(items, pages)
    references = reference_sets()
    numbers = {
        item_id: {
            name: heldout_v2_check.overlap(question, texts) for name, texts in references.items()
        }
        for item_id, question in frozen.items()
    }
    e5 = e5_nearest(frozen, references, args.e5_model_cache) if args.e5_model_cache else {}
    app_hits = heldout_check.app_fourgram_hits(items)
    REVIEW.write_text(
        render_review(items, excerpts, numbers, e5, problems, app_hits, lock["sha256"]),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "items": len(items),
        "problems": problems,
        "excerpts_not_found": [
            {"id": i, **row} for i, rows in excerpts.items() for row in rows if not row["verified"]
        ],
        "app_fourgram_hits": app_hits,
        "near_other_sets": flagged(numbers, e5),
        "overlap": numbers,
        "e5": e5 or "NOT RUN",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    shown = {k: v for k, v in report.items() if k not in ("overlap", "e5")}
    print(json.dumps(shown, ensure_ascii=False, indent=1))
    refusals = problems + [
        f"{r['id']}: excerpt not on its page" for r in report["excerpts_not_found"]
    ]
    if args.lock_gold is not None:
        try:
            print(json.dumps(lock_gold(args.lock_gold, refusals), ensure_ascii=False, indent=1))
        except GoldNotLockedError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
    return 1 if refusals else 0


if __name__ == "__main__":
    raise SystemExit(main())
