"""Group Q001-Q100 cases into (a) identical to baseline and (b) changed, after the mojibake fix.

usage: compare_before_after.py <reference_grade.json> <out.json> <out.md>
       <baseline grade_proxy.json>,<baseline grade_proxy.json> <after grade_proxy.json>,<...>

Signature = (grounding_status, ordered (document_code, page) citations, whitespace-normalized
answer). Group (a): both baseline runs and both after runs share one signature; the manual
TASK-035.3B label is carried over. Group (b): anything else, split into
  b1 = baseline runs already differed from each other (run-to-run noise was seen before the fix),
  b2 = baseline runs agreed but an after run differs.
No correctness is assigned to group (b).
"""

import json
import sys


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def signature(case):
    return (
        case["grounding_status"],
        tuple((c["document_code"], c["page_number"]) for c in case["citations"]),
        " ".join((case["answer"] or "").split()),
    )


def brief(case):
    return {
        "grounding_status": case["grounding_status"],
        "cited": [f"{c['document_code']} p{c['page_number']}" for c in case["citations"]],
        "answer": case["answer"],
        "citations": case["citations"],
    }


def main():
    reference = {c["id"]: c for c in load(sys.argv[1])["cases"]}
    out_json, out_md = sys.argv[2], sys.argv[3]
    before = [{c["id"]: c for c in load(p)["cases"]} for p in sys.argv[4].split(",")]
    after = [{c["id"]: c for c in load(p)["cases"]} for p in sys.argv[5].split(",")]
    rows = []
    for case_id in sorted(reference):
        b_sigs = [signature(run[case_id]) for run in before]
        a_sigs = [signature(run[case_id]) for run in after]
        if len(set(b_sigs + a_sigs)) == 1:
            group = "a"
        elif len(set(b_sigs)) > 1:
            group = "b1"
        else:
            group = "b2"
        rows.append(
            {
                "id": case_id,
                "group": group,
                "question": before[0][case_id]["question"],
                "manual_label": reference[case_id]["semantic_result"] if group == "a" else None,
                "reference_answer": reference[case_id]["answer"],
                "before": [brief(run[case_id]) for run in before],
                "after": [brief(run[case_id]) for run in after],
            }
        )
    summary = {
        "cases": len(rows),
        "a_identical": sum(r["group"] == "a" for r in rows),
        "b1_baseline_already_unstable": [r["id"] for r in rows if r["group"] == "b1"],
        "b2_baseline_stable_after_differs": [r["id"] for r in rows if r["group"] == "b2"],
        "a_manual_labels": {
            label: sum(r["manual_label"] == label for r in rows if r["group"] == "a")
            for label in ("PASS", "SAFE_ABSTENTION", "FAIL")
        },
    }
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "cases": rows}, handle, ensure_ascii=False, indent=1)

    lines = [
        "# Group (b): cases that changed after the mojibake fix",
        "",
        "No correctness is assigned here. b1 = baseline runs already differed; "
        "b2 = baseline runs agreed, an after run differs.",
        "",
    ]
    for r in rows:
        if r["group"] == "a":
            continue
        lines += [
            f"## {r['id']} ({r['group']}) {r['question']}",
            "",
            f"Reference answer (035.3B): {r['reference_answer']}",
            "",
        ]
        for name, runs in (("before", r["before"]), ("after", r["after"])):
            for index, run in enumerate(runs, start=1):
                lines.append(
                    f"- **{name} run{index}** {run['grounding_status']} | cited: "
                    f"{', '.join(run['cited']) or '-'}"
                )
                lines.append(f"  - answer: {run['answer']}")
        lines.append("")
    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


main()
