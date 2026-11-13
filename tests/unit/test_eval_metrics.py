"""Eval metrics on made-up cases: definitions, null denominators, labels, leak signals."""

from __future__ import annotations

import pytest

from scripts.eval import metrics
from scripts.eval.metrics import CaseRecord, LabelError

DOC = frozenset({"DOC-A"})


def _yes(case_id: str, status: str = "ANSWERED", grade: str = "PASS", **kwargs) -> CaseRecord:
    defaults = {"cited_docs": DOC, "required_docs": DOC, "allowed_docs": DOC}
    return CaseRecord(case_id, "ANSWERED", status, grade, **{**defaults, **kwargs})


def _no(case_id: str, status: str = "NO_ANSWER", grade: str = "PASS", **kwargs) -> CaseRecord:
    return CaseRecord(case_id, "NO_ANSWER", status, grade, **kwargs)


def _score(records: list[CaseRecord], leak_measured: bool = True) -> dict:
    return metrics.score(records, grade_source=metrics.MANUAL, leak_measured=leak_measured)


def test_rates_use_their_own_denominators() -> None:
    result = _score(
        [
            _yes("A1"),
            _yes("A2", status="NO_ANSWER", grade="FAIL"),
            _yes("A3", grade="PARTIAL"),
            _no("N1"),
            _no("N2", status="ANSWERED", grade="FAIL"),
        ]
    )
    assert result["false_answer_rate"]["value"] == 0.5
    assert result["false_answer_rate"]["ids"] == ["N2"]
    assert result["false_refusal_rate"]["numerator"] == 1
    assert result["false_refusal_rate"]["denominator"] == 3
    assert result["answer_accuracy"]["numerator"] == 2
    assert result["answer_accuracy_with_partial"]["numerator"] == 3


def test_accuracy_is_split_by_gold_status() -> None:
    result = _score([_yes("A1"), _yes("A2", grade="FAIL"), _yes("A3", grade="PARTIAL"), _no("N1")])
    assert result["answerable_accuracy"]["ids"] == ["A1"]
    assert result["answerable_accuracy"]["denominator"] == 3
    assert result["refusal_accuracy"]["ids"] == ["N1"]
    assert result["refusal_accuracy"]["denominator"] == 1
    assert _score([_yes("A1")])["refusal_accuracy"]["value"] is None


def test_empty_denominator_is_null_not_zero() -> None:
    result = _score([_yes("A1")])
    assert result["false_answer_rate"]["value"] is None
    assert result["false_answer_rate"]["denominator"] == 0


def test_infra_error_is_excluded_and_counted() -> None:
    result = _score([_yes("A1"), _yes("A2", status="INFRA_ERROR", grade=None)])
    assert result["scored_cases"] == 1
    assert result["excluded_infra_error"] == ["A2"]
    assert result["answer_accuracy"]["denominator"] == 1


def test_limited_answer_is_a_false_answer_only_when_graded_wrong() -> None:
    result = _score(
        [
            _no("N1", status="ANSWERED", grade="PARTIAL", limited_ok=True),
            _no("N2", status="ANSWERED", grade="FAIL", limited_ok=True),
        ]
    )
    assert result["false_answer_rate"]["ids"] == ["N2"]


@pytest.mark.parametrize(
    ("cited", "correct"),
    [({"DOC-A"}, True), ({"DOC-A", "DOC-X"}, False), (set(), False), ({"DOC-B"}, False)],
)
def test_citation_accuracy_needs_required_and_nothing_outside_allowed(
    cited: set[str], correct: bool
) -> None:
    result = _score([_yes("A1", cited_docs=frozenset(cited))])
    assert result["citation_accuracy"]["numerator"] == int(correct)
    assert result["citation_accuracy"]["denominator"] == 1


def test_citation_accuracy_only_scores_answered_gold_answered_cases() -> None:
    result = _score([_yes("A1", status="NO_ANSWER", grade="FAIL"), _no("N1")])
    assert result["citation_accuracy"]["value"] is None


def test_unmeasured_leak_is_null_and_a_leak_is_counted_when_measured() -> None:
    leaky = _no("N1", status="ANSWERED", grade="LEAK", leak_reasons=("label_leak",))
    assert _score([leaky])["permission_leak_count"] == 1
    assert _score([leaky])["permission_leaks"] == {"N1": ["label_leak"]}
    assert _score([_yes("A1")])["permission_leak_count"] == 0
    assert _score([leaky], leak_measured=False)["permission_leak_count"] is None


def _row(case_id: str = "HO-1", run1: str = "PASS", run2: str = "", differ: str = "0") -> dict:
    return {
        "id": case_id,
        "label_run1": run1,
        "label_run2": run2,
        "RUNS_DIFFER": differ,
        "run1_status": "ANSWERED",
        "run2_status": "ANSWERED",
    }


def test_blank_run2_label_inherits_only_when_the_runs_are_identical() -> None:
    assert metrics.resolve_labels([_row()], 2) == {"HO-1": "PASS"}
    with pytest.raises(LabelError, match="HO-1: blank"):
        metrics.resolve_labels([_row(differ="1")], 2)


def test_missing_or_invalid_label_refuses_to_score() -> None:
    with pytest.raises(LabelError, match="HO-1: blank"):
        metrics.resolve_labels([_row(run1="")], 1)
    with pytest.raises(LabelError, match="HO-1: GOOD"):
        metrics.resolve_labels([_row(run1="good")], 1)


