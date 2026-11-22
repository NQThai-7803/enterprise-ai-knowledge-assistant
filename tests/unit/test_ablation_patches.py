"""PROMPT 6 ablation helpers (scripts/diagnostics); invented data only."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.llm.models import LLMGenerationResult
from scripts.diagnostics import ablation_patches as patches
from scripts.diagnostics.build_oracle import fact_oracle, uat_oracle

ROOT = Path(__file__).resolve().parents[2]


def test_wide_cut_turns_the_first_two_into_the_first_five() -> None:
    hits = patches._WideCut(range(7))
    assert hits[:2] == (0, 1, 2, 3, 4)
    assert hits[:3] == (0, 1, 2) and hits[1] == 1


def test_ablations_are_dot_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_ABLATION", "group5.low_alignment_off")
    assert patches.selected() == {"group5", "low_alignment_off"}
    monkeypatch.setenv("EVAL_ABLATION", "")
    assert patches.selected() == frozenset()


def test_gold_is_a_page_or_a_fact_of_the_gold_document() -> None:
    hit = SimpleNamespace(text="Phí cấp lại thẻ là 50.000 đồng.", page_numbers=(3,))
    assert patches.is_gold(hit, "DOC-1", [{"document": "DOC-1", "pages": [3]}])
    assert patches.is_gold(hit, "DOC-1", [{"document": "DOC-1", "facts": ["50.000 dong"]}])
    assert not patches.is_gold(hit, "DOC-2", [{"document": "DOC-1", "pages": [3]}])
    assert not patches.is_gold(hit, "DOC-1", [{"document": "DOC-1", "pages": [4]}])


def test_oracle_maps_questions_to_their_gold_and_skips_items_to_refuse() -> None:
    questions = {"items": [{"id": "Q1", "question": "Câu một?"}]}
    gold = {"items": {"Q1": [["DOC-1", 4], ["DOC-1", 2], ["DOC-2", 1]]}}
    assert uat_oracle(questions, gold) == {
        "Câu một?": [{"document": "DOC-1", "pages": [2, 4]}, {"document": "DOC-2", "pages": [1]}]
    }
    data = {
        "items": [
            {"question": "A?", "expect": "answer", "document": "D", "fact": "5 phút",
             "fact_alternatives": ["05 phút"], "also_facts": [{"fact": "30 phút"}]},
            {"question": "B?", "expect": "refuse"},
            {"question": "C?", "document": "E", "fact": "17 phút"},
            {"question": "P?", "expect": "partial", "document": "F", "fact": "6 lần"},
        ]
    }  # fmt: skip
    assert fact_oracle(data) == {
        "A?": [{"document": "D", "facts": ["5 phút", "05 phút", "30 phút"]}],
        "C?": [{"document": "E", "facts": ["17 phút"]}],
        "P?": [{"document": "F", "facts": ["6 lần"]}],  # the stated part of a partial item
    }


class _Service:
    def __init__(self) -> None:
        self.generation: Any = None

    async def _draft_from_generation(self, generation: Any, **kwargs: Any) -> str:
        assert kwargs["claims_already_validated"] is True
        self.generation = generation
        return "draft"


def _partial(claims: dict[str, Any], needs: tuple[str, ...]) -> tuple[Any, _Service]:
    service = _Service()
    generation = LLMGenerationResult(
        content="{}", model="m", finish_reason="stop", prompt_tokens=1, completion_tokens=1,
        response_time_ms=1, provider="p",
    )  # fmt: skip
    gas = SimpleNamespace(LLMGenerationResult=LLMGenerationResult)
    draft = asyncio.run(
        patches.partial_draft(
            service, gas, generation, claims,
            information_needs=needs, source_registry=None, current_user=None,
            grounding_question="q",
        )
    )  # fmt: skip
    return draft, service


def test_partial_answer_keeps_validated_parts_and_names_the_missing_ones() -> None:
    claim = SimpleNamespace(answer="Khóa học kéo dài 40 giờ.", citations=("SOURCE_1",))
    draft, service = _partial({"CLAIM_1": claim}, ("Khóa học dài bao lâu?", "Học phí bao nhiêu?"))
    assert draft == "draft"
    content = json.loads(service.generation.content)
    assert content == {
        "answer": "Khóa học kéo dài 40 giờ. "
        "Tài liệu bạn được phép truy cập không đề cập: Học phí bao nhiêu",
        "citations": ["SOURCE_1"],
    }


@pytest.mark.parametrize("validated", [0, 2])
def test_partial_answer_is_not_built_with_none_or_all_parts_validated(validated: int) -> None:
    claim = SimpleNamespace(answer="a", citations=("SOURCE_1",))
    claims = {f"CLAIM_{i}": claim for i in range(1, validated + 1)}
    draft, _ = _partial(claims, ("x?", "y?"))
    assert draft is None


def _run_site(ablation: str) -> subprocess.CompletedProcess[str]:
    site = ROOT / "scripts" / "diagnostics" / "ablation_site"
    env = {**os.environ, "EVAL_ABLATION": ablation}
    env["PYTHONPATH"] = os.pathsep.join([str(site), str(ROOT)])
    code = (
        "import app.services.grounded_answer_service as g;"
        "print(g._filter_low_alignment_documents(((0, 'h', 1.0),)) == ((0, 'h', 1.0),),"
        " g._filter_low_alignment_documents.__name__)"
    )
    return subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=ROOT
    )


def test_sitecustomize_applies_an_ablation_only_when_asked() -> None:
    patched = _run_site("low_alignment_off")
    assert patched.returncode == 0, patched.stderr
    assert patched.stdout.split() == ["True", "<lambda>"]
    plain = _run_site("")
    assert plain.returncode == 0, plain.stderr
    assert plain.stdout.split()[-1] == "_filter_low_alignment_documents"


def test_an_unknown_ablation_stops_the_process() -> None:
    result = _run_site("no_such_ablation")
    assert result.returncode != 0 and "ABLATION failed: unknown ablation" in result.stderr


def test_every_ablation_applies_to_the_current_service(tmp_path: Path) -> None:
    oracle = tmp_path / "oracle.json"
    oracle.write_text(json.dumps({"Câu hỏi?": [{"document": "D", "pages": [1]}]}), "utf-8")
    site = ROOT / "scripts" / "diagnostics" / "ablation_site"
    env = {**os.environ, "EVAL_ABLATION": "oracle.partial_compound.group5.low_alignment_off"}
    env["EVAL_ABLATION"] += ".excerpt_off.deterministic_off"
    env["EVAL_ORACLE_FILE"] = str(oracle)
    env["PYTHONPATH"] = os.pathsep.join([str(site), str(ROOT)])
    code = (
        "import app.services.grounded_answer_service as g;"
        "from app.retrieval.hybrid_service import HybridRetrievalService as H;"
        "s = g.GroundedAnswerService;"
        "print(H.retrieve.__qualname__, s._prepare_prompt_retrieval_hits.__qualname__,"
        " s._compound_draft_with_claim_repair.__qualname__, s._prepare_answer_draft.__qualname__);"
        "import app.chat.context_builder as c;"
        "assert c.query_focused_excerpt('a b', 'Ai ký?') == 'a b'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 0, result.stderr
    assert all(
        name.startswith("_patch") or name.startswith("apply") for name in result.stdout.split()
    )


def test_simple_trace_records_every_draft_and_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.claim_evidence_validation_service as validation
    import app.services.grounded_answer_service as gas
    from scripts.diagnostics import ablation_patches
    from tests.unit.test_simple_answer_mode import GOOD, QUESTION, _ask

    wrong = "Tai trong toi da cua xe toi la 9.900 kg [SOURCE_1]."
    plain_result, _ = _ask(wrong, GOOD)
    trace, oracle = tmp_path / "trace.jsonl", tmp_path / "oracle.json"
    oracle.write_text(json.dumps({QUESTION: [{"document": "DOC-1", "pages": [1]}]}), "utf-8")
    monkeypatch.setenv("EVAL_SIMPLE_TRACE_FILE", str(trace))
    monkeypatch.setenv("EVAL_ORACLE_FILE", str(oracle))

    async def codes(ids: set[Any]) -> dict[Any, str]:
        return dict.fromkeys(ids, "DOC-1")

    monkeypatch.setattr(patches, "_document_codes", codes)
    for method in ("_simple_validate", "_simple_answer_draft", "_simple_claim_similarity"):
        monkeypatch.setattr(gas.GroundedAnswerService, method,
                            getattr(gas.GroundedAnswerService, method))  # fmt: skip
    monkeypatch.setattr(gas, "value_bound_to_subject", gas.value_bound_to_subject)
    monkeypatch.setattr(gas, "_simple_select_hits", gas._simple_select_hits)
    monkeypatch.setattr(
        gas.GroundedAnswerService, "_simple_no_answer", gas.GroundedAnswerService._simple_no_answer
    )
    for name, value in list(vars(validation).items()):  # restored after the test
        if name.startswith("_") and callable(value):
            monkeypatch.setattr(validation, name, value)
    ablation_patches._patch_simple_trace(gas)
    token = patches._question.set(QUESTION)  # apply() sets it around each question
    try:
        result, llm = _ask(wrong, GOOD)
    finally:
        patches._question.reset(token)
    assert llm.calls == 2
    assert result.assistant_message.content == plain_result.assistant_message.content
    first, second, summary = (json.loads(line) for line in trace.read_text("utf-8").splitlines())
    assert (first["outcome"], first["final"]) == ("claim_contradicted", False)
    assert first["draft"] == wrong
    assert first["sentences"][0]["sources"] == ["SOURCE_1"]
    assert first["sentences"][0]["status"] == "CONTRADICTED"
    assert first["sentences"][0]["rule"] == "_numbers_are_contradicted=True"
    assert (second["outcome"], second["whole"]["status"]) == ("answered", "SUPPORTED")
    assert (first["attempt"], second["attempt"]) == (1, 2) and first["similarities"] == []
    assert first["sources"][0]["kind"] == "answer" and "2.500 kg" in first["sources"][0]["text"]
    # one record per question: retrieval, the prompt's chunks, gold ranks, every attempt
    assert summary["kind"] == "question" and "draft" not in summary
    assert (summary["retrieved"], summary["gold_ranks"]) == (1, [1])
    assert summary["gold_codes"] == ["DOC-1"]
    assert summary["selected"][0]["code"] == "DOC-1" and summary["selected"][0]["gold"]
    assert summary["selected"][0]["hybrid"] is not None
    assert (summary["llm_calls"], summary["outcomes"]) == (2, ["claim_contradicted", "answered"])
    assert summary["no_answer_reason"] is None


def test_simple_trace_follows_the_s1_s2_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.claim_evidence_validation_service as validation
    import app.services.grounded_answer_service as gas
    from scripts.diagnostics import ablation_patches
    from tests.unit.test_simple_answer_mode import (
        GOOD,
        OFF_TOPIC,
        S2,
        UNVERIFIED,
        _ask,
        _ByWordEmbeddings,
    )

    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("EVAL_SIMPLE_TRACE_FILE", str(trace))
    monkeypatch.delenv("EVAL_ORACLE_FILE", raising=False)

    async def codes(ids: set[Any]) -> dict[Any, str]:
        return {}

    monkeypatch.setattr(patches, "_document_codes", codes)
    for method in ("_simple_validate", "_simple_answer_draft", "_simple_claim_similarity"):
        monkeypatch.setattr(gas.GroundedAnswerService, method,
                            getattr(gas.GroundedAnswerService, method))  # fmt: skip
    monkeypatch.setattr(gas, "value_bound_to_subject", gas.value_bound_to_subject)
    monkeypatch.setattr(gas, "_simple_select_hits", gas._simple_select_hits)
    monkeypatch.setattr(
        gas.GroundedAnswerService, "_simple_no_answer", gas.GroundedAnswerService._simple_no_answer
    )
    for name, value in list(vars(validation).items()):
        if name.startswith("_") and callable(value):
            monkeypatch.setattr(validation, name, value)
    ablation_patches._patch_simple_trace(gas)
    draft = f"{GOOD} {OFF_TOPIC} {UNVERIFIED}: nguoi kiem dinh [SOURCE_1]."
    _ask(draft, embeddings=_ByWordEmbeddings("2.500"), **S2)
    record, summary = (json.loads(line) for line in trace.read_text("utf-8").splitlines())
    assert record["outcome"] == "answered" and record["attempt"] == 1
    assert summary["kind"] == "question" and not summary["has_gold"]  # no oracle file
    assert [s["absence"] for s in record["sentences"]] == [False, False, True]
    assert [round(s["similarity"], 2) for s in record["similarities"]] == [1.0, 0.0]
    assert record["bindings"] == []  # s4 off


def test_simple_trace_names_the_final_no_answer_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.claim_evidence_validation_service as validation
    import app.services.grounded_answer_service as gas
    from scripts.diagnostics import ablation_patches
    from tests.unit.test_simple_answer_mode import _ask

    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("EVAL_SIMPLE_TRACE_FILE", str(trace))
    monkeypatch.delenv("EVAL_ORACLE_FILE", raising=False)

    async def codes(ids: set[Any]) -> dict[Any, str]:
        return {}

    monkeypatch.setattr(patches, "_document_codes", codes)
    for method in ("_simple_validate", "_simple_answer_draft", "_simple_claim_similarity"):
        monkeypatch.setattr(gas.GroundedAnswerService, method,
                            getattr(gas.GroundedAnswerService, method))  # fmt: skip
    monkeypatch.setattr(gas, "value_bound_to_subject", gas.value_bound_to_subject)
    monkeypatch.setattr(gas, "_simple_select_hits", gas._simple_select_hits)
    monkeypatch.setattr(
        gas.GroundedAnswerService, "_simple_no_answer", gas.GroundedAnswerService._simple_no_answer
    )
    for name, value in list(vars(validation).items()):
        if name.startswith("_") and callable(value):
            monkeypatch.setattr(validation, name, value)
    ablation_patches._patch_simple_trace(gas)
    wrong = "Tai trong toi da cua xe toi la 9.900 kg [SOURCE_1]."
    result, _ = _ask(wrong, wrong)
    assert result.assistant_message.grounding_status == "NO_ANSWER"
    summary = json.loads(trace.read_text("utf-8").splitlines()[-1])
    assert summary["outcomes"] == ["claim_contradicted", "claim_contradicted"]
    assert summary["no_answer_reason"] == "claim_contradicted"


def test_retrieval_oracle_records_the_chosen_chunks_and_calls_no_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.grounded_answer_service as gas

    oracle, trace = tmp_path / "oracle.json", tmp_path / "trace.jsonl"
    oracle.write_text(json.dumps({"Hỏi gì?": [{"document": "DOC-1", "pages": [2]}]}), "utf-8")
    monkeypatch.setenv("EVAL_ORACLE_FILE", str(oracle))
    monkeypatch.setenv("EVAL_SIMPLE_TRACE_FILE", str(trace))
    service = gas.GroundedAnswerService
    monkeypatch.setattr(service, "_simple_answer_draft", service._simple_answer_draft)  # restored
    monkeypatch.setattr(gas, "_chat_retrieval_candidate_top_k", lambda **_: 10)

    async def codes(ids: set[Any]) -> dict[Any, str]:
        return {"d1": "DOC-1", "d2": "DOC-2"}

    monkeypatch.setattr(patches, "_document_codes", codes)

    def hit(chunk: str, document: str, page: int, group: str | None = None) -> Any:
        return SimpleNamespace(
            chunk_id=chunk, document_id=document, page_numbers=(page,), text=f"text {chunk}",
            group_id=group or chunk,
        )  # fmt: skip

    hits = (hit("c1", "d2", 1), hit("c2", "d1", 2, group="c9"), hit("c3", "d1", 5))

    async def retrieve(**_: Any) -> Any:
        return SimpleNamespace(hits=hits)

    fake = SimpleNamespace(
        hybrid_retrieval_service=SimpleNamespace(retrieve=retrieve),
        settings=None,
        retrieval_reranker=None,
        _simple_no_answer=lambda reason: ("no answer", reason),
    )
    patches._patch_retrieval_oracle(gas)
    token = patches._question.set("Hỏi gì?")
    try:
        outcome = asyncio.run(
            service._simple_answer_draft(fake, current_user=None, grounding_question="Hỏi gì?")
        )
    finally:
        patches._question.reset(token)

    assert outcome == ("no answer", "retrieval_oracle")
    (record,) = [json.loads(line) for line in trace.read_text("utf-8").splitlines()]
    assert record["has_gold"] and record["gold_hit"]
    assert [(h["code"], h["gold"], h["row"]) for h in record["hits"]] == [
        ("DOC-2", False, False),
        ("DOC-1", True, True),
        ("DOC-1", False, False),
    ]
