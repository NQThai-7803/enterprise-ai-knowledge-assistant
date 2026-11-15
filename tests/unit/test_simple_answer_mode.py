"""Simple answer mode (RAG_ANSWER_MODE=simple|simple_det). Invented questions and sources only."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest

from app.chat.context_builder import select_context_for_prompt
from app.chat.models import GroundingStatus
from app.chat.prompt_builder import build_simple_grounded_prompt
from app.citations.errors import CitationFailureCode, CitationValidationError
from app.citations.models import PromptSourceRegistry
from app.llm.models import LLMGenerationResult
from app.observability.metrics import GLOBAL_METRICS
from app.services import claim_evidence_validation_service as validation
from app.services import grounded_answer_service as grounded_answer_module
from app.services.grounded_answer_service import _simple_claim_text, _simple_select_hits
from tests.unit.test_grounded_answer_service import (
    FakeCitationValidationService,
    FakeCounter,
    FakeRetrievalService,
    SequentialFakeLLMProvider,
    chat_session,
    hit,
    make_service,
    retrieval_result,
    settings,
    user,
)

SOURCE = (
    "Quy dinh xe toi. Tai trong toi da cua xe toi la 2.500 kg. Day cap duoc kiem tra 2 lan moi quy."
)
QUESTION = "Xe toi co tai trong toi da the nao?"
GOOD = "Tai trong toi da cua xe toi la 2.500 kg [SOURCE_1]."


def _generation(content: str) -> LLMGenerationResult:
    return LLMGenerationResult(
        content=content, model="fake", finish_reason="stop", prompt_tokens=1,
        completion_tokens=1, response_time_ms=1,
    )  # fmt: skip


class StrictCitationValidation(FakeCitationValidationService):
    """Refuses a marker that is not in the registry, as the real service does."""

    async def validate_and_map(self, *, answer: str, source_registry, current_user):  # noqa: ANN001
        known = {source.marker for source in source_registry.sources}
        import re

        if any(marker not in known for marker in re.findall(r"\[SOURCE_\d+\]", answer)):
            raise CitationValidationError(CitationFailureCode.CITATION_MARKER_UNKNOWN)
        return await super().validate_and_map(
            answer=answer, source_registry=source_registry, current_user=current_user
        )


def _ask(*contents: str, mode: str = "simple", hits: tuple = (), **flags: Any) -> tuple:
    llm = SequentialFakeLLMProvider(*(_generation(c) for c in contents))
    retrieval = FakeRetrievalService(retrieval_result(*(hits or (hit(SOURCE),))))
    service, _, _, _, resolved_llm, _, _ = make_service(
        retrieval=retrieval,
        llm=llm,
        citation_validation=StrictCitationValidation(),
        settings_obj=settings(rag_answer_mode=mode, **flags),
    )
    result = asyncio.run(
        service.answer_question(
            current_user=user(), session_id=chat_session().id, question=QUESTION
        )
    )
    return result, resolved_llm


@pytest.fixture(autouse=True)
def _clean_counters() -> Any:
    GLOBAL_METRICS.reset()
    yield
    GLOBAL_METRICS.reset()


def _hit(doc: int, chunk: int) -> Any:
    return replace(
        hit(f"doc {doc} chunk {chunk}"),
        chunk_id=UUID(int=1000 + 10 * doc + chunk),
        document_id=UUID(int=doc),
    )


def test_simple_takes_the_first_five_chunks_with_at_most_two_per_document() -> None:
    hits = (_hit(1, 1), _hit(1, 2), _hit(1, 3), _hit(2, 1), _hit(1, 4), _hit(3, 1), _hit(2, 2),
            _hit(4, 1))  # fmt: skip
    chosen = _simple_select_hits(hits)
    assert [(h.document_id.int, h.text[-7:]) for h in chosen] == [
        (1, "chunk 1"), (1, "chunk 2"), (2, "chunk 1"), (3, "chunk 1"), (2, "chunk 2"),
    ]  # fmt: skip


def test_whole_chunks_skip_the_query_focused_excerpt(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import context_builder

    monkeypatch.setattr(context_builder, "query_focused_excerpt", lambda text, q, **_: "excerpt")
    common = {"hits": (hit(SOURCE),), "history_messages": (), "question": QUESTION,
              "system_prompt": "s", "token_counter": FakeCounter(), "max_tokens": 1000}  # fmt: skip
    assert select_context_for_prompt(**common).items[0].text == "excerpt"
    assert select_context_for_prompt(**common, whole_chunks=True).items[0].text == SOURCE


def test_the_prompt_keeps_sources_out_of_the_system_message() -> None:
    from app.citations.registry import build_prompt_source_registry

    items = select_context_for_prompt(
        hits=(hit(SOURCE),), history_messages=(), question=QUESTION, system_prompt="s",
        token_counter=FakeCounter(), max_tokens=1000, whole_chunks=True,
    ).items  # fmt: skip
    registry: PromptSourceRegistry = build_prompt_source_registry(
        context_items=items, max_sources=5
    )
    system, user_message = build_simple_grounded_prompt(
        question=QUESTION, source_registry=registry, no_answer_sentinel="__NO_ANSWER__"
    )
    assert system.role == "system" and "2.500 kg" not in system.content
    assert "[SOURCE_1]" in system.content and "Tài liệu không đề cập" in system.content
    assert "SOURCE_1" in user_message.content and "2.500 kg" in user_message.content
    _, retry = build_simple_grounded_prompt(
        question=QUESTION, source_registry=registry, no_answer_sentinel="__NO_ANSWER__",
        retry_reason="it has no source marker.", previous_answer="x " * 500,
    )  # fmt: skip
    assert "Reason: it has no source marker." in retry.content
    assert len(retry.content) < len(user_message.content) + 800  # the old answer is cut


def test_a_supported_answer_with_a_valid_marker_is_answered_in_one_call() -> None:
    result, llm = _ask(GOOD)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1
    assert "[SOURCE_1]" not in result.assistant_message.content  # renumbered by the mapper
    assert GLOBAL_METRICS.answer_branch_counts()["route_llm"] == 1


def test_a_bad_marker_is_retried_once_with_its_reason() -> None:
    result, llm = _ask("Tai trong toi da cua xe toi la 2.500 kg [SOURCE_9].", GOOD)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 2
    assert "Reason: it uses a marker that is not one of the sources" in (
        llm.message_history[1][1].content
    )
    assert GLOBAL_METRICS.answer_branch_counts()["simple_retry"] == 1


@pytest.mark.parametrize(
    ("contents", "reason", "calls"),
    [
        (("Tai trong toi da [SOURCE_9].",) * 2, "citation_invalid", 2),
        (("Tai trong toi da cua xe toi la 2.500 kg.",) * 2, "citation_missing", 2),
        (("Tai trong toi da cua xe toi la 9.900 kg [SOURCE_1].",) * 2, "claim_", 2),
        (("__NO_ANSWER__",), "llm_refused", 1),
        (("Tài liệu không đề cập tải trọng của xe tải.",), "refusal_text", 1),
    ],
)
def test_each_refusal_is_counted_with_its_reason(contents: tuple, reason: str, calls: int) -> None:
    result, llm = _ask(*contents)
    assert result.grounding_status == GroundingStatus.NO_ANSWER and llm.calls == calls
    counted = {k: v for k, v in GLOBAL_METRICS.answer_branch_counts().items() if v}
    assert any(k.startswith(f"simple_no_answer_{reason}") for k in counted), counted
    assert counted.get("simple_retry", 0) == (1 if calls == 2 else 0)


def test_no_retrieved_chunk_refuses_without_calling_the_llm() -> None:
    llm = SequentialFakeLLMProvider(_generation(GOOD))
    service, _, _, _, resolved_llm, _, _ = make_service(
        retrieval=FakeRetrievalService(retrieval_result()),
        llm=llm,
        settings_obj=settings(rag_answer_mode="simple"),
    )
    result = asyncio.run(
        service.answer_question(current_user=user(), session_id=chat_session().id, question="q?")
    )
    assert result.grounding_status == GroundingStatus.NO_ANSWER and resolved_llm.calls == 0
    assert GLOBAL_METRICS.answer_branch_counts()["simple_no_answer_no_sources"] == 1


@pytest.mark.parametrize(("mode", "llm_calls", "deterministic"), [
    ("simple", 1, 0), ("simple_det", 0, 1),
])  # fmt: skip
def test_the_deterministic_route_runs_only_in_simple_det(
    mode: str, llm_calls: int, deterministic: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    def built(**_: Any) -> LLMGenerationResult:
        return replace(
            _generation('{"answer":"Tai trong toi da cua xe toi la 2.500 kg.",'
                        '"citations":["SOURCE_1"]}'),
            model="local-structured-value-repair", provider="local",
        )  # fmt: skip

    monkeypatch.setattr(grounded_answer_module, "_structured_value_repair_generation", built)
    result, llm = _ask(GOOD, mode=mode)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == llm_calls
    assert GLOBAL_METRICS.answer_branch_counts()["simple_deterministic"] == deterministic


def test_legacy_stays_the_default() -> None:
    assert settings().rag_answer_mode == "legacy"


def test_unmarked_absence_sentences_are_not_claims() -> None:
    assert _simple_claim_text("Tài liệu không đề cập mức phụ cấp.") == ""
    assert _simple_claim_text("The documents do not mention the allowance.") == ""
    partial = "Phụ cấp là 500.000 đồng [SOURCE_1]. Tài liệu không đề cập thời điểm chi trả."
    assert _simple_claim_text(partial) == "Phụ cấp là 500.000 đồng ."
    assert _simple_claim_text("Tài liệu không đề cập A.\nB là 5 ngày. [SOURCE_2]") == (
        "B là 5 ngày."
    )
    # With a marker it is a claim to check, even with a negation inside.
    assert _simple_claim_text("Công ty không cung cấp xe đưa đón [SOURCE_1].") != ""
    # A fact without a marker is still a claim (and then has no citation).
    assert _simple_claim_text("Phụ cấp là 500.000 đồng.") == "Phụ cấp là 500.000 đồng."


def test_a_partial_answer_is_validated_on_its_stated_part() -> None:
    result, llm = _ask(GOOD[:-1] + ". Tài liệu không đề cập người kiểm định xe.")
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1
    assert "không đề cập người kiểm định" in result.assistant_message.content


def test_number_normalization_applies_only_inside_its_block() -> None:
    answer, evidence = "kiem tra 1 lan moi nam", "kiem tra 01 lan/nam"
    assert validation._numbers_are_contradicted(answer, evidence)  # F is off by default
    with validation.number_normalization():
        assert not validation._numbers_are_contradicted(answer, evidence)
    assert validation._numbers_are_contradicted(answer, evidence)
