"""Held-out v2 release run (phase 3, DEC-012). Prepared 2026-11-15; not run during development.

usage (repo root, project venv):
  python scripts/eval/heldout_v2_release.py gate
  python scripts/eval/heldout_v2_release.py preflight      # stack up; sends no held-out question
  python scripts/eval/heldout_v2_release.py lock-gold --approved-by "<owner>, <date>"
  python scripts/eval/heldout_v2_release.py run --output <dir>/runtime_results.json
  python scripts/eval/heldout_v2_release.py near-uat --output <dir>/near-uat.json
  python scripts/eval/heldout_v2_release.py grading <run1 dir> <run2 dir> <out dir>
      --stack-manifest <runtime-manifest.json> [--near-uat near-uat.json]
  python scripts/eval/heldout_v2_release.py report <out dir>    # after the owner's labels

- gate refuses unless the questions match their lock and the gold is locked with the owner's
  approval (heldout-v2-gold.lock, written by lock-gold once the owner has approved every item).
- run, like run_heldout.py, records answers only; it never grades. One session per item, as its
  role; INFRA_ERROR is retried once at the end.
- grading writes grading.md / grading.csv with automatic REVIEW flags and proxy hints only. The
  label columns stay empty: the owner assigns PASS / PARTIAL / FAIL / LEAK.
- Every sheet and report splits the items into "near UAT" (e5 cosine to the nearest Q001-Q100
  question >= 0.90) and the rest, and states that the owner ran the 20 questions by hand on
  2026-11-11, outside DEC-012 (DEC-022).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval import heldout_grading, heldout_v2_check, reranker_check, run_heldout  # noqa: E402

GOLD_LOCK = heldout_v2_check.DOCS / "heldout-v2-gold.lock"
UAT_QUESTIONS = ROOT / "eval-data" / "uat" / "questions.json"
NEAR_UAT_THRESHOLD = 0.90  # the review threshold of held-out v1 and v2 (heldout_check.E5_THRESHOLD)
LATENCY_LIMIT_MS = heldout_grading.LATENCY_LIMIT_MS
LABELS = ("PASS", "PARTIAL", "FAIL", "LEAK")
NEAR, OTHER = "near_uat", "other"
DEC_022_NOTICE = (
    "**Sự việc phải nêu (DEC-022):** ngày 2026-11-11 owner đã chạy tay 20 câu held-out v2 trên "
    "hệ thống, ngoài quy trình DEC-012. Bản ghi lần chạy đó không có trong repo và không được "
    "dùng để thiết kế bản sửa nào; chỉ ba lỗi hiển thị chung (D2) được lấy từ đó. Vì vậy đây "
    "không phải lần đầu hệ thống gặp bộ câu này."
)


class GateRefusedError(RuntimeError):
    """The release run may not start: the frozen questions or the approved gold do not hold."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _yaml(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def gate(
    *,
    questions: Path = heldout_v2_check.QUESTIONS,
    questions_lock: Path = heldout_v2_check.LOCK,
    gold: Path = heldout_v2_check.GOLD,
    gold_lock: Path = GOLD_LOCK,
) -> dict[str, Any]:
    """The verified question lock and gold lock; raises GateRefusedError otherwise."""
    try:
        frozen_lock = heldout_v2_check.verify_frozen(questions, questions_lock)
    except heldout_v2_check.FrozenSetChangedError as exc:
        raise GateRefusedError(str(exc)) from exc
    if not gold_lock.is_file():
        raise GateRefusedError(
            f"{gold_lock.name} missing: the owner has not approved and locked the gold yet"
        )
    lock = json.loads(gold_lock.read_text(encoding="utf-8"))
    if _sha256(gold) != lock.get("sha256"):
        raise GateRefusedError("the gold differs from its lock; a new approval and lock are needed")
    if not str(lock.get("approved_by") or "").strip():
        raise GateRefusedError("the gold lock has no approved_by")
    frozen = {item["id"]: item["question"] for item in _yaml(questions)["items"]}
    problems = heldout_v2_check.gold_problems(_yaml(gold)["items"], frozen)
    if problems:
        raise GateRefusedError("gold problems: " + "; ".join(problems))
    return {"questions": frozen_lock, "gold": lock}


