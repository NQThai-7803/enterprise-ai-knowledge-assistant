"""Hybrid answer mode (RAG_ANSWER_MODE=hybrid, a DEC-041 option, off by default) and the
answer_route counters. Invented questions and sources only."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from app.chat.models import GroundingStatus
from app.chat.prompt_builder import build_simple_system_prompt
from app.citations.errors import CitationPermissionRevalidationError
from app.core.config import Settings
from app.llm.models import LLMGenerationResult
from app.observability.metrics import GLOBAL_METRICS
from app.services import grounded_answer_service as gas
from tests.unit.test_grounded_answer_service import (
    FakeRetrievalService,
    SequentialFakeLLMProvider,
    chat_session,
    hit,
    make_service,
    retrieval_result,
    settings,
    user,
)
from tests.unit.test_simple_answer_mode import GOOD, QUESTION, SOURCE, StrictCitationValidation

ROUTE_ANSWER = "Tai trong toi da cua xe toi la 2.500 kg."


class RevokedCitationValidation(StrictCitationValidation):
    """The user lost access to every cited document after retrieval."""

    async def validate_and_map(self, *, answer: str, source_registry, current_user):  # noqa: ANN001
        raise CitationPermissionRevalidationError()


@pytest.fixture(autouse=True)
def _clean_counters() -> Any:
    GLOBAL_METRICS.reset()
    yield
    GLOBAL_METRICS.reset()


def _route(monkeypatch: pytest.MonkeyPatch, answer: str | None) -> None:
    """Stand in for the deterministic route: it answers from SOURCE_1, or matches nothing."""

    def generation(**_: Any) -> LLMGenerationResult | None:
        if answer is None:
            return None
        return LLMGenerationResult(
            content=json.dumps({"answer": answer, "citations": ["SOURCE_1"]}),
            model="local-structured-value-repair:invented", finish_reason="stop",
            prompt_tokens=0, completion_tokens=0, response_time_ms=0, provider="local",
        )  # fmt: skip

    monkeypatch.setattr(gas, "_structured_value_repair_generation", generation)


def _ask(mode: str, *contents: str, hits: tuple = (hit(SOURCE),), validation=None) -> tuple:  # noqa: ANN001
    llm = SequentialFakeLLMProvider(
        *(
            LLMGenerationResult(
                content=c,
                model="fake",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                response_time_ms=1,
            )  # fmt: skip
            for c in contents or (GOOD,)
        )
    )
    service, _, _, _, resolved_llm, _, _ = make_service(
        retrieval=FakeRetrievalService(retrieval_result(*hits)),
        llm=llm,
        citation_validation=validation or StrictCitationValidation(),
        settings_obj=settings(rag_answer_mode=mode),
    )
    result = asyncio.run(
        service.answer_question(
            current_user=user(), session_id=chat_session().id, question=QUESTION
        )
    )
    return result, resolved_llm


def _routes() -> dict[str, int]:
    return {
        branch.removeprefix("answer_route_"): count
        for branch, count in GLOBAL_METRICS.answer_branch_counts().items()
        if branch.startswith("answer_route_")
    }


def test_hybrid_is_off_by_default() -> None:
    assert Settings(_env_file=None).rag_answer_mode == "simple"


@pytest.mark.parametrize("mode", ["hybrid", "legacy"])
def test_a_question_the_route_answers_takes_the_route_without_the_llm(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    _route(monkeypatch, ROUTE_ANSWER)
    result, llm = _ask(mode)
    assert result.grounding_status == GroundingStatus.ANSWERED
    assert ROUTE_ANSWER in result.assistant_message.content
    assert llm.calls == 0
    assert _routes() == {"det_invented": 1}
    assert GLOBAL_METRICS.answer_branch_counts()["route_deterministic"] == 1


def test_a_question_no_route_answers_goes_to_the_simple_path_in_hybrid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _route(monkeypatch, None)
    result, llm = _ask("hybrid")
    assert result.grounding_status == GroundingStatus.ANSWERED
    assert llm.calls == 1
    system = build_simple_system_prompt(
        no_answer_sentinel=settings().llm_no_answer_sentinel, short=False
    )
    assert llm.messages[0].content == system
    assert _routes() == {"llm_simple": 1}


def test_legacy_without_a_route_keeps_its_own_llm_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _route(monkeypatch, None)
    _, llm = _ask("legacy")
    assert llm.calls >= 1
    assert llm.message_history[0][0].content != build_simple_system_prompt(
        no_answer_sentinel=settings().llm_no_answer_sentinel, short=False
    )
    assert _routes() == {"llm_legacy": 1}


@pytest.mark.parametrize("route_answer", [ROUTE_ANSWER, None])
def test_a_revoked_document_leaks_through_neither_branch(
    monkeypatch: pytest.MonkeyPatch, route_answer: str | None
) -> None:
    _route(monkeypatch, route_answer)
    result, _ = _ask("hybrid", validation=RevokedCitationValidation())
    assert result.grounding_status == GroundingStatus.NO_ANSWER
    assert result.assistant_citations == ()
    assert SOURCE not in result.assistant_message.content
    assert ROUTE_ANSWER not in result.assistant_message.content


@pytest.mark.parametrize("mode", ["simple", "legacy"])
def test_no_source_is_a_refusal_gate(mode: str) -> None:
    result, llm = _ask(mode, hits=())
    assert result.grounding_status == GroundingStatus.NO_ANSWER
    assert llm.calls == 0
    assert _routes() == {"refusal_gate": 1}
