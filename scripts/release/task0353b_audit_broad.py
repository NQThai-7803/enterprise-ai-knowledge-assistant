"""Read-only, case-level evidence audit for the isolated TASK-035.3B broad run.

This does not decide semantic correctness. It compares the frozen, previously
manually reviewed V2 capture and resolves citations against the restored
candidate's persisted chunks so a reviewer can adjudicate every case.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CANDIDATE = ROOT / "artifacts/task-035-3b-20261013/broad-v2-candidate.json"
DEFAULT_REFERENCE = ROOT / "artifacts/uat-corpus-v2/h5-2-broad-v2-final-20261013.json"
DEFAULT_OUTPUT = ROOT / "artifacts/task-035-3b-20261013/broad-evidence-audit.json"
CONTAINER = "enterprise-ai-task0353b-postgres-1"
QUERY = """
SELECT json_agg(row_to_json(x))::text FROM (
  SELECT id::text AS chunk_id, document_id::text AS document_id,
         text, page_numbers, start_page, end_page
  FROM document_chunks ORDER BY id
) x
"""


def compact(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def load_chunks() -> dict[str, dict[str, Any]]:
    raw = subprocess.check_output(
        [
            "docker",
            "exec",
            CONTAINER,
            "psql",
            "-U",
            "task0353b",
            "-d",
            "task0353b",
            "-At",
            "-c",
            QUERY,
        ],
        text=True,
        encoding="utf-8",
    )
    rows = json.loads(raw)
    if len(rows) != 143:
        raise ValueError(f"Expected 143 restored candidate chunks, got {len(rows)}")
    return {row["chunk_id"]: row for row in rows}


def applicability(case_id: str) -> str:
    if case_id == "Q018":
        return "INTENTIONALLY_CONFLICTING"
    if case_id == "Q100":
        return "UNSUPPORTED_BY_V2"
    return "SUPPORTED_BY_V2"


def citation_audit(citation: dict[str, Any], chunks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    chunk_id = str(citation.get("chunk_id") or "")
    document_id = str(citation.get("document_id") or "")
    chunk = chunks.get(chunk_id)
    identity = bool(chunk and chunk["document_id"] == document_id)
    page = citation.get("page_number")
    page_valid = bool(identity and page in chunk["page_numbers"])
    evidence = str(citation.get("evidence_text") or "")
    excerpt = str(citation.get("excerpt") or "")
    evidence_in_chunk = bool(identity and evidence and compact(evidence) in compact(chunk["text"]))
    # Excerpts can be truncated with ellipses; inspect their substantial
    # non-ellipsis segments rather than demanding full-string equality.
    segments = [compact(part) for part in excerpt.replace("...", "…").split("…")]
    segments = [part for part in segments if len(part) >= 12]
    excerpt_segments_in_chunk = bool(
        identity and segments and all(part in compact(chunk["text"]) for part in segments)
    )
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "page_number": page,
        "registry_identity_valid": identity,
        "page_in_chunk": page_valid,
        "evidence_text_in_chunk": evidence_in_chunk if evidence else None,
        "excerpt_segments_in_chunk": excerpt_segments_in_chunk,
        "evidence_text": evidence,
        "excerpt": excerpt,
    }


def run(candidate_path: Path, reference_path: Path, output_path: Path) -> None:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    candidate_cases = candidate["cases"]
    reference_cases = {case["id"]: case for case in reference["cases"]}
    expected = [f"Q{i:03d}" for i in range(1, 101)]
    actual = [case["id"] for case in candidate_cases]
    if actual != expected or set(reference_cases) != set(expected):
        raise ValueError("Candidate or frozen reference inventory is not the exact Q001-Q100 set")
    chunks = load_chunks()
    cases: list[dict[str, Any]] = []
    for case in candidate_cases:
        ref = reference_cases[case["id"]]
        citations = case.get("citations") or []
        source_ids = [(c.get("document_id"), c.get("chunk_id")) for c in citations]
        ref_source_ids = [
            (c.get("document_id"), c.get("chunk_id")) for c in ref.get("citations") or []
        ]
        audit = [citation_audit(citation, chunks) for citation in citations]
        cases.append(
            {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "applicability": applicability(case["id"]),
                "http": case.get("http"),
                "execution_status": case.get("execution_status"),
                "grounding_status": case.get("status"),
                "answer": case.get("answer"),
                "latency_ms": case.get("latency_ms"),
                "citation_count": len(citations),
                "citation_audit": audit,
                "all_citation_identities_valid": all(
                    citation["registry_identity_valid"] and citation["page_in_chunk"]
                    for citation in audit
                ),
                "same_answer_as_reviewed_reference": case.get("answer") == ref.get("answer"),
                "same_citation_identities_as_reviewed_reference": source_ids == ref_source_ids,
                "same_grounding_status_as_reviewed_reference": case.get("status")
                == ref.get("status"),
                "reference_answer": ref.get("answer"),
                "reference_citation_ids": ref_source_ids,
                "semantic_decision": "REQUIRES_SOURCE_REVIEW",
                "materiality_decision": "REQUIRES_SOURCE_REVIEW",
            }
        )
    citation_rows = [citation for case in cases for citation in case["citation_audit"]]
    summary = {
        "case_count": len(cases),
        "applicability": dict(Counter(case["applicability"] for case in cases)),
        "transport_ok": sum(
            case["execution_status"] == "OK" and case["http"] == 201 for case in cases
        ),
        "status_counts": dict(Counter(case["grounding_status"] for case in cases)),
        "citation_count": len(citation_rows),
        "citation_registry_and_page_valid": sum(
            row["registry_identity_valid"] and row["page_in_chunk"] for row in citation_rows
        ),
        "reference_answer_exact": sum(case["same_answer_as_reviewed_reference"] for case in cases),
        "reference_source_ids_exact": sum(
            case["same_citation_identities_as_reviewed_reference"] for case in cases
        ),
        "semantic_review_status": "NOT_AUTOMATICALLY_GRADED",
    }
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "candidate_result": str(candidate_path),
        "reviewed_reference": str(reference_path),
        "candidate_postgres_container": CONTAINER,
        "method": (
            "Read-only registry/page/excerpt checks and exact comparison with "
            "manually reviewed frozen V2 capture; all semantic/material "
            "decisions require source review."
        ),
        "summary": summary,
        "cases": cases,
    }
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing audit: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.candidate, args.reference, args.output)


if __name__ == "__main__":
    main()
