from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.real_llm_acceptance

_REQUIRED_CASES = {
    "exact_fact",
    "number",
    "date",
    "named_entity",
    "conditional_rule",
    "exception",
    "multi_source_synthesis",
    "paraphrase",
    "unsupported_fact",
    "hallucination_trap",
    "false_premise",
    "cross_document_contamination",
    "existing_work_policy",
    "existing_leave_policy",
    "existing_nova_digital",
    "conversation_memory",
    "streaming",
    "permissions",
    "provider_failure",
    "privacy_logging",
}

_FORBIDDEN_FAKE_VALUES = {
    "fake",
    "fake-openai-provider",
    "uat-deterministic-model",
    "deterministic",
}


def test_real_llm_acceptance_report_is_explicit_and_grounded() -> None:
    if os.getenv("RUN_REAL_LLM_ACCEPTANCE") != "true":
        pytest.skip(
            "Set RUN_REAL_LLM_ACCEPTANCE=true and REAL_LLM_ACCEPTANCE_REPORT "
            "to validate a manual real-LLM acceptance report."
        )

    report_path = os.getenv("REAL_LLM_ACCEPTANCE_REPORT")
    assert report_path, "REAL_LLM_ACCEPTANCE_REPORT must point to a JSON report."
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))

    assert data.get("status") == "COMPLETED"
    assert data.get("fake_provider_used_for_quality_acceptance") is False
    provider = str(data.get("provider", "")).strip().lower()
    model = str(data.get("model", "")).strip().lower()
    assert provider
    assert model
    assert all(value not in provider for value in _FORBIDDEN_FAKE_VALUES)
    assert all(value not in model for value in _FORBIDDEN_FAKE_VALUES)

    cases = data.get("cases")
    assert isinstance(cases, list) and cases
    observed_names = {str(case.get("name", "")) for case in cases}
    assert observed_names >= _REQUIRED_CASES

    for case in cases:
        assert case.get("result") in {"PASS", "NO_ANSWER_PASS"}
        if case.get("grounding_status") == "ANSWERED":
            assert int(case.get("citation_count", 0)) > 0
            citations = case.get("citations")
            assert isinstance(citations, list) and citations
            claims = case.get("claims")
            assert isinstance(claims, list) and claims
            assert all(claim.get("supported") is True for claim in claims)
        else:
            assert case.get("grounding_status") == "NO_ANSWER"
            assert int(case.get("citation_count", 0)) == 0
