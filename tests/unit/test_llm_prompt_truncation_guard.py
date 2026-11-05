"""LLM_PROMPT_TRUNCATION_GUARD_ENABLED / LLM_CONTEXT_WINDOW / LLM_TOKEN_ESTIMATE_RATIO guard."""

from __future__ import annotations

import logging

import pytest

from app.chat.models import GroundingStatus
from app.llm.models import LLMGenerationResult, LLMMessage
from app.services.grounded_answer_service import (
    PROMPT_BUDGET_EXCEEDED_ERROR_CODE,
    PROMPT_POSSIBLY_TRUNCATED_ERROR_CODE,
    _PromptTruncationGuard,
    estimate_prompt_tokens,
    prompt_budget_exceeded,
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

# context window 16384 - reserved output 1024 = threshold 15360 prompt tokens; the window is large
# enough that the pre-send budget check never fires for the test prompt.
WINDOW = {"llm_context_window": 16384, "llm_max_output_tokens": 1024}
BELOW, AT = 15359, 15360


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
    result, llm = _answer(BELOW, enforce=enforce)

    assert result.grounding_status == GroundingStatus.ANSWERED
    assert llm.messages is not None  # the guard forwards the prompt payload unchanged
    assert _guard_warnings(caplog) == []


@pytest.mark.parametrize("prompt_tokens", [AT, None], ids=["at_threshold", "usage_missing"])
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


@pytest.mark.parametrize("prompt_tokens", [AT, None], ids=["at_threshold", "usage_missing"])
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
    assert defaults.llm_token_estimate_ratio > 0


# --- PROMPT 4 item 0b: pre-send budget check and usage-below-estimate check ---------------------


class FixedCounter:
    """Counts every message content as ``tokens`` tokens."""

    def __init__(self, tokens: int) -> None:
        self.tokens = tokens

    def count(self, text: str) -> int:
        return self.tokens


def _messages() -> tuple[LLMMessage, ...]:
    return (LLMMessage(role="system", content="rules"), LLMMessage(role="user", content="q"))


def _guard(llm: FakeLLMProvider, *, per_message: int, enforce: bool) -> _PromptTruncationGuard:
    # 2 messages x per_message tiktoken tokens x ratio 1.5 = estimate
    return _PromptTruncationGuard(
        llm,
        context_window=4096,
        reserved_output_tokens=1024,
        enforce=enforce,
        token_counter=FixedCounter(per_message),
        token_estimate_ratio=1.5,
    )


def _generate(guard: _PromptTruncationGuard) -> object:
    holder: dict[str, object] = {}

    async def run() -> None:
        holder["result"] = await guard.generate(
            messages=_messages(), temperature=0.0, max_output_tokens=1024
        )

    run_async(run())
    return holder["result"]


def _records(caplog: pytest.LogCaptureFixture, code: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if getattr(r, "error_code", None) == code]


def test_estimate_and_budget_functions() -> None:
    assert estimate_prompt_tokens(_messages(), token_counter=FixedCounter(5), ratio=1.05) == 11
    assert not prompt_budget_exceeded(3072, max_output_tokens=1024, context_window=4096)
    assert prompt_budget_exceeded(3073, max_output_tokens=1024, context_window=4096)
    assert prompt_truncation_reason(69, threshold_tokens=3072, estimated_prompt_tokens=100) == (
        "USAGE_BELOW_ESTIMATE"
    )
    assert prompt_truncation_reason(70, threshold_tokens=3072, estimated_prompt_tokens=100) is None


@pytest.mark.parametrize("enforce", [False, True])
def test_prompt_within_budget_is_sent_without_budget_warning(
    enforce: bool, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    llm = FakeLLMProvider(_generation(3000))
    # estimate 2 x 1024 x 1.5 = 3072, plus 1024 output = 4096 = window: not exceeded
    result = _generate(_guard(llm, per_message=1024, enforce=enforce))

    assert llm.calls == 1 and result.prompt_tokens == 3000
    assert _records(caplog, PROMPT_BUDGET_EXCEEDED_ERROR_CODE) == []
    assert _records(caplog, PROMPT_POSSIBLY_TRUNCATED_ERROR_CODE) == []


def test_budget_exceeded_flag_off_logs_and_still_sends(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    llm = FakeLLMProvider(_generation(2050))
    _generate(_guard(llm, per_message=1025, enforce=False))  # estimate 3075 + 1024 > 4096

    assert llm.calls == 1
    (record,) = _records(caplog, PROMPT_BUDGET_EXCEEDED_ERROR_CODE)
    assert record.estimated_prompt_tokens == 3075
    assert record.context_window == 4096 and record.enforced is False


def test_budget_exceeded_flag_on_does_not_send_and_answers_no_answer(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    llm = FakeLLMProvider(_generation(100))
    # The real service with a tiny window: the test prompt alone exceeds it.
    service, *_ = make_service(
        settings_obj=settings(
            llm_context_window=1024,
            llm_max_output_tokens=1000,
            llm_prompt_truncation_guard_enabled=True,
        ),
        llm=llm,
    )
    holder: dict[str, object] = {}

    async def run() -> None:
        holder["result"] = await service.answer_question(
            current_user=user(), session_id=chat_session().id, question="Question"
        )

    run_async(run())
    result = holder["result"]

    assert llm.calls == 0  # never sent
    assert result.grounding_status == GroundingStatus.NO_ANSWER
    assert result.assistant_message.content == settings().chat_no_answer_message
    assert result.assistant_citations == ()
    (record,) = _records(caplog, PROMPT_BUDGET_EXCEEDED_ERROR_CODE)
    assert record.enforced is True
    rendered = record.getMessage() + repr(record.__dict__)
    assert "Question" not in rendered and "rules" not in rendered


@pytest.mark.parametrize("enforce", [False, True])
def test_usage_below_estimate_is_logged_but_not_enforced(
    enforce: bool, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    llm = FakeLLMProvider(_generation(1400))
    # estimate 2 x 1000 x 1.5 = 3000; 1400 < 0.7 x 3000 = 2100 (Ollama's cut-to-half signature)
    result = _generate(_guard(llm, per_message=1000, enforce=enforce))

    assert result.prompt_tokens == 1400  # the answer is kept even with the flag on
    (record,) = _records(caplog, PROMPT_POSSIBLY_TRUNCATED_ERROR_CODE)
    assert record.reason == "USAGE_BELOW_ESTIMATE"
    assert record.estimated_prompt_tokens == 3000 and record.enforced is False
