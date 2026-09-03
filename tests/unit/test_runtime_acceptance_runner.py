from __future__ import annotations

import json

from tests.acceptance import task_034_1_2_runtime_acceptance as acceptance


def test_cross_document_contract_requires_sources_only_when_claims_need_them() -> None:
    specs = {spec.name: spec for spec in acceptance.cases()}

    assert specs["cross_doc_oncall_sunday"].expectation.min_distinct_docs == 1
    assert specs["cross_doc_leave_incident"].expectation.min_distinct_docs == 1
    assert specs["cross_doc_hybrid_security_allowance"].expectation.min_distinct_docs == 2


def test_rate_limit_is_infrastructure_error_not_semantic_failure() -> None:
    spec = acceptance.cases()[0]
    result = acceptance.evaluate_case(
        spec,
        {
            "http_status": 429,
            "body": {"error": {"code": "RATE_LIMIT_EXCEEDED"}},
            "headers": {"Retry-After": "1"},
        },
        10,
    )

    assert result.status == "INFRA_ERROR"
    assert result.failure_class == "INFRA_RATE_LIMIT"
    assert not result.passed


def test_resume_replays_incomplete_conversation_group(tmp_path, monkeypatch) -> None:
    specs = [spec for spec in acceptance.cases() if spec.session_key == "followup_exec"]
    report_path = tmp_path / "runtime_acceptance_report.json"
    report_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": specs[0].name,
                        "result": "PASS",
                        "http_status": 201,
                        "grounding_status": "ANSWERED",
                        "answer": "Supported [1]",
                        "citations": [{"document_id": "doc", "chunk_id": "chunk"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(acceptance, "REPORT_JSON", report_path)

    assert acceptance.load_resumable_results(specs) == {}
