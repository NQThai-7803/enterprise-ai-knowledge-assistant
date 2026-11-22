"""Classify the refusals of a simple-mode run from its simple_trace records. Dev sets only.

usage: python scripts/diagnostics/refusal_classes.py <uat|natural> <run dir>... [--ids ID...]

Each run dir holds the runner's results.json and the simple_trace.jsonl of a configuration with
EVAL_ABLATION=simple_trace and the gold map (ci_batch.sh). Every NO_ANSWER item gets one class,
in this order (fixed before the 2026-11-22 diagnosis):

  retrieval_miss       the question has gold, and no gold chunk is among the prompt's sources;
                       gold_ranks says where retrieval put it ("-" = not retrieved at all) and
                       miss whether the gold document is in the prompt with other chunks
                       (chunk_not_selected) or not at all (document_absent)
  gate_blocked         gold in the prompt, refused by a gate: no_sources, claim_irrelevant (s2),
                       claim_unbound (s4) or permission
  llm_refused          gold in the prompt, the model wrote only absence sentences or the sentinel
  validator_rejected   gold in the prompt, the claim or citation validator rejected every draft
  no_gold / no_trace   cannot be classified

Evidence: the prompt's sources (G = gold), the top hybrid and reranker scores, each LLM attempt's
outcome, whether the prompt's sources state every reference value (src_values: ok / missing n;
other values in a source are no conflict), and for
validator_rejected the last draft's values against the reference (values ok / missing n /
conflicting n) with the validator rule that rejected its claims. Prints IDs, labels, reason codes
and numbers only, never question, gold, source or answer text.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.diagnostics.ablation_patches import question_key  # noqa: E402
from scripts.eval.value_grading import _yaml, check  # noqa: E402

GATES = {"no_sources", "claim_irrelevant", "claim_unbound", "permission"}
MODEL_REFUSALS = {"refusal_text", "llm_refused"}


def references(set_name: str, results: dict[str, Any]) -> dict[str, tuple[str, list[str]]]:
    """id -> (question, reference texts)."""
    if set_name == "uat":
        return {
            case["id"]: (case.get("question") or "", [case.get("reference_answer") or ""])
            for case in results["cases"]
        }
    keys = _yaml("natural_dev_v1_proxy")["items"]
    return {
        item["id"]: (item["question"], [group[0] for group in keys[item["id"]].get("facts", [])])
        for item in _yaml("natural_dev_v1")["items"]
    }


def value_state(text: str, refs: list[str], question: str, *, source: bool = False) -> str:
    checked = check(text, refs, question)
    if not checked["required"]:
        return "no_ref_values"
    if checked["conflicting"] and not source:
        return f"conflicting {len(checked['conflicting'])}"
    if checked["missing"]:
        return f"missing {len(checked['missing'])}/{len(checked['required'])}"
    return "ok"


def classify(case: dict[str, Any], records: list[dict[str, Any]], question: str, refs: list[str]):
    key = question_key(question)
    mine = [r for r in records if question_key(r.get("asked") or "") == key]
    summary = next((r for r in reversed(mine) if r.get("kind") == "question"), None)
    drafts = [r for r in mine if "draft" in r]
    status = case.get("grounding_status") or case.get("status")
    row: dict[str, Any] = {"id": case["id"], "status": status}
    if status != "NO_ANSWER":
        return {**row, "class": "answered"}
    if summary is None:
        return {**row, "class": "no_trace"}
    selected = summary["selected"]
    reason = summary["no_answer_reason"]
    if not summary["has_gold"]:
        label = "no_gold"
    elif not any(source["gold"] for source in selected):
        label = "retrieval_miss"
    elif reason in GATES:
        label = "gate_blocked"
    elif reason in MODEL_REFUSALS:
        label = "llm_refused"
    else:
        label = "validator_rejected"
    sources = drafts[-1]["sources"] if drafts else []
    source_text = " ".join(s["text"] for s in sources)
    if label == "retrieval_miss":
        in_prompt = set(summary["gold_codes"]) & {source["code"] for source in selected}
        row["miss"] = "chunk_not_selected" if in_prompt else "document_absent"
    row |= {
        "class": label,
        "reason": reason,
        "outcomes": summary["outcomes"],
        "retrieved": summary["retrieved"],
        "prompt": " ".join(f"{s['code']}{'(G)' if s['gold'] else ''}" for s in selected),
        "gold_ranks": summary["gold_ranks"][:5] or "-",
        "hybrid": [round(s["hybrid"], 3) for s in selected[:1] + selected[-1:]],
        "reranker": [
            None if s["reranker"] is None else round(s["reranker"], 2)
            for s in selected[:1] + selected[-1:]
        ],
        "src_values": value_state(source_text, refs, question, source=True)
        if sources
        else "no_llm",
    }
    if label == "validator_rejected" and drafts:
        last = drafts[-1]
        claims = " ".join(s["text"] for s in last["sentences"] if not s["absence"])
        rejected = [s for s in last["sentences"] if s.get("status") not in (None, "SUPPORTED")]
        rules = sorted({s.get("rule", "-") for s in rejected})
        row |= {"draft_values": value_state(claims, refs, question), "rules": rules}
    return row


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("set", choices=["uat", "natural"])
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--ids", nargs="*", default=None)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)
    out: dict[str, list[dict[str, Any]]] = {}
    for run in args.runs:
        results = json.loads((run / "results.json").read_text(encoding="utf-8"))
        trace = run / "simple_trace.jsonl"
        records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        refs = references(args.set, results)
        for case in results["cases"]:
            if args.ids and case["id"] not in args.ids:
                continue
            question, reference = refs[case["id"]]
            out.setdefault(case["id"], []).append(classify(case, records, question, reference))
    for case_id, rows in out.items():
        labels = [row["class"] for row in rows]
        stable = "stable" if len(set(labels)) == 1 else "unstable"
        print(case_id, " / ".join(labels), stable)
        for row in rows:
            detail = {k: v for k, v in row.items() if k not in ("id", "status", "class")}
            print("   ", json.dumps(detail, ensure_ascii=False))
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
