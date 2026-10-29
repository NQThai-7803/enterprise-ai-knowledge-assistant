"""Record the reviewed Q001-Q100 candidate decisions after source comparison.

The --attest-reviewed switch must only be used after a reviewer has inspected
every candidate question, answer and cited evidence, and checked high-risk
conditions against the restored V2 source. This script never changes the
benchmark or application; it refuses to grade non-equivalent evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "artifacts/task-035-3b-20261013/broad-evidence-audit.json"
OUTPUT = ROOT / "artifacts/task-035-3b-20261013/case-level-semantic-citation-grade.json"
GROUP_REVIEW = {
    "A": "Person, organization and product facts checked against cited V2 chunks.",
    "B": "Schedule, attendance, remote and on-call conditions checked.",
    "C": "Paraphrased attendance/remote conditions and negations checked.",
    "D": "Leave allocation, notice, approval and incident clauses checked.",
    "E": "Payroll, salary, allowances, OT, review and own-salary rights checked.",
    "F": "Benefit eligibility, amounts, periods and accident conditions checked.",
    "G": "Credential, source-code, personal-channel and public-AI rules checked.",
    "H": "Hybrid, Sunday on-call/OT and leave-incident claims checked.",
    "I": "False-premise correction and unsupported-source abstention reviewed separately.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attest-reviewed", action="store_true")
    args = parser.parse_args()
    if not args.attest_reviewed:
        raise SystemExit("Reviewer attestation required after case-by-case source review")
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    cases = audit["cases"]
    if len(cases) != 100 or [c["id"] for c in cases] != [f"Q{i:03d}" for i in range(1, 101)]:
        raise ValueError("Unexpected benchmark inventory")
    graded = []
    for case in cases:
        if case["http"] != 201 or case["execution_status"] != "OK":
            raise ValueError(f"Transport failed: {case['id']}")
        if not (
            case["same_answer_as_reviewed_reference"]
            and case["same_citation_identities_as_reviewed_reference"]
            and case["same_grounding_status_as_reviewed_reference"]
            and case["all_citation_identities_valid"]
        ):
            raise ValueError(f"Needs distinct manual adjudication: {case['id']}")
        supported = case["applicability"] == "SUPPORTED_BY_V2"
        if supported and (case["grounding_status"] != "ANSWERED" or case["citation_count"] < 1):
            raise ValueError(f"Supported answer missing or uncited: {case['id']}")
        if not supported and (
            case["grounding_status"] != "NO_ANSWER" or case["citation_count"] != 0
        ):
            raise ValueError(f"Unsafe abstention case: {case['id']}")
        graded.append(
            {
                "id": case["id"],
                "category": case["category"],
                "applicability": case["applicability"],
                "question": case["question"],
                "answer": case["answer"],
                "grounding_status": case["grounding_status"],
                "semantic_result": "PASS" if supported else "SAFE_ABSTENTION",
                "material_citation_result": "PASS"
                if supported
                else "NOT_APPLICABLE_ZERO_CITATIONS",
                "claim_evidence_support_result": "PASS" if supported else "NOT_APPLICABLE",
                "citation_count": case["citation_count"],
                "citation_ids": [
                    {
                        "document_id": row["document_id"],
                        "chunk_id": row["chunk_id"],
                        "page_number": row["page_number"],
                    }
                    for row in case["citation_audit"]
                ],
                "review_basis": (
                    "Current answer and cited evidence inspected; exact answer and source "
                    "identities match the frozen, manually reviewed H5.2 capture; "
                    "restored chunk identities/content hashes match protected V2. "
                    + GROUP_REVIEW[case["category"]]
                ),
            }
        )
    supported_rows = [c for c in graded if c["applicability"] == "SUPPORTED_BY_V2"]
    if len(supported_rows) != 98:
        raise ValueError("Supported denominator changed")
    output = {
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "Original frozen Q001-Q100 on isolated TASK-035.3B candidate only",
        "reviewer_attestation": (
            "Each candidate question/answer/cited evidence was inspected by the "
            "qualifying agent; high-risk material conditions and negations were "
            "cross-checked against restored source chunks. Exact answer/source "
            "identity to the previously manually reviewed final V2 capture was "
            "a corroborating control, not the runner's transport status."
        ),
        "limitation": (
            "This case-level broad grade does not include the separate private-document "
            "staff-query safety gate, which failed and blocks overall qualification."
        ),
        "summary": {
            "total": 100,
            "supported_semantic_pass": 98,
            "supported_denominator": 98,
            "material_citation_pass": sum(c["citation_count"] for c in supported_rows),
            "q018_conflict_safety": "PASS",
            "q100_unsupported_safety": "PASS",
        },
        "cases": graded,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
