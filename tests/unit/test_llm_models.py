from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.llm.models import LLMGenerationResult, LLMMessage

CONFIDENTIAL_MARKER = "CONFIDENTIAL_LLM_MARKER"


def test_llm_message_is_immutable() -> None:
    message = LLMMessage(role="user", content="hello")
    with pytest.raises(FrozenInstanceError):
        message.role = "assistant"  # type: ignore[misc]


def test_llm_message_content_not_in_repr() -> None:
    assert CONFIDENTIAL_MARKER not in repr(LLMMessage(role="user", content=CONFIDENTIAL_MARKER))


def test_llm_generation_result_is_immutable() -> None:
    result = LLMGenerationResult(
        content="answer",
        model="model",
        finish_reason="stop",
        prompt_tokens=1,
        completion_tokens=2,
        response_time_ms=3,
    )
    with pytest.raises(FrozenInstanceError):
        result.model = "other"  # type: ignore[misc]


def test_generation_content_not_in_repr() -> None:
    result = LLMGenerationResult(
        content=CONFIDENTIAL_MARKER,
        model="model",
        finish_reason=None,
        prompt_tokens=None,
        completion_tokens=None,
        response_time_ms=0,
    )
    assert CONFIDENTIAL_MARKER not in repr(result)


def test_negative_response_time_rejected() -> None:
    with pytest.raises(ValueError):
        LLMGenerationResult(
            content="answer",
            model="model",
            finish_reason=None,
            prompt_tokens=None,
            completion_tokens=None,
            response_time_ms=-1,
        )


def test_negative_token_usage_rejected() -> None:
    with pytest.raises(ValueError):
        LLMGenerationResult(
            content="answer",
            model="model",
            finish_reason=None,
            prompt_tokens=-1,
            completion_tokens=None,
            response_time_ms=0,
        )


def test_invalid_role_rejected() -> None:
    with pytest.raises(ValueError):
        LLMMessage(role="tool", content="hello")  # type: ignore[arg-type]


def test_missing_usage_metadata_stays_none() -> None:
    result = LLMGenerationResult(
        content="answer",
        model="model",
        finish_reason=None,
        prompt_tokens=None,
        completion_tokens=None,
        response_time_ms=0,
    )

    assert result.usage is None
