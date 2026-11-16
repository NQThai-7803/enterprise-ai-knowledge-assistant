from __future__ import annotations

from scripts.eval import heldout_v2_check, natural_dev_check

ITEM = {
    "id": "ND-001",
    "question": "Q?",
    "gold_status": "ANSWERED",
    "gold_answer": ["a"],
    "gold_citations": [{"document": "ND-HR-004", "pages": [5]}],
    "forbidden": [{"document": "UAT-GROUNDING-001", "value": "x"}],
    "source_excerpt": [{"document": "ND-HR-004", "page": 5, "text": "a"}],
}


def test_gold_problems_accept_a_complete_item_and_name_each_gap() -> None:
    assert natural_dev_check.gold_problems([ITEM], {"ND-001": "Q?"}) == []
    limited = {**ITEM, "gold_status": "ANSWERED_LIMITED", "missing_points": ["b"]}
    restricted = {**ITEM, "gold_citations": [{"document": "UAT-GROUNDING-001", "pages": [1]}]}
    problems = natural_dev_check.gold_problems([limited], {"ND-001": "Q changed?"})
    assert any("frozen text" in p for p in problems)
    assert any("limited_pass" in p for p in problems)
    assert any(
        "restricted" in p for p in natural_dev_check.gold_problems([restricted], {"ND-001": "Q?"})
    )


def test_flagged_reports_only_items_at_the_review_thresholds() -> None:
    row = {"trigram_max": 0.2, "trigram_nearest": "Q001", "difflib_max": 0.3, "word4_max": 0.0}
    numbers = {"ND-001": {"uat": {**row, "difflib_max": 0.61}}, "ND-002": {"uat": row}}
    e5 = {"uat": {"ND-002": {"cosine_max": 0.95, "nearest": "Q002"}}}
    assert set(natural_dev_check.flagged(numbers, e5)) == {"ND-001", "ND-002"}
    assert natural_dev_check.flagged({"ND-002": {"uat": row}}, {}) == {}


def test_the_committed_questions_match_their_lock() -> None:
    lock = heldout_v2_check.verify_frozen(natural_dev_check.QUESTIONS, natural_dev_check.LOCK)
    frozen = natural_dev_check._questions(natural_dev_check.QUESTIONS)
    assert lock["items"] == len(frozen) == 20
    assert list(frozen) == [f"ND-{n:03d}" for n in range(1, 21)]
