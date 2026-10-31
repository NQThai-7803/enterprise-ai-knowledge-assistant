"""Build the owner's grading sheet for two held-out v1 runs. Never assigns a label.

usage (repo root, project venv):
  python scripts/eval/heldout_grading.py <run1 dir> <run2 dir> <out dir>
      [--stack-manifest artifacts/prompt3d/uat-stack/runtime-manifest.json]

Writes <out>/grading.md, <out>/grading.csv and <out>/metadata.json.
- REVIEW flags (automatic, for the grader's attention only): forbidden string, restricted document
  cited by a role that cannot see it, absent keyword in the answer, language mismatch, empty
  evidence_text, odd glyph in the answer (U+FFFD or a private-use PDF bullet such as U+F0B7),
  the two runs differ, INFRA_ERROR.
- Proxy suggestions (status vs gold, cited documents vs gold) are hints only; the label columns
  stay empty for the owner.
- Run validity: VALID needs 0 INFRA_ERROR, one Ollama server PID that always answered, and no
  latency above 120 s; otherwise INVALID_RESOURCE_PRESSURE with the violating items.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELDOUT = ROOT / "docs" / "eval" / "heldout-v1.yaml"
LOCK = ROOT / "docs" / "eval" / "heldout-v1.lock"
RESTRICTED = {"UAT-GROUNDING-001"}
CAN_SEE_RESTRICTED = {"manager", "admin"}
LATENCY_LIMIT_MS = 120_000
EN_STOPWORDS = {
    "the", "is", "are", "to", "of", "and", "not", "an", "a", "for", "with", "be", "or",
    "does", "do", "this", "that", "policy", "employee", "employees", "their", "from",
}  # fmt: skip
FLAGS = (
    "INFRA_ERROR",
    "FORBIDDEN_HIT",
    "RESTRICTED_DOC_CITED",
    "ABSENT_KEYWORD_HIT",
    "LANGUAGE_MISMATCH",
    "EVIDENCE_EMPTY",
    "ODD_GLYPH",
    "RUNS_DIFFER",
)


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").casefold()).replace("đ", "d")
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def no_answer_message() -> str:
    sys.path.insert(0, str(ROOT))
    from app.core.config import Settings

    return Settings(_env_file=None).chat_no_answer_message


def language_mismatch(question_language: str, answer: str, fixed_no_answer: str) -> bool:
    """Heuristic only: English sentence in a Vietnamese answer, or Vietnamese in an English one."""
    if not answer.strip() or answer.strip() == fixed_no_answer.strip():
        return False
    text = re.sub(r"\[\d+\]", " ", answer)
    letters = [ch for ch in text if ch.isalpha()]
    accented = sum(1 for ch in letters if ord(ch) > 127)
    if question_language == "en":
        return bool(letters) and accented / len(letters) > 0.05
    for sentence in re.split(r"[.!?\n;:]+", text):
        words = re.findall(r"[A-Za-z']+", sentence)
        if (
            len(words) >= 5
            and all(ord(ch) < 128 for ch in sentence)
            and sum(w.casefold() in EN_STOPWORDS for w in words) >= 2
        ):
            return True
    return False


def signature(case: dict, codes: dict[str, str]) -> tuple:
    return (
        case["status"],
        tuple(
            (codes.get(c.get("document_id"), "?"), c.get("page_number")) for c in case["citations"]
        ),
        " ".join((case.get("answer") or "").split()),
    )


def case_flags(item: dict, case: dict, codes: dict[str, str], fixed: str) -> list[str]:
    flags = []
    if case["execution_status"] == "INFRA_ERROR":
        return ["INFRA_ERROR"]
    cited = [codes.get(c.get("document_id"), "?") for c in case["citations"]]
    surface = " ".join(
        [case.get("answer") or ""]
        + [
            " ".join(str(c.get(k) or "") for k in ("document_title", "excerpt", "evidence_text"))
            for c in case["citations"]
        ]
    ).casefold()
    for entry in item.get("forbidden", []):
        if entry["value"].casefold() in surface or (
            entry["type"] == "document" and entry["value"] in cited
        ):
            flags.append("FORBIDDEN_HIT")
            break
    if item["role"] not in CAN_SEE_RESTRICTED and set(cited) & RESTRICTED:
        flags.append("RESTRICTED_DOC_CITED")
    answer_folded = fold(case.get("answer") or "")
    if any(fold(k) in answer_folded for k in item.get("absent_keywords", [])):
        flags.append("ABSENT_KEYWORD_HIT")
    if language_mismatch(item["language"], case.get("answer") or "", fixed):
        flags.append("LANGUAGE_MISMATCH")
    if any(not (c.get("evidence_text") or "").strip() for c in case["citations"]):
        flags.append("EVIDENCE_EMPTY")
    if has_odd_glyph(case.get("answer") or ""):
        flags.append("ODD_GLYPH")
    return flags


def has_odd_glyph(text: str) -> bool:
    return any(ch == "\ufffd" or unicodedata.category(ch) == "Co" for ch in text)


def proxy_suggestions(item: dict, case: dict, codes: dict[str, str]) -> list[str]:
    hints = []
    status = case["status"]
    if status == "INFRA_ERROR":
        return hints
    if status != item["gold_status"]:
        if "ANSWERED_LIMITED" in item.get("acceptable_status", []) and status == "ANSWERED":
            hints.append("answered on an ANSWERED_LIMITED item: check limited_pass / fail_examples")
        else:
            hints.append(f"status {status} differs from gold {item['gold_status']}")
    if status == "ANSWERED" and item["gold_status"] == "ANSWERED":
        allowed = {c["document"] for c in item["gold_citations"]} | {
            c["document"] for c in item.get("acceptable_extra_citations", [])
        }
        gold_docs = {c["document"] for c in item["gold_citations"]}
        cited = {codes.get(c.get("document_id"), "?") for c in case["citations"]}
        if cited - allowed:
            hints.append(f"cites documents outside gold: {sorted(cited - allowed)}")
        if gold_docs - cited:
            hints.append(f"gold documents not cited: {sorted(gold_docs - cited)}")
    return hints


def run_validity(results: dict) -> dict:
    violations = []
    cases = results["cases"]
    infra = [c["id"] for c in cases if c["execution_status"] == "INFRA_ERROR"]
    if infra:
        violations.append({"rule": "INFRA_ERROR", "items": infra})
    slow = [
        c["id"]
        for c in cases
        if c.get("latency_ms") is not None and c["latency_ms"] > LATENCY_LIMIT_MS
    ]
    if slow:
        violations.append({"rule": "LATENCY_OVER_120S", "items": slow})
    pid_sets = {tuple(c["monitor"]["ollama_pids"] or ()) for c in cases if c.get("monitor")}
    down = [c["id"] for c in cases if c.get("monitor") and not c["monitor"]["ollama_up"]]
    if len(pid_sets) > 1 or () in pid_sets or down:
        violations.append(
            {"rule": "OLLAMA_RESTARTED_OR_DOWN", "items": down, "pid_sets": sorted(pid_sets)}
        )
    if not all(c.get("monitor") for c in cases):
        violations.append(
            {"rule": "MONITOR_MISSING", "items": [c["id"] for c in cases if not c.get("monitor")]}
        )
    return {
        "validity": "VALID" if not violations else "INVALID_RESOURCE_PRESSURE",
        "violations": violations,
    }


def fmt_citations(case: dict, codes: dict[str, str]) -> list[str]:
    if not case["citations"]:
        return ["- (no citations)"]
    lines = []
    for c in case["citations"]:
        evidence = (c.get("evidence_text") or "").strip() or "**(empty)**"
        lines.append(
            f"- [{c.get('citation_order')}] {codes.get(c.get('document_id'), '?')} "
            f"p.{c.get('page_number')} — evidence_text: {evidence}"
        )
    return lines


def main() -> int:
    import yaml

    parser = argparse.ArgumentParser()
    parser.add_argument("run1", type=Path)
    parser.add_argument("run2", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--stack-manifest",
        type=Path,
        default=ROOT / "artifacts" / "prompt3d" / "uat-stack" / "runtime-manifest.json",
    )
    args = parser.parse_args()

    items = yaml.safe_load(HELDOUT.read_text(encoding="utf-8"))["items"]
    lock = load_json(LOCK)
    codes = {d["id"]: d["code"] for d in load_json(args.stack_manifest)["documents"]}
    fixed = no_answer_message()
    runs = [load_json(d / "runtime_results.json") for d in (args.run1, args.run2)]
    metas = [load_json(d / "metadata.json") for d in (args.run1, args.run2)]
    for run in runs:
        if run["heldout_sha256"] != lock["sha256"]:
            raise SystemExit("run was not made on the frozen held-out file")
    by_run = [{c["id"]: c for c in run["cases"]} for run in runs]
    validity = [run_validity(run) for run in runs]

    rows, md = [], []
    for item in items:
        c1, c2 = by_run[0][item["id"]], by_run[1][item["id"]]
        flags1, flags2 = case_flags(item, c1, codes, fixed), case_flags(item, c2, codes, fixed)
        differ = signature(c1, codes) != signature(c2, codes)
        flags = sorted(set(flags1) | set(flags2) | ({"RUNS_DIFFER"} if differ else set()))
        hints = sorted(
            set(proxy_suggestions(item, c1, codes)) | set(proxy_suggestions(item, c2, codes))
        )
        rows.append(
            {
                "id": item["id"],
                "group": item["group"],
                "role": item["role"],
                "gold_status": item["gold_status"],
                "acceptable_status": " ".join(item.get("acceptable_status", [])),
                "run1_status": c1["status"],
                "run2_status": c2["status"],
                **{flag: int(flag in flags) for flag in FLAGS},
                "proxy_suggestions": " | ".join(hints),
                "label_run1": "",
                "label_run2": "",
                "notes": "",
            }
        )
        md += [
            "",
            "---",
            "",
            f"## {item['id']} | group {item['group']} | role `{item['role']}`"
            + (f" | pair `{item['pair_id']}`" if item.get("pair_id") else ""),
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
            ("ANSWERED_LIMITED passes when all hold", "limited_pass"),
            ("FAIL examples", "fail_examples"),
            ("LEAK examples (grader decides)", "leak_examples"),
        ):
            if item.get(key):
                md += ["", f"**{title}:**"] + [f"- {p}" for p in item[key]]
        if item["gold_citations"]:
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
            f"### Run 1 — `{c1['status']}` ({c1.get('latency_ms')} ms)",
            "",
            f"> {(c1.get('answer') or '').strip() or '(empty)'}",
            "",
        ] + fmt_citations(c1, codes)
        if differ:
            md += [
                "",
                f"### Run 2 — `{c2['status']}` ({c2.get('latency_ms')} ms)"
                " — **differs from run 1**",
                "",
                f"> {(c2.get('answer') or '').strip() or '(empty)'}",
                "",
            ] + fmt_citations(c2, codes)
        else:
            md += ["", f"### Run 2 — same as run 1 ({c2.get('latency_ms')} ms)"]
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

    args.out.mkdir(parents=True, exist_ok=True)
    head = [
        "# Held-out v1 grading sheet (owner)",
        "",
        f"Held-out file SHA256 `{lock['sha256']}` (frozen commit `{lock['frozen_commit'][:7]}`). "
        f"System: image `{metas[0]['api_image'][7:19]}` built from commit "
        f"`{metas[0]['api_image_commit'][:7]}`. Two runs, baseline v2 protocol.",
        "",
        "Groups B and C are **RBAC smoke-level**: one restricted document of about 100 characters",
        "(text cut mid-word) and manager access equal to admin.",
        "",
        "REVIEW flags and proxy suggestions are automatic hints. **No label was filled in**; the",
        "owner assigns PASS / PARTIAL / FAIL / LEAK (rubric: heldout-v1-design.md section 7).",
        "",
        "| Run | Validity | INFRA_ERROR | Max latency | Available MB (min-max) | Pagefile % max |",
        "|---|---|---|---|---|---|",
    ]
    for n, (run, val) in enumerate(zip(runs, validity, strict=True), 1):
        mon = [c["monitor"] for c in run["cases"] if c.get("monitor")]
        head.append(
            f"| {n} | {val['validity']} | {run['infra_error_cases']} | "
            f"{max(c['latency_ms'] or 0 for c in run['cases'])} ms | "
            f"{min(m['available_mb'] for m in mon)}-{max(m['available_mb'] for m in mon)} | "
            f"{max(m['pagefile_pct'] for m in mon)} |"
        )
    (args.out / "grading.md").write_text(
        "\n".join(head + md) + "\n", encoding="utf-8", newline="\n"
    )
    with (args.out / "grading.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "heldout": {
            "file": "docs/eval/heldout-v1.yaml",
            "sha256": lock["sha256"],
            "frozen_commit": lock["frozen_commit"],
        },
        "system": {
            "repo_head_at_run": metas[0]["repo_head"],
            "api_image": metas[0]["api_image"],
            "api_image_commit": metas[0]["api_image_commit"],
            "llm": metas[0]["llm"],
            "flags_set_on_api": metas[0]["flags_set_on_api"],
            "settings_in_container": {
                "LLM_PROMPT_TRUNCATION_GUARD_ENABLED": False,
                "RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED": True,
                "WEB_SEARCH_ENABLED": False,
                "LLM_SEED": 20261031,
                "LLM_TEMPERATURE": 0.0,
            },
            "ollama_context_length": (
                "8192 (OLLAMA_CONTEXT_LENGTH on the host; /api/ps saved per run)"
            ),
        },
        "runs": [],
    }
    for n, (run, val, folder) in enumerate(
        zip(runs, validity, (args.run1, args.run2), strict=True), 1
    ):
        ps = load_json(folder / "ollama_ps_before_run.json")
        metadata["runs"].append(
            {
                "run": n,
                "started_at": run["started_at"],
                "finished_at": run["updated_at"],
                "status": run["status"],
                "infra_error_cases": run["infra_error_cases"],
                "warmup": load_json(folder / "warmup.json"),
                "ollama_ps_before_run": [
                    {"name": m["name"], "context_length": m.get("context_length")}
                    for m in ps["models"]
                ],
                **val,
                "per_item": [
                    {
                        "id": c["id"],
                        "status": c["status"],
                        "latency_ms": c.get("latency_ms"),
                        "available_mb": c.get("monitor", {}).get("available_mb"),
                        "pagefile_pct": c.get("monitor", {}).get("pagefile_pct"),
                        "ollama_pids": c.get("monitor", {}).get("ollama_pids"),
                        "ollama_up": c.get("monitor", {}).get("ollama_up"),
                        "sampled_at": c.get("monitor", {}).get("at"),
                    }
                    for c in run["cases"]
                ],
            }
        )
    (args.out / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    print(json.dumps({"validity": [v["validity"] for v in validity], "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
