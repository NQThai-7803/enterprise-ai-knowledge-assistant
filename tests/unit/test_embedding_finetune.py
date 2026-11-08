"""The embedding fine-tune pipeline (ml/embedding_finetune): the parts that need no model."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "ml" / "embedding_finetune").is_dir():  # the backend image has no ml/
    pytest.skip("ml/ is not in this checkout", allow_module_level=True)

from ml.embedding_finetune import augment, common, eval_retrieval, mine_negatives  # noqa: E402
from ml.embedding_finetune.generate_queries import parse_questions  # noqa: E402
from ml.embedding_finetune.train import examples  # noqa: E402


def test_unaccent_drops_every_diacritic_and_keeps_case() -> None:
    assert common.unaccent("Đơn nghỉ phép năm được duyệt") == "Don nghi phep nam duoc duyet"


def test_variants_are_seeded_and_keep_the_positive() -> None:
    row = {
        "query_id": "c1:0",
        "query": "Nhân viên được nghỉ phép năm bao nhiêu ngày?",
        "positive_chunk_id": "c1",
        "form": "vi",
    }
    first = augment.variants(row, seed=7)
    assert first == augment.variants(row, seed=7)
    forms = {v["form"]: v for v in first}
    assert set(forms) == {"vi_unaccented", "vi_partial", "vi_typo"}
    assert forms["vi_unaccented"]["query"] == "Nhan vien duoc nghi phep nam bao nhieu ngay?"
    partial = forms["vi_partial"]["query"]
    assert partial not in (row["query"], forms["vi_unaccented"]["query"])
    assert all(v["positive_chunk_id"] == "c1" and v["variant_of"] == "c1:0" for v in first)


def test_typo_changes_one_word_by_one_edit() -> None:
    text = "Thời gian thử việc kéo dài bao lâu"
    changed = augment.typo(text, random.Random(3))
    before, after = text.split(" "), changed.split(" ")
    diffs = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert len(diffs) == 1
    original, typo = diffs[0]
    assert len(typo) in (len(original), len(original) - 1)
    assert sorted(typo) == sorted(original) or len(typo) == len(original) - 1


def test_parse_questions_keeps_distinct_questions_of_four_words_or_more() -> None:
    reply = json.dumps({"questions": ["Ai duyệt đơn nghỉ?", "Ai  duyệt đơn nghỉ?", "Ngắn?", 3]})
    assert parse_questions(reply) == ["Ai duyệt đơn nghỉ?"]
    assert parse_questions("not json") == []


def test_negatives_skip_the_positive_its_neighbours_and_identical_text() -> None:
    chunks = {
        "p": {"document_code": "D", "chunk_index": 5, "text": "answer"},
        "n1": {"document_code": "D", "chunk_index": 6, "text": "overlap"},
        "n2": {"document_code": "E", "chunk_index": 0, "text": "answer"},
        "n3": {"document_code": "D", "chunk_index": 9, "text": "other"},
        "n4": {"document_code": "E", "chunk_index": 1, "text": "more"},
    }
    ranked = ["p", "n1", "n2", "unknown", "n3", "n4"]
    assert mine_negatives.pick_negatives(ranked, "p", chunks, 3) == ["n3", "n4"]
    assert mine_negatives.pick_negatives(ranked, "p", chunks, 1) == ["n3"]


def test_training_examples_carry_the_e5_prefixes_and_skip_rows_without_negatives() -> None:
    chunks = {"p": {"text": "P"}, "n": {"text": "N"}}
    rows = [
        {"query": "q1", "positive_chunk_id": "p", "negative_chunk_ids": ["n"]},
        {"query": "q2", "positive_chunk_id": "p", "negative_chunk_ids": []},
    ]
    assert examples(rows, chunks) == [("query: q1", "passage: P", "passage: N")]


def test_scores_count_any_gold_chunk_in_the_top_k() -> None:
    ranked = [["a", "b", "c"], ["x", "y", "g"], ["z"]]
    gold = [{"a"}, {"g"}, {"missing"}]
    result = eval_retrieval.score(ranked, gold)
    assert result["recall@1"] == round(1 / 3, 4)
    assert result["recall@5"] == round(2 / 3, 4)
    assert result["mrr@10"] == round((1 + 1 / 3) / 3, 4)


def test_gold_chunks_are_the_chunks_covering_a_gold_page() -> None:
    chunks = [
        {"chunk_id": "1", "document_code": "D", "page_numbers": [1, 2]},
        {"chunk_id": "2", "document_code": "D", "page_numbers": [3]},
        {"chunk_id": "3", "document_code": "E", "page_numbers": [2]},
    ]
    assert eval_retrieval.gold_chunks([["D", 2]], chunks) == {"1"}


@pytest.mark.repo_layout("scripts/eval/question_fingerprints.json", "docs/eval/heldout-v1.lock")
def test_data_rule_refuses_a_protected_question_and_passes_a_new_one() -> None:
    uat = json.loads((ROOT / "eval-data/uat/questions.json").read_text(encoding="utf-8"))
    protected = uat["items"][0]["question"]
    with pytest.raises(common.DataRuleError):
        common.check_data_rule([protected])
    common.check_data_rule(["Quy trình bàn giao thiết bị cho kho lưu trữ tạm thời diễn ra thế nào"])
