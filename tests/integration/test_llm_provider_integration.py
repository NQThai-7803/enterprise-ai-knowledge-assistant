from __future__ import annotations

import httpx
import pytest

from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMMessage
from app.llm.openai_compatible_provider import OpenAICompatibleLLMProvider

pytestmark = pytest.mark.llm_provider_integration


@pytest.mark.anyio
async def test_openai_compatible_provider_end_to_end() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "mock-model",
                "choices": [
                    {"message": {"content": "Mock grounded answer"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 3},
            },
        )

    provider = OpenAICompatibleLLMProvider(
        base_url="http://mock-provider.test/v1",
        api_key="",
        model="mock-model",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        transport=httpx.MockTransport(handler),
    )

    result = await provider.generate(
        messages=(LLMMessage(role="user", content="Question"),),
        temperature=0.0,
        max_output_tokens=32,
    )

    assert result.content == "Mock grounded answer"
    assert result.model == "mock-model"
    assert result.prompt_tokens == 4
    assert result.completion_tokens == 3


@pytest.mark.anyio
async def test_provider_returns_safe_result_model() -> None:
    provider = OpenAICompatibleLLMProvider(
        base_url="http://mock-provider.test/v1",
        api_key="SECRET",
        model="mock-model",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "model": "mock-model",
                    "choices": [{"message": {"content": "SECRET ANSWER"}}],
                },
            )
        ),
    )

    result = await provider.generate(
        messages=(LLMMessage(role="user", content="SECRET QUESTION"),),
        temperature=0.0,
        max_output_tokens=32,
    )

    assert "SECRET ANSWER" not in repr(result)
    assert not hasattr(result, "raw_response")


@pytest.mark.anyio
async def test_provider_timeout_is_bounded() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    provider = OpenAICompatibleLLMProvider(
        base_url="http://mock-provider.test/v1",
        api_key="",
        model="mock-model",
        timeout_seconds=0.01,
        max_retries=0,
        retry_backoff_seconds=0.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMError) as exc_info:
        await provider.generate(
            messages=(LLMMessage(role="user", content="Question"),),
            temperature=0.0,
            max_output_tokens=32,
        )

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_TIMEOUT
