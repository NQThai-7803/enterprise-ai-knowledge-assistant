from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from app.llm.azure_openai_provider import AzureOpenAILLMProvider
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMMessage


def make_provider(handler) -> AzureOpenAILLMProvider:  # noqa: ANN001
    return AzureOpenAILLMProvider(
        endpoint="https://azure.example.com",
        api_key=SecretStr("azure-secret"),
        deployment="deployment-one",
        api_version="2024-02-15-preview",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        transport=httpx.MockTransport(handler),
    )


async def call_provider(provider: AzureOpenAILLMProvider):
    return await provider.generate(
        messages=(LLMMessage(role="user", content="Question"),),
        temperature=0.0,
        max_output_tokens=32,
    )


def ok_payload() -> dict[str, object]:
    return {
        "model": "deployment-one",
        "choices": [{"message": {"content": "Answer"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
    }


@pytest.mark.anyio
async def test_azure_request_url() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=ok_payload())

    await call_provider(make_provider(handler))

    assert captured["url"] == (
        "https://azure.example.com/openai/deployments/deployment-one/chat/completions"
        "?api-version=2024-02-15-preview"
    )


@pytest.mark.anyio
async def test_azure_headers() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["api_key"] = request.headers.get("api-key")
        return httpx.Response(200, json=ok_payload())

    await call_provider(make_provider(handler))

    assert captured["api_key"] == "azure-secret"


@pytest.mark.anyio
async def test_azure_response_mapping() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_payload()))
    )

    assert result.provider == "azure_openai"
    assert result.model == "deployment-one"
    assert result.content == "Answer"
    assert result.usage.input_tokens == 2
    assert result.usage.output_tokens == 3
    assert result.usage.total_tokens == 5


@pytest.mark.anyio
async def test_azure_safe_error() -> None:
    provider = make_provider(lambda request: httpx.Response(401, json={"error": "SECRET"}))

    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_AUTHENTICATION_FAILED
    assert "SECRET" not in str(exc_info.value)
