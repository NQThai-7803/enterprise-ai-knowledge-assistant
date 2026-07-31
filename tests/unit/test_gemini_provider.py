from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from app.llm.errors import LLMError, LLMFailureCode
from app.llm.gemini_provider import GeminiLLMProvider
from app.llm.models import LLMMessage


def make_provider(handler) -> GeminiLLMProvider:  # noqa: ANN001
    return GeminiLLMProvider(
        api_key=SecretStr("gemini-secret"),
        model="gemini-test",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        transport=httpx.MockTransport(handler),
    )


async def call_provider(provider: GeminiLLMProvider):
    return await provider.generate(
        messages=(
            LLMMessage(role="system", content="System policy"),
            LLMMessage(role="user", content="Question"),
            LLMMessage(role="assistant", content="Previous answer"),
        ),
        temperature=0.2,
        max_output_tokens=64,
    )


def ok_payload() -> dict[str, object]:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": "Gemini answer"}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 5,
            "candidatesTokenCount": 7,
            "totalTokenCount": 12,
        },
    }


@pytest.mark.anyio
async def test_gemini_system_instruction_mapping() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content.decode()))
        return httpx.Response(200, json=ok_payload())

    await call_provider(make_provider(handler))

    assert captured["systemInstruction"] == {"parts": [{"text": "System policy"}]}


@pytest.mark.anyio
async def test_gemini_message_mapping() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content.decode()))
        return httpx.Response(200, json=ok_payload())

    await call_provider(make_provider(handler))

    assert captured["contents"] == [
        {"role": "user", "parts": [{"text": "Question"}]},
        {"role": "model", "parts": [{"text": "Previous answer"}]},
    ]
    assert captured["generationConfig"] == {"temperature": 0.2, "maxOutputTokens": 64}


@pytest.mark.anyio
async def test_gemini_response_mapping() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_payload()))
    )

    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.content == "Gemini answer"
    assert result.finish_reason == "stop"


@pytest.mark.anyio
async def test_gemini_usage_mapping() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_payload()))
    )

    assert result.usage.input_tokens == 5
    assert result.usage.output_tokens == 7
    assert result.usage.total_tokens == 12


@pytest.mark.anyio
async def test_gemini_safe_error() -> None:
    provider = make_provider(lambda request: httpx.Response(429, json={"error": "SECRET"}))

    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_RATE_LIMITED
    assert "SECRET" not in str(exc_info.value)


@pytest.mark.anyio
async def test_gemini_request_rejected_for_safety_response() -> None:
    provider = make_provider(
        lambda request: httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]},
        )
    )

    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert exc_info.value.code == LLMFailureCode.LLM_REQUEST_REJECTED


@pytest.mark.anyio
async def test_gemini_missing_usage_stays_none() -> None:
    payload = ok_payload()
    payload.pop("usageMetadata")

    result = await call_provider(make_provider(lambda request: httpx.Response(200, json=payload)))

    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.usage is None
