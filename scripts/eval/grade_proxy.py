"""Proxy grade of a Q001-Q100 run against the manually reviewed TASK-035.3B grade.

PROXY ONLY, not a semantic grade. A case is "match" when:
- reference ANSWERED: run is ANSWERED and the set of cited document codes equals the reference set;
- reference NO_ANSWER: run is NO_ANSWER with no citations.
Document IDs are mapped to manifest codes (reference: V2 runtime manifest; run: this stack's).
Also reports whether the answer text is identical to the reference answer.
DEC-032: `value_match` is `proxy_match` that also states every value of the reference answer and no
conflicting one (scripts/eval/value_grading.py); the categories use it.
Cases with execution_status INFRA_ERROR (transport, timeout, 5xx; still failing after the runner's
single end-of-run retry) are excluded from the score: proxy_match is null and the summary lists
how many and which cases were excluded.

Owner grading policy (DEC-037), from the reference and the corpus metadata, never per question:
- a reference may list `accepted_sources`: then any non-empty set of cited codes within that list
  matches (two documents stating the same value, policy 1; on a conflict the list holds only the
  winning document, policy 2);
- a citation of a template or draft (lifecycle_status DRAFT in uat/corpus-v2/manifest.json) never
  matches (policy 3); the row says which in `template_cited`.

usage: grade_proxy.py <reference_grade.json> <v2_runtime_manifest.json> <run_runtime_manifest.json>
                      <run_results.json> <out.json>
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.eval import branch_counters  # noqa: E402
from scripts.eval.branch_counters import coarse_route  # noqa: E402
from scripts.eval.value_grading import regrade  # noqa: E402


def load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def check_lock(path) -> None:
    """A gold file next to a gold.lock (eval-data/uat, DEC-033) must match it byte for byte."""
    import hashlib

    path = Path(path)
    lock_path = path.parent / "gold.lock"
    if not lock_path.is_file():
        return
    expected = json.loads(lock_path.read_text(encoding="utf-8"))["files"].get(path.name)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected != actual:
        raise SystemExit(f"{path} sha256 {actual} differs from {lock_path} ({expected})")


CORPUS_MANIFEST = Path(__file__).resolve().parents[2] / "uat" / "corpus-v2" / "manifest.json"


def draft_codes(path=CORPUS_MANIFEST):
    """Codes of the corpus documents marked DRAFT (templates, drafts; DEC-033)."""
    return frozenset(
        d["code"] for d in load(path)["documents"] if d.get("lifecycle_status") == "DRAFT"
    )


def code_map(manifest):
    return {d["id"]: d["code"] for d in manifest["documents"]}


INFRA_ERROR = "INFRA_ERROR"


def grade(reference, v2_manifest, run_manifest, run, drafts=frozenset()):
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
        accepted = sorted(ref.get("accepted_sources") or ref_cited)
        template_cited = sorted(set(cited) & set(drafts))
        if case.get("execution_status") == INFRA_ERROR:
            match = None
        elif ref["grounding_status"] == "NO_ANSWER":
            match = case.get("status") == "NO_ANSWER" and not cited
        elif template_cited:
            match = False
        elif ref.get("accepted_sources"):
            match = case.get("status") == "ANSWERED" and bool(cited) and set(cited) <= set(accepted)
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
                "accepted_sources": accepted,
                "template_cited": template_cited,
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
                **{field: case.get(field) for field in branch_counters.ROUTE_FIELDS},
                "evidence_similarities": case.get("evidence_similarities"),
            }
        )
    rows = regrade("uat", {"cases": rows})["cases"]
    excluded = [r["id"] for r in rows if r["proxy_match"] is None]
    scored = [r for r in rows if r["proxy_match"] is not None]
    summary = {
        "cases": len(rows),
        "scored_cases": len(scored),
        "excluded_infra_error": len(excluded),
        "excluded_infra_error_ids": excluded,
        "proxy_match": sum(r["proxy_match"] for r in scored),
        "value_match": sum(r["value_match"] for r in scored),
        "status_counts": dict(Counter(r["grounding_status"] for r in rows)),
        "answer_identical_to_reference": sum(r["answer_identical_to_reference"] for r in scored),
        "retried_cases": sum(int(r["attempts"] or 1) > 1 for r in rows),
        # Server-built answers vs the LLM path; None = the stack did not report the route.
        "by_route": {
            str(route): {
                "cases": sum(coarse_route(r["answer_route"]) == route for r in scored),
                "proxy_match": sum(
                    r["proxy_match"] for r in scored if coarse_route(r["answer_route"]) == route
                ),
                "value_match": sum(
                    r["value_match"] for r in scored if coarse_route(r["answer_route"]) == route
                ),
            }
            for route in sorted({coarse_route(r["answer_route"]) for r in scored}, key=str)
        },
        "note": (
            "proxy vs TASK-035.3B manual grade (status + cited document codes); "
            "not a semantic grade; proxy_match counts scored_cases only; "
            "value_match = proxy_match + the reference's values (DEC-032)"
        ),
    }
    return {"summary": summary, "cases": rows}


def main():
    reference, v2_manifest, run_manifest, run, out = sys.argv[1:6]
    check_lock(reference)
    drafts = draft_codes()
    result = grade(load(reference), load(v2_manifest), load(run_manifest), load(run), drafts)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
