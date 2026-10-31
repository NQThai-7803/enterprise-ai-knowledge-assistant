"""Proxy grade of a Q001-Q100 run against the manually reviewed TASK-035.3B grade.

PROXY ONLY, not a semantic grade. A case is "match" when:
- reference ANSWERED: run is ANSWERED and the set of cited document codes equals the reference set;
- reference NO_ANSWER: run is NO_ANSWER with no citations.
Document IDs are mapped to manifest codes (reference: V2 runtime manifest; run: this stack's).
Also reports whether the answer text is identical to the reference answer.
Cases with execution_status INFRA_ERROR (transport, timeout, 5xx; still failing after the runner's
single end-of-run retry) are excluded from the score: proxy_match is null and the summary lists
how many and which cases were excluded.

usage: grade_proxy.py <reference_grade.json> <v2_runtime_manifest.json> <run_runtime_manifest.json>
                      <run_results.json> <out.json>
"""

import json
import sys
from collections import Counter


def load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def code_map(manifest):
    return {d["id"]: d["code"] for d in manifest["documents"]}


INFRA_ERROR = "INFRA_ERROR"


def grade(reference, v2_manifest, run_manifest, run):
    ref_codes = code_map(v2_manifest)
    run_codes = code_map(run_manifest)
    ref_cases = {c["id"]: c for c in reference["cases"]}
    rows = []
    for case in run["cases"]:
        ref = ref_cases[case["id"]]
        cited = sorted(
            {
                run_codes.get(c.get("document_id"), "?" + str(c.get("document_id")))
                for c in case.get("citations", [])
            }
        )
        ref_cited = sorted(
            {ref_codes.get(c["document_id"], "?") for c in ref.get("citation_ids", [])}
        )
        if case.get("execution_status") == INFRA_ERROR:
            match = None
        elif ref["grounding_status"] == "NO_ANSWER":
            match = case.get("status") == "NO_ANSWER" and not cited
        else:
            match = case.get("status") == "ANSWERED" and cited == ref_cited
        rows.append(
            {
                "id": case["id"],
                "category": case.get("category"),
                "grounding_status": case.get("status"),
                "reference_status": ref["grounding_status"],
                "cited_codes": cited,
                "reference_cited_codes": ref_cited,
                "citation_count": len(case.get("citations", [])),
                "question": case.get("question"),
                "answer": case.get("answer"),
                "citations": [
                    {
                        "order": c.get("citation_order"),
                        "document_code": run_codes.get(c.get("document_id")),
                        "document_title": c.get("document_title"),
                        "page_number": c.get("page_number"),
                        "chunk_id": c.get("chunk_id"),
                        "relevance_score": c.get("relevance_score"),
                        "excerpt": c.get("excerpt"),
                        "evidence_text": c.get("evidence_text"),
                    }
                    for c in case.get("citations", [])
                ],
                "reference_answer": ref.get("answer"),
                "answer_identical_to_reference": (case.get("answer") or "").strip()
                == (ref.get("answer") or "").strip(),
                "proxy_match": match,
                "latency_ms": case.get("latency_ms"),
                "execution_status": case.get("execution_status"),
                "attempts": case.get("attempts", 1),
            }
        )
    excluded = [r["id"] for r in rows if r["proxy_match"] is None]
    scored = [r for r in rows if r["proxy_match"] is not None]
    summary = {
        "cases": len(rows),
        "scored_cases": len(scored),
        "excluded_infra_error": len(excluded),
        "excluded_infra_error_ids": excluded,
        "proxy_match": sum(r["proxy_match"] for r in scored),
        "status_counts": dict(Counter(r["grounding_status"] for r in rows)),
        "answer_identical_to_reference": sum(r["answer_identical_to_reference"] for r in scored),
        "retried_cases": sum(int(r["attempts"] or 1) > 1 for r in rows),
        "note": (
            "proxy vs TASK-035.3B manual grade (status + cited document codes); "
            "not a semantic grade; proxy_match counts scored_cases only"
        ),
    }
    return {"summary": summary, "cases": rows}


def main():
    reference, v2_manifest, run_manifest, run, out = sys.argv[1:6]
    result = grade(load(reference), load(v2_manifest), load(run_manifest), load(run))
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
