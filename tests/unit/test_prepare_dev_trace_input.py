"""Trace input for the frozen relevance-style dev sets (scripts/diagnostics)."""

from __future__ import annotations

import pytest

from scripts.diagnostics.prepare_dev_trace_input import ALL_PAGES, heldout_v1_items, trace_items


def test_answer_items_take_their_fact_as_gold_and_refuse_items_have_none() -> None:
    data = {
        "items": [
            {
                "id": "X-1",
                "group": "A",
                "expect": "answer",
                "document": "DOC-1",
                "fact": "trưởng phòng",
                "question": "Ai duyệt?",
            },
            {"id": "X-2", "group": "A", "expect": "refuse", "question": "Ai ký?"},
        ]
    }
    answer, refuse = trace_items(data)
    assert answer["role"] == "staff" and answer["gold_status"] == "answer"
    assert answer["excerpts"] == [{"document": "DOC-1", "text": "trưởng phòng"}]
    assert answer["gold_citations"] == [{"document": "DOC-1", "pages": ALL_PAGES}]
    assert refuse["excerpts"] == [] and refuse["gold_citations"] == []
    assert refuse["question"] == "Ai ký?"


def test_heldout_items_keep_their_own_role_and_gold_and_refuse_unknown_ids() -> None:
    raw = [
        {
            "id": "HO-900",
            "role": "manager",
            "group": "X",
            "gold_status": "ANSWERED",
            "question": "Câu hỏi giả?",
            "gold_citations": [{"document": "DOC-1", "pages": [2]}],
            "source_excerpt": [{"document": "DOC-1", "page": 2, "text": "đoạn"}],
        }
    ]
    (item,) = heldout_v1_items(raw, ["HO-900"])
    assert item["role"] == "manager" and item["gold_status"] == "ANSWERED"
    assert item["excerpts"] == raw[0]["source_excerpt"]
    with pytest.raises(SystemExit):
        heldout_v1_items(raw, ["HO-901"])