def lock_gold(
    approved_by: str,
    *,
    questions: Path = heldout_v2_check.QUESTIONS,
    questions_lock: Path = heldout_v2_check.LOCK,
    gold: Path = heldout_v2_check.GOLD,
    gold_lock: Path = GOLD_LOCK,
) -> dict[str, Any]:
    """Write the gold lock once the owner has approved every item. Refuses open decisions."""
    if not approved_by.strip():
        raise GateRefusedError("approved_by is required")
    try:
        heldout_v2_check.verify_frozen(questions, questions_lock)
    except heldout_v2_check.FrozenSetChangedError as exc:
        raise GateRefusedError(str(exc)) from exc
    items = _yaml(gold)["items"]
    frozen = {item["id"]: item["question"] for item in _yaml(questions)["items"]}
    problems = heldout_v2_check.gold_problems(items, frozen)
    open_decisions = [item["id"] for item in items if item.get("owner_decision")]
    if open_decisions:
        problems.append(
            "owner_decision still open (record the decision in notes, then remove it): "
            + ", ".join(open_decisions)
        )
    if problems:
        raise GateRefusedError("; ".join(problems))
    payload = {
        "version": "heldout_v2_gold",
        "file": gold.name,
        "sha256": _sha256(gold),
        "items": len(items),
        "approved_by": approved_by.strip(),
        "locked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rule": "any edit needs a new approval and a new lock",
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    gold_lock.write_text(text, encoding="utf-8", newline="\n")  # LF on every OS
    return payload


def passwords_from_env(environ: Mapping[str, str] = os.environ) -> dict[str, str]:
    """The account passwords the run needs; raises GateRefusedError when one is missing."""
    missing = [r for r in run_heldout.ACCOUNTS if not environ.get(f"EVAL_PASSWORD_{r.upper()}")]
    if missing:
        raise GateRefusedError(
            "set " + ", ".join(f"EVAL_PASSWORD_{role.upper()}" for role in missing)
        )
    return {role: environ[f"EVAL_PASSWORD_{role.upper()}"] for role in run_heldout.ACCOUNTS}


def preflight(args: argparse.Namespace, base_url: str, client_factory: Any = None) -> dict:
    """Every check the run makes before its first question, and one login per role.

    Run #1 (2026-11-15) stopped at the Ollama check after the stack and corpus were up; this
    runs the same checks first, so a failure costs no corpus load and sends no question.
    """
    locks = gate()
    passwords = passwords_from_env()
    checks = reranker_check.guard(args, base_url)  # reranker mode, then Ollama (DEC-014)
    factory = client_factory or (
        lambda role: run_heldout.EvalClient(
            base_url, email=run_heldout.ACCOUNTS[role], password=passwords[role]
        )
    )
    for role in run_heldout.ACCOUNTS:
        client = factory(role)
        try:
            client.login()
        except run_heldout.EvalInfraError as exc:
            raise GateRefusedError(f"login failed for {role}: {exc}") from exc
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                close()
    return {
        "questions_sha256": locks["questions"]["sha256"],
        "gold_sha256": locks["gold"]["sha256"],
        "logins": list(run_heldout.ACCOUNTS),
        **checks,
    }


def merged_items(
    questions: Path = heldout_v2_check.QUESTIONS, gold: Path = heldout_v2_check.GOLD
) -> list[dict[str, Any]]:
    """Frozen question text, with the gold fields of the same id and safe defaults."""
    by_id = {item["id"]: item for item in _yaml(gold)["items"]}
    items = []
    for item in _yaml(questions)["items"]:
        merged = {**by_id.get(item["id"], {}), **item}
        merged.setdefault("role", "staff")
        merged.setdefault("group", "-")
        merged.setdefault("language", "vi")
        merged.setdefault("forbidden", [])
        merged.setdefault("gold_citations", [])
        items.append(merged)
    return items


def near_uat(
    questions: Mapping[str, str], uat: Mapping[str, str], embed: Any = None
) -> dict[str, dict[str, Any]]:
    """Nearest Q001-Q100 question by e5 cosine (query prefix, as heldout_check), per item."""
    if embed is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")

        def embed(texts: Sequence[str]) -> Any:
            return model.encode(
                [f"query: {text}" for text in texts], normalize_embeddings=True, batch_size=16
            )

    held_ids, uat_ids = list(questions), list(uat)
    sims = embed([questions[i] for i in held_ids]) @ embed([uat[i] for i in uat_ids]).T
    out = {}
    for row, item_id in enumerate(held_ids):
        col = int(sims[row].argmax())
        cosine = round(float(sims[row][col]), 4)
        out[item_id] = {
            "cosine_max": cosine,
            "nearest": uat_ids[col],
            "group": NEAR if cosine >= NEAR_UAT_THRESHOLD else OTHER,
        }
    return out


def run_validity(results: Mapping[str, Any]) -> dict[str, Any]:
    """INFRA_ERROR and latency over 120 s. The host monitor of v1 is Windows-only, so the
    Ollama-restart rule is checked from the Ollama log of the job instead (see the workflow)."""
    cases = results["cases"]
    violations = []
    infra = [c["id"] for c in cases if c["execution_status"] == "INFRA_ERROR"]
    if infra:
        violations.append({"rule": "INFRA_ERROR", "items": infra})
    slow = [c["id"] for c in cases if (c.get("latency_ms") or 0) > LATENCY_LIMIT_MS]
    if slow:
        violations.append({"rule": "LATENCY_OVER_120S", "items": slow})
    return {"validity": "VALID" if not violations else "INVALID", "violations": violations}


def build_grading(
    items: Sequence[Mapping[str, Any]],
    runs: Sequence[Mapping[str, Any]],
    codes: Mapping[str, str],
    groups: Mapping[str, Mapping[str, Any]],
    *,
    fixed_no_answer: str,
    header: Sequence[str] = (),
) -> tuple[str, list[dict[str, Any]]]:
    """The owner's grading sheet: flags and hints only, every label left empty."""
    by_run = [{c["id"]: c for c in run["cases"]} for run in runs]
    rows: list[dict[str, Any]] = []
    sections: dict[str, list[str]] = {NEAR: [], OTHER: []}
    for item in items:
        c1, c2 = by_run[0][item["id"]], by_run[1][item["id"]]
        flags1 = heldout_grading.case_flags(item, c1, codes, fixed_no_answer)
        flags2 = heldout_grading.case_flags(item, c2, codes, fixed_no_answer)
        differ = heldout_grading.signature(c1, codes) != heldout_grading.signature(c2, codes)
        flags = sorted(set(flags1) | set(flags2) | ({"RUNS_DIFFER"} if differ else set()))
        hints = sorted(
            set(heldout_grading.proxy_suggestions(item, c1, codes))
            | set(heldout_grading.proxy_suggestions(item, c2, codes))
            | set(page_hints(item, c1, codes))
            | set(page_hints(item, c2, codes))
        )
        near = groups.get(item["id"], {})
        group = near.get("group", OTHER)
        rows.append(
            {
                "id": item["id"],
                "near_uat_group": group,
                "e5_to_uat": near.get("cosine_max", ""),
                "nearest_uat": near.get("nearest", ""),
                "role": item["role"],
                "gold_status": item["gold_status"],
                "acceptable_status": " ".join(item.get("acceptable_status", [])),
                "run1_status": c1["status"],
                "run2_status": c2["status"],
                **{flag: int(flag in flags) for flag in heldout_grading.FLAGS},
                "proxy_suggestions": " | ".join(hints),
                "report_note": item.get("report_note", ""),
                "label_run1": "",
                "label_run2": "",
                "notes": "",
            }
        )
        md = [
            "",
            "---",
            "",
            f"## {item['id']} | role `{item['role']}` | e5 to UAT {near.get('cosine_max', '?')}"
            f" ({near.get('nearest', '?')})",
            "",
            f"**Question** ({item['language']}): {item['question']}",
            "",
            f"**Gold status:** `{item['gold_status']}`"
            + (
                " | acceptable: " + ", ".join(f"`{s}`" for s in item["acceptable_status"])
                if item.get("acceptable_status")
                else ""
            ),
        ]
        for title, key in (
            ("Required points", "gold_answer"),
            ("Optional points", "gold_optional"),
            ("Not stated by the documents", "missing_points"),
            ("ANSWERED_LIMITED passes when", "limited_pass"),
            ("FAIL examples", "fail_examples"),
        ):
            value = item.get(key)
            if value:
                md += ["", f"**{title}:**"] + (
                    [f"- {p}" for p in value] if isinstance(value, list) else [f"- {value}"]
                )
        if item.get("notes"):
            md += ["", f"**Gold notes:** {item['notes']}"]
        if item.get("report_note"):
            md += ["", f"**Report note:** {item['report_note']}"]
        if item.get("gold_citations"):
            md += [
                "",
                "**Gold citations:** "
                + ", ".join(
                    f"{c['document']} p.{','.join(map(str, c['pages']))}"
                    for c in item["gold_citations"]
                ),
            ]
        md += [
            "",
            f"### Run 1: `{c1['status']}` ({c1.get('latency_ms')} ms)",
            "",
            f"> {(c1.get('answer') or '').strip() or '(empty)'}",
            "",
            *heldout_grading.fmt_citations(c1, codes),
        ]
        if differ:
            md += [
                "",
                f"### Run 2: `{c2['status']}` ({c2.get('latency_ms')} ms), **differs from run 1**",
                "",
                f"> {(c2.get('answer') or '').strip() or '(empty)'}",
                "",
                *heldout_grading.fmt_citations(c2, codes),
            ]
        else:
            md += ["", f"### Run 2: same as run 1 ({c2.get('latency_ms')} ms)"]
        md += [
            "",
            "**REVIEW flags (automatic):** " + (", ".join(f"`{f}`" for f in flags) or "none"),
            "",
            "**Proxy suggestions (hints only, not a label):** " + ("; ".join(hints) or "none"),
            "",
            "**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK",
            "",
            "**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK"
            "  (same as run 1 if identical)",
            "",
            "**Notes:** ",
        ]
        sections[group] += md
    near_ids = [r["id"] for r in rows if r["near_uat_group"] == NEAR]
    lines = [
        "# Held-out v2 grading sheet (owner)",
        "",
        DEC_022_NOTICE,
        "",
        "REVIEW flags and proxy suggestions are automatic hints. **No label was filled in**; the",
        "owner assigns PASS / PARTIAL / FAIL / LEAK in this file or in grading.csv.",
        "",
        *header,
        "",
        f"Near UAT (e5 >= {NEAR_UAT_THRESHOLD:.2f} to a Q001-Q100 question): "
        f"{len(near_ids)} items ({', '.join(near_ids) or 'none'}); the rest: "
        f"{len(rows) - len(near_ids)} items. Results must be reported for each group apart.",
        "",
        f"# Group 1: near UAT (e5 >= {NEAR_UAT_THRESHOLD:.2f})",
        *(sections[NEAR] or ["", "(none)"]),
        "",
        "# Group 2: the rest",
        *(sections[OTHER] or ["", "(none)"]),
    ]
    return "\n".join(lines) + "\n", rows


def page_hints(
    item: Mapping[str, Any], case: Mapping[str, Any], codes: Mapping[str, str]
) -> list[str]:
    """A gold document cited only on pages outside its gold pages (the proxy is per document)."""
    if case["status"] != "ANSWERED":
        return []
    cited: dict[str, set[Any]] = {}
    for citation in case["citations"]:
        code = codes.get(citation.get("document_id"), "?")
        cited.setdefault(code, set()).add(citation.get("page_number"))
    hints = []
    for gold in item.get("gold_citations", []):
        pages = cited.get(gold["document"])
        if pages and not pages & set(gold["pages"]):
            hints.append(
                f"{gold['document']} cited on p.{sorted(pages, key=str)} but not on gold "
                f"p.{gold['pages']}"
            )
    return hints


def report(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Counts per group and run from the owner's labels; refuses a sheet with a blank label."""
    blank = [r["id"] for r in rows if not r["label_run1"].strip() or not r["label_run2"].strip()]
    if blank:
        raise GateRefusedError("labels missing for: " + ", ".join(blank))
    bad = [
        r["id"]
        for r in rows
        if {r["label_run1"].strip().upper(), r["label_run2"].strip().upper()} - set(LABELS)
    ]
    if bad:
        raise GateRefusedError("labels outside PASS/PARTIAL/FAIL/LEAK for: " + ", ".join(bad))
    out: dict[str, Any] = {}
    for group in (NEAR, OTHER, "all"):
        members = [r for r in rows if group == "all" or r["near_uat_group"] == group]
        per_run = {}
        for run in ("run1", "run2"):
            labels = [r[f"label_{run}"].strip().upper() for r in members]
            gold_no = [r for r in members if r["gold_status"] == "NO_ANSWER"]
            gold_yes = [r for r in members if r["gold_status"] != "NO_ANSWER"]
            per_run[run] = {
                **{label: labels.count(label) for label in LABELS},
                "items": len(members),
                "false_answers": [r["id"] for r in gold_no if r[f"{run}_status"] == "ANSWERED"],
                "false_refusals": [r["id"] for r in gold_yes if r[f"{run}_status"] == "NO_ANSWER"],
                "leaks": [r["id"] for r in members if r[f"label_{run}"].strip().upper() == "LEAK"],
            }
        out[group] = per_run
    out["report_notes"] = {r["id"]: r["report_note"] for r in rows if r.get("report_note")}
    return out


def render_report(counts: Mapping[str, Any]) -> str:
    lines = [
        "# Held-out v2: kết quả (owner chấm)",
        "",
        DEC_022_NOTICE,
        "",
        "| Nhóm | Lượt | Số câu | PASS | PARTIAL | FAIL | LEAK | Trả lời sai | Từ chối sai |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    names = {NEAR: "gần UAT (e5 ≥ 0,90)", OTHER: "còn lại", "all": "tất cả"}
    for group in (NEAR, OTHER, "all"):
        for run, row in counts[group].items():
            lines.append(
                f"| {names[group]} | {run} | {row['items']} | {row['PASS']} | {row['PARTIAL']} | "
                f"{row['FAIL']} | {row['LEAK']} | {', '.join(row['false_answers']) or '-'} | "
                f"{', '.join(row['false_refusals']) or '-'} |"
            )
    lines += [
        "",
        "Nhóm gần UAT đo gần với bộ dev nên dễ được lợi từ việc tinh chỉnh trên UAT; nhóm còn lại "
        "là tín hiệu chính.",
    ]
    notes = counts.get("report_notes") or {}
    if notes:
        lines += ["", "**Ghi chú từng câu (owner):**"]
        lines += [f"- {item_id}: {note}" for item_id, note in sorted(notes.items())]
    return "\n".join(lines) + "\n"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("gate")
    pre = sub.add_parser("preflight")
    reranker_check.add_arguments(pre)
    lock = sub.add_parser("lock-gold")
    lock.add_argument("--approved-by", required=True)
    runner = sub.add_parser("run")
    reranker_check.add_arguments(runner)
    runner.add_argument("--output", type=Path, required=True)
    runner.add_argument("--delay-seconds", type=float, default=0.5)
    near = sub.add_parser("near-uat")
    near.add_argument("--output", type=Path, required=True)
    grading = sub.add_parser("grading")
    grading.add_argument("run1", type=Path)
    grading.add_argument("run2", type=Path)
    grading.add_argument("out", type=Path)
    grading.add_argument("--stack-manifest", type=Path, required=True)
    grading.add_argument("--near-uat", type=Path)
    rep = sub.add_parser("report")
    rep.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "gate":
            print(json.dumps(gate(), ensure_ascii=False))
            return 0
        if args.command == "preflight":
            base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
            print(json.dumps(preflight(args, base_url), ensure_ascii=False, default=str))
            return 0
        if args.command == "lock-gold":
            print(json.dumps(lock_gold(args.approved_by), ensure_ascii=False))
            return 0
        if args.command == "run":
            locks = gate()
            passwords = passwords_from_env()
            base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
            reranker = reranker_check.guard(args, base_url)
            code = run_heldout.run(
                output=args.output,
                selected=set(),
                resume=False,
                base_url=base_url,
                passwords=passwords,
                delay_seconds=max(0.0, args.delay_seconds),
                run_metadata={**reranker, "gold_sha256": locks["gold"]["sha256"]},
                frozen=locks["questions"],
                all_items=merged_items(),
                label="heldout-v2",
            )
            return reranker_check.finish(args.output, reranker, base_url, code)
        if args.command == "near-uat":
            gate()
            questions = {i["id"]: i["question"] for i in _yaml(heldout_v2_check.QUESTIONS)["items"]}
            uat = {i["id"]: i["question"] for i in _load_json(UAT_QUESTIONS)["items"]}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(near_uat(questions, uat), indent=1) + "\n", encoding="utf-8"
            )
            return 0
        if args.command == "grading":
            locks = gate()
            runs = [_load_json(d / "runtime_results.json") for d in (args.run1, args.run2)]
            for run in runs:
                if run["heldout_sha256"] != locks["questions"]["sha256"]:
                    raise GateRefusedError("a run was not made on the frozen held-out v2 file")
            codes = {d["id"]: d["code"] for d in _load_json(args.stack_manifest)["documents"]}
            groups = _load_json(args.near_uat) if args.near_uat else {}
            validity = [run_validity(run) for run in runs]
            header = [
                f"Questions SHA256 `{locks['questions']['sha256']}`; gold SHA256 "
                f"`{locks['gold']['sha256']}`, approved by {locks['gold']['approved_by']}.",
                "",
                "| Run | Validity | INFRA_ERROR | Max latency |",
                "|---|---|---|---|",
                *(
                    f"| {n} | {v['validity']} | {run['infra_error_cases']} | "
                    f"{max((c.get('latency_ms') or 0) for c in run['cases'])} ms |"
                    for n, (run, v) in enumerate(zip(runs, validity, strict=True), 1)
                ),
            ]
            text, rows = build_grading(
                merged_items(),
                runs,
                codes,
                groups,
                fixed_no_answer=heldout_grading.no_answer_message(),
                header=header,
            )
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / "grading.md").write_text(text, encoding="utf-8", newline="\n")
            with (args.out / "grading.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            (args.out / "metadata.json").write_text(
                json.dumps(
                    {"locks": locks, "validity": validity, "near_uat": groups, "dec_022": True},
                    ensure_ascii=False,
                    indent=1,
                )
                + "\n",
                encoding="utf-8",
            )
            return 0
        if args.command == "report":
            with (args.out / "grading.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            counts = report(rows)
            (args.out / "report.json").write_text(
                json.dumps(counts, indent=1) + "\n", encoding="utf-8"
            )
            (args.out / "report.md").write_text(render_report(counts), encoding="utf-8")
            return 0
    except (
        GateRefusedError,
        run_heldout.HeldoutHashMismatchError,
        reranker_check.RerankerModeRefusedError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
