"""Synthetic offline harness invariants; no model, Docker, or protected data."""

import json

from scripts.release.task0353c2e_eval import _load_manifest
from scripts.release.task0353c2f_eval import (
    MANIFEST,
    apply_decisions,
    choose_threshold,
    extraction_payload,
    parse_extraction,
)


def test_independent_manifest_split_and_review_fields() -> None:
    cases, _ = _load_manifest(MANIFEST)
    assert len(cases) == 36
    assert sum(case["split"] == "final_test" for case in cases) == 24
    assert len({case["id"] for case in cases}) == 36
    assert all(
        case["obligations"]
        and case["materiality"]
        and case["rationale"]
        and case["question"]
        and case["answer"]
        for case in cases
    )
    assert all(case["id"].startswith("F-") for case in cases)


def test_parse_extraction_rejects_malformed_or_empty_obligations() -> None:
    assert parse_extraction("not JSON") is None
    assert (
        parse_extraction(
            '{"obligations": [], "evidence_relevant": true, "unresolved_conflict": false}'
        )
        is None
    )
    assert (
        parse_extraction(
            '{"obligations": ["actor"], "evidence_relevant": true, "unresolved_conflict": false}'
        )
        is not None
    )


def test_extraction_payload_excludes_answer_and_restricted_evidence() -> None:
    case = {
        "question": "Who signs?",
        "answer": "SECRET_ANSWER",
        "authorized_evidence": ["Visible clause"],
        "restricted_evidence": ["SECRET_RESTRICTED"],
        "gold": "ACCEPT",
    }
    payload = extraction_payload(case)
    assert json.loads(payload) == {
        "question": "Who signs?",
        "authorized_evidence": ["Visible clause"],
    }
    assert "SECRET_" not in payload


def test_threshold_uses_development_only() -> None:
    cases = [
        {"id": "dev-good", "gold": "ACCEPT"},
        {"id": "dev-bad", "gold": "REJECT"},
        {"id": "test-bad", "gold": "REJECT"},
    ]
    rows = [
        {"id": "dev-good", "split": "development", "automatic_min": 0.9},
        {"id": "dev-bad", "split": "development", "automatic_min": 0.2},
        {"id": "test-bad", "split": "final_test", "automatic_min": 0.99},
    ]
    assert choose_threshold(cases, rows, "automatic_min") == 0.9


def test_conflict_and_invalid_extraction_never_accept() -> None:
    cases = [
        {
            "id": "conflict", "split": "development", "language": "EN",
            "tags": [], "gold": "UNCERTAIN", "authorized_evidence": ["A", "not A"],
        },
        {
            "id": "invalid", "split": "final_test", "language": "VI",
            "tags": [], "gold": "REJECT", "authorized_evidence": ["A"],
        },
    ]
    existing = [
        {"id": case["id"], "decision": "ACCEPT", "latency_ms": 1.0}
        for case in cases
    ]
    extraction = [
        {
            "id": "conflict",
            "extraction": {
                "obligations": ["A"],
                "evidence_relevant": True,
                "unresolved_conflict": True,
            },
            "failure": None,
            "latency_ms": 1.0,
        },
        {"id": "invalid", "extraction": None, "failure": "INVALID_OUTPUT", "latency_ms": 1.0},
    ]
    scored = [
        {
            "id": case["id"], "oracle_min": 1.0, "automatic_min": 1.0,
            "score_latency_ms": 1.0,
        }
        for case in cases
    ]
    rows = apply_decisions(cases, existing, extraction, scored, 0.5, 0.5)
    assert [row["automatic"] for row in rows] == ["UNCERTAIN", "UNCERTAIN"]
    assert [row["hybrid"] for row in rows] == ["UNCERTAIN", "UNCERTAIN"]