def test_label_is_case_insensitive_and_infra_error_may_stay_blank() -> None:
    assert metrics.resolve_labels([_row(run1="pass")], 1) == {"HO-1": "PASS"}
    row = _row(run1="")
    row["run1_status"] = "INFRA_ERROR"
    assert metrics.resolve_labels([row], 1) == {"HO-1": None}


ITEM = {
    "id": "HO-1",
    "role": "staff",
    "gold_status": "NO_ANSWER",
    "forbidden": [
        {"type": "document", "value": "DOC-F"},
        {"type": "content", "value": "made up secret phrase"},
    ],
}


def _records(citations: list[dict], answer: str = "", label: str = "PASS") -> list[CaseRecord]:
    run = {
        "cases": [
            {
                "id": "HO-1",
                "status": "ANSWERED" if citations or answer else "NO_ANSWER",
                "answer": answer,
                "citations": citations,
            }
        ]
    }
    return metrics.heldout_records(
        [ITEM],
        run,
        {"HO-1": label},
        {"d-f": "DOC-F", "d-r": "DOC-R", "d-a": "DOC-A"},
        {"DOC-R"},
        {"manager"},
    )


def test_leak_signals_from_document_content_restricted_and_label() -> None:
    assert _records([{"document_id": "d-f"}])[0].leak_reasons == ("forbidden_document:DOC-F",)
    assert _records([], answer="A Made Up Secret Phrase.")[0].leak_reasons == ("forbidden_content",)
    assert _records([{"document_id": "d-r"}])[0].leak_reasons == ("restricted_document:DOC-R",)
    assert _records([], label="LEAK")[0].leak_reasons == ("label_leak",)
    assert _records([{"document_id": "d-a"}])[0].leak_reasons == ()


def test_restricted_document_is_allowed_for_a_role_that_can_see_it() -> None:
    item = {**ITEM, "role": "manager"}
    run = {"cases": [{"id": "HO-1", "status": "ANSWERED", "citations": [{"document_id": "d-r"}]}]}
    records = metrics.heldout_records(
        [item], run, {"HO-1": "PASS"}, {"d-r": "DOC-R"}, {"DOC-R"}, {"manager"}
    )
    assert records[0].leak_reasons == ()


def test_grading_sheet_must_cover_exactly_the_heldout_ids() -> None:
    with pytest.raises(LabelError, match="HO-2"):
        metrics.heldout_records([ITEM], {"cases": []}, {"HO-2": "PASS"}, {}, set(), set())


def test_proxy_records_score_as_proxy_with_leak_unmeasured() -> None:
    graded = {
        "cases": [
            {
                "id": "Q1",
                "reference_status": "ANSWERED",
                "grounding_status": "ANSWERED",
                "cited_codes": ["DOC-A"],
                "reference_cited_codes": ["DOC-A"],
                "proxy_match": True,
                "execution_status": "OK",
            },
            {
                "id": "Q2",
                "reference_status": "NO_ANSWER",
                "grounding_status": "ANSWERED",
                "cited_codes": ["DOC-A"],
                "reference_cited_codes": [],
                "proxy_match": False,
                "execution_status": "OK",
            },
            {
                "id": "Q3",
                "reference_status": "ANSWERED",
                "grounding_status": "INFRA_ERROR",
                "cited_codes": [],
                "reference_cited_codes": ["DOC-A"],
                "proxy_match": None,
                "execution_status": "INFRA_ERROR",
            },
        ]
    }
    result = metrics.score(
        metrics.proxy_records(graded), grade_source=metrics.PROXY, leak_measured=False
    )
    assert result["grade_source"] == "proxy"
    assert result["permission_leak_count"] is None
    assert result["false_answer_rate"]["ids"] == ["Q2"]
    assert result["answer_accuracy"]["value"] == 0.5
    assert result["excluded_infra_error"] == ["Q3"]


def test_markdown_shows_null_and_ids_without_any_text_field() -> None:
    results = {"run1": _score([_yes("A1")], leak_measured=False)}
    text = metrics.render_markdown(results)
    assert "null (not measured)" in text
    assert "null (0/0)" in text
    assert "100.0% (1/1)" in text


def test_uat_score_splits_correct_and_wrong_by_answer_route() -> None:
    def row(case_id: str, match: bool, route: str | None) -> dict[str, object]:
        return {
            "id": case_id,
            "reference_status": "ANSWERED",
            "grounding_status": "ANSWERED",
            "cited_codes": ["DOC-A"] if match else ["DOC-B"],
            "reference_cited_codes": ["DOC-A"],
            "proxy_match": match,
            "execution_status": "OK",
            "answer_route": route,
        }

    graded = {"cases": [row("Q1", True, "deterministic"), row("Q2", False, "deterministic"),
                        row("Q3", True, "llm"), row("Q4", True, None)]}  # fmt: skip
    result = metrics.score(
        metrics.proxy_records(graded), grade_source=metrics.PROXY, leak_measured=False
    )
    assert result["by_route"] == {
        "deterministic": {"cases": 2, "correct": ["Q1"], "wrong": ["Q2"]},
        "llm": {"cases": 1, "correct": ["Q3"], "wrong": []},
        "unknown": {"cases": 1, "correct": ["Q4"], "wrong": []},
    }
    text = metrics.render_markdown({"run1": result})
    assert "| route deterministic | 1 correct, 1 wrong |" in text
    without = metrics.score([_yes("A1")], grade_source=metrics.PROXY, leak_measured=False)
    assert without["by_route"] is None
    assert "| route " not in metrics.render_markdown({"run1": without})
