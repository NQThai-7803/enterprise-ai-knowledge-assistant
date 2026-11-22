"""Refusal classes of the 2026-11-22 diagnosis (scripts/diagnostics); invented data only."""

from __future__ import annotations

import pytest

from scripts.diagnostics.refusal_classes import classify

QUESTION = "Quỹ đồng phục thu theo quý ra sao?"
REFS = ["Quỹ đồng phục thu 120.000 đồng mỗi quý."]


def summary(*, gold_in_prompt: bool, reason: str | None, has_gold: bool = True) -> dict:
    return {
        "kind": "question",
        "asked": QUESTION,
        "retrieved": 40,
        "selected": [
            {"code": "D-1", "gold": gold_in_prompt, "hybrid": 0.03, "reranker": None},
            {"code": "D-2", "gold": False, "hybrid": 0.02, "reranker": None},
        ],
        "has_gold": has_gold,
        "gold_codes": ["D-1"],
        "gold_ranks": [1] if gold_in_prompt else [9],
        "outcomes": [reason or "answered"],
        "no_answer_reason": reason,
    }


def draft(text: str, *, absence: bool = False, status: str | None = None) -> dict:
    sentence = {"text": text, "absence": absence}
    if status:
        sentence |= {"status": status, "rule": "_numbers_are_contradicted=True"}
    return {
        "asked": QUESTION,
        "draft": text,
        "sentences": [sentence],
        "sources": [{"text": "Quỹ đồng phục thu 120.000 đồng mỗi quý."}],
    }


@pytest.mark.parametrize(
    ("gold_in_prompt", "reason", "label"),
    [
        (False, "claim_insufficient", "retrieval_miss"),
        (True, "claim_irrelevant", "gate_blocked"),
        (True, "refusal_text", "llm_refused"),
        (True, "claim_contradicted", "validator_rejected"),
    ],
)
def test_each_refusal_gets_one_class(gold_in_prompt: bool, reason: str, label: str) -> None:
    case = {"id": "X-1", "status": "NO_ANSWER"}
    records = [draft("Quỹ thu 90.000 đồng [SOURCE_1]."), summary(gold_in_prompt=gold_in_prompt,
                                                            reason=reason)]  # fmt: skip
    row = classify(case, records, QUESTION, REFS)
    assert row["class"] == label
    assert row["src_values"] == "ok"  # the prompt's source states the reference value
    if label == "retrieval_miss":
        assert row["miss"] == "chunk_not_selected"  # D-1 is in the prompt, on other chunks


def test_a_source_with_other_values_still_states_the_reference() -> None:
    record = draft("Quỹ thu 90.000 đồng [SOURCE_1].")
    record["sources"] = [{"text": "Áo 120.000 đồng, mũ 900.000 đồng mỗi quý."}]
    row = classify(
        {"id": "X-1", "status": "NO_ANSWER"},
        [record, summary(gold_in_prompt=True, reason="refusal_text")],
        QUESTION,
        REFS,
    )
    assert row["src_values"] == "ok"


def test_validator_rejection_says_whether_the_draft_was_right() -> None:
    case = {"id": "X-1", "status": "NO_ANSWER"}
    wrong = draft("Quỹ thu 90.000 đồng [SOURCE_1].", status="CONTRADICTED")
    right = draft("Quỹ thu 120.000 đồng [SOURCE_1].", status="INSUFFICIENT")
    for record, values in ((wrong, "conflicting 1"), (right, "ok")):
        row = classify(
            case,
            [record, summary(gold_in_prompt=True, reason="claim_contradicted")],
            QUESTION,
            REFS,
        )
        assert (row["class"], row["draft_values"]) == ("validator_rejected", values)
        assert row["rules"] == ["_numbers_are_contradicted=True"]


def test_answered_and_unclassifiable_items() -> None:
    assert classify({"id": "X", "status": "ANSWERED"}, [], QUESTION, REFS)["class"] == "answered"
    assert classify({"id": "X", "status": "NO_ANSWER"}, [], QUESTION, REFS)["class"] == "no_trace"
    no_gold = [summary(gold_in_prompt=False, reason="refusal_text", has_gold=False)]
    assert classify({"id": "X", "status": "NO_ANSWER"}, no_gold, QUESTION, REFS)["class"] == (
        "no_gold"
    )
