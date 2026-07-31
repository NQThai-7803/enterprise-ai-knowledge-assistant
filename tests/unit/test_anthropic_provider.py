from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from app.llm.anthropic_provider import AnthropicLLMProvider
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMMessage


def make_provider(handler) -> AnthropicLLMProvider:  # noqa: ANN001
    return AnthropicLLMProvider(
        api_key=SecretStr("anthropic-secret"),
        model="claude-test",
        anthropic_version="2023-06-01",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        transport=httpx.MockTransport(handler),
    )


async def call_provider(provider: AnthropicLLMProvider):
    return await provider.generate(
        messages=(
            LLMMessage(role="system", content="System policy"),
            LLMMessage(role="user", content="Question"),
            LLMMessage(role="assistant", content="Previous answer"),
        ),
        temperature=0.1,
        max_output_tokens=128,
    )


def ok_payload() -> dict[str, object]:
    return {
        "model": "claude-test",
        "content": [{"type": "text", "text": "Anthropic answer"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 6, "output_tokens": 4},
    }


@pytest.mark.anyio
async def test_anthropic_system_mapping() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content.decode()))
        return httpx.Response(200, json=ok_payload())

    await call_provider(make_provider(handler))

    assert captured["system"] == "System policy"


@pytest.mark.anyio
async def test_anthropic_message_mapping() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content.decode()))
        return httpx.Response(200, json=ok_payload())

    await call_provider(make_provider(handler))

    assert captured["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "Question"}]},
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Previous answer"}],
        },
    ]
    assert captured["max_tokens"] == 128
    assert captured["temperature"] == 0.1


@pytest.mark.anyio
async def test_anthropic_response_mapping() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_payload()))
    )

    assert result.provider == "anthropic"
    assert result.model == "claude-test"
    assert result.content == "Anthropic answer"
    assert result.finish_reason == "stop"


@pytest.mark.anyio
async def test_anthropic_usage_mapping() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_payload()))
    )

    assert result.usage.input_tokens == 6
    assert result.usage.output_tokens == 4
    assert result.usage.total_tokens is None


@pytest.mark.anyio
async def test_anthropic_safe_error() -> None:
    provider = make_provider(lambda request: httpx.Response(503, json={"error": "SECRET"}))

    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_UNAVAILABLE
    assert "SECRET" not in str(exc_info.value)


@pytest.mark.anyio
async def test_anthropic_missing_usage_stays_none() -> None:
    payload = ok_payload()
    payload.pop("usage")

    result = await call_provider(make_provider(lambda request: httpx.Response(200, json=payload)))

    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.usage is None
