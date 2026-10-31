"""LLM_PROMPT_TRUNCATION_GUARD_ENABLED / LLM_CONTEXT_WINDOW: warn, and optionally fail safe."""

from __future__ import annotations

import logging

import pytest

from app.chat.models import GroundingStatus
from app.llm.models import LLMGenerationResult
from app.services.grounded_answer_service import (
    PROMPT_POSSIBLY_TRUNCATED_ERROR_CODE,
    prompt_truncation_reason,
)
from tests.unit.test_grounded_answer_service import (
    FakeLLMProvider,
    chat_session,
    make_service,
    run_async,
    settings,
    user,
)

# context window 2048 - reserved output 1024 = threshold 1024 prompt tokens
WINDOW = {"llm_context_window": 2048, "llm_max_output_tokens": 1024}


def _generation(prompt_tokens: int | None) -> LLMGenerationResult:
    return LLMGenerationResult(
        content='{"answer":"Grounded answer","citations":["SOURCE_1"]}',
        model="fake",
        finish_reason="stop",
        prompt_tokens=prompt_tokens,
        completion_tokens=5,
        response_time_ms=10,
    )


def _answer(prompt_tokens: int | None, *, enforce: bool):
    llm = FakeLLMProvider(_generation(prompt_tokens))
    service, *_ = make_service(
        settings_obj=settings(**WINDOW, llm_prompt_truncation_guard_enabled=enforce), llm=llm
    )

    async def scenario():
        return await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

    holder: dict[str, object] = {}

    async def run() -> None:
        holder["result"] = await scenario()

    run_async(run())
    return holder["result"], llm


def _guard_warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if getattr(record, "error_code", None) == PROMPT_POSSIBLY_TRUNCATED_ERROR_CODE
    ]


def test_reason_for_each_usage_case() -> None:
    assert prompt_truncation_reason(1023, threshold_tokens=1024) is None
    assert prompt_truncation_reason(1024, threshold_tokens=1024) == "NEAR_CONTEXT_WINDOW"
    assert prompt_truncation_reason(None, threshold_tokens=1024) == "USAGE_MISSING"


@pytest.mark.parametrize("enforce", [False, True])
def test_prompt_below_threshold_answers_without_warning(
    enforce: bool, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    result, llm = _answer(1023, enforce=enforce)

    assert result.grounding_status == GroundingStatus.ANSWERED
    assert llm.messages is not None  # the guard forwards the prompt payload unchanged
    assert _guard_warnings(caplog) == []


@pytest.mark.parametrize("prompt_tokens", [1024, None], ids=["at_threshold", "usage_missing"])
def test_possible_truncation_warns_and_keeps_answer_when_flag_off(
    prompt_tokens: int | None, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    result, _ = _answer(prompt_tokens, enforce=False)

    assert result.grounding_status == GroundingStatus.ANSWERED
    warnings = _guard_warnings(caplog)
    assert len(warnings) == 1
    assert warnings[0].reason == (
        "USAGE_MISSING" if prompt_tokens is None else "NEAR_CONTEXT_WINDOW"
    )
    assert warnings[0].enforced is False


@pytest.mark.parametrize("prompt_tokens", [1024, None], ids=["at_threshold", "usage_missing"])
def test_possible_truncation_returns_fixed_no_answer_when_flag_on(
    prompt_tokens: int | None, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    result, _ = _answer(prompt_tokens, enforce=True)

    assert result.grounding_status == GroundingStatus.NO_ANSWER
    assert result.assistant_message.content == settings().chat_no_answer_message
    assert result.assistant_citations == ()
    warnings = _guard_warnings(caplog)
    assert len(warnings) == 1 and warnings[0].enforced is True


def test_warning_carries_no_prompt_or_answer_text(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    _answer(None, enforce=True)

    warning = _guard_warnings(caplog)[0]
    rendered = warning.getMessage() + repr(warning.__dict__)
    assert "Question" not in rendered
    assert "Grounded answer" not in rendered


def test_settings_defaults() -> None:
    defaults = settings()
    assert defaults.llm_context_window == 8192
    assert defaults.llm_prompt_truncation_guard_enabled is False
