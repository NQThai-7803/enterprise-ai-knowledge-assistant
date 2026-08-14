from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMMessage
from app.llm.openai_compatible_provider import OpenAICompatibleLLMProvider

CONFIDENTIAL_PROMPT = "CONFIDENTIAL_PROVIDER_PROMPT"
CONFIDENTIAL_RESPONSE = "CONFIDENTIAL_PROVIDER_RESPONSE"
CONFIDENTIAL_KEY = "CONFIDENTIAL_API_KEY"


def make_provider(handler, **overrides: object) -> OpenAICompatibleLLMProvider:  # noqa: ANN001
    defaults = {
        "base_url": "http://provider.test/v1",
        "api_key": SecretStr(""),
        "model": "test-model",
        "timeout_seconds": 1.0,
        "max_retries": 0,
        "retry_backoff_seconds": 0.0,
        "transport": httpx.MockTransport(handler),
    }
    defaults.update(overrides)
    return OpenAICompatibleLLMProvider(**defaults)


def ok_response(content: str = "answer") -> dict[str, object]:
    return {
        "model": "test-model",
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3},
    }


async def call_provider(provider: OpenAICompatibleLLMProvider):
    return await provider.generate(
        messages=(
            LLMMessage(role="system", content="policy"),
            LLMMessage(role="user", content=CONFIDENTIAL_PROMPT),
            LLMMessage(role="assistant", content="previous"),
        ),
        temperature=0.25,
        max_output_tokens=123,
    )


def test_provider_does_not_call_network_on_import() -> None:
    import app.llm.openai_compatible_provider as provider_module

    assert provider_module.OpenAICompatibleLLMProvider is OpenAICompatibleLLMProvider


@pytest.mark.anyio
async def test_provider_sends_configured_model_and_messages() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.read().decode()
        return httpx.Response(200, json=ok_response())

    result = await call_provider(make_provider(handler))

    assert result.content == "answer"
    body = captured["json"]
    assert '"model":"test-model"' in body
    assert '"role":"system"' in body
    assert '"role":"user"' in body
    assert '"role":"assistant"' in body
    assert '"stream":false' in body
    assert '"temperature":0.25' in body
    assert '"max_tokens":123' in body


@pytest.mark.anyio
async def test_provider_omits_reasoning_effort_by_default() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.read().decode()
        return httpx.Response(200, json=ok_response())

    await call_provider(make_provider(handler))

    assert "reasoning_effort" not in captured["json"]


@pytest.mark.anyio
async def test_provider_sends_configured_reasoning_effort() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.read().decode()
        return httpx.Response(200, json=ok_response())

    await call_provider(make_provider(handler, provider_name="ollama", reasoning_effort="none"))

    assert '"reasoning_effort":"none"' in captured["json"]
    assert '"reasoning":{"effort":"none"}' in captured["json"]
    assert "/no_think" in captured["json"]


@pytest.mark.anyio
async def test_provider_adds_authorization_when_configured() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json=ok_response())

    provider = make_provider(handler, api_key=SecretStr(CONFIDENTIAL_KEY))
    await call_provider(provider)

    assert captured["authorization"] == f"Bearer {CONFIDENTIAL_KEY}"


@pytest.mark.anyio
async def test_provider_omits_authorization_when_key_empty() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json=ok_response())

    await call_provider(make_provider(handler))

    assert captured["authorization"] is None


@pytest.mark.anyio
async def test_provider_parses_answer_and_usage() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_response()))
    )

    assert result.content == "answer"
    assert result.model == "test-model"
    assert result.finish_reason == "stop"
    assert result.prompt_tokens == 7
    assert result.completion_tokens == 3
    assert result.response_time_ms >= 0


@pytest.mark.anyio
async def test_provider_accepts_missing_usage() -> None:
    payload = ok_response()
    payload.pop("usage")
    result = await call_provider(make_provider(lambda request: httpx.Response(200, json=payload)))

    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.usage is None


@pytest.mark.anyio
async def test_provider_strips_visible_thinking_before_returning_content() -> None:
    result = await call_provider(
        make_provider(
            lambda request: httpx.Response(
                200,
                json=ok_response("<think>draft</think>\n\nFinal answer [SOURCE_1]"),
            )
        )
    )

    assert result.content == "Final answer [SOURCE_1]"


@pytest.mark.anyio
async def test_provider_rejects_thinking_only_content() -> None:
    provider = make_provider(
        lambda request: httpx.Response(
            200,
            json=ok_response("<think>draft only</think>"),
        )
    )

    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE


@pytest.mark.anyio
async def test_provider_rejects_empty_choices() -> None:
    provider = make_provider(
        lambda request: httpx.Response(200, json={"model": "m", "choices": []})
    )
    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)
    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE


@pytest.mark.anyio
async def test_provider_rejects_empty_content() -> None:
    provider = make_provider(lambda request: httpx.Response(200, json=ok_response("   ")))
    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)
    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE


@pytest.mark.anyio
async def test_provider_maps_authentication_error() -> None:
    provider = make_provider(lambda request: httpx.Response(401, json={"error": "secret body"}))
    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)
    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_AUTHENTICATION_FAILED


@pytest.mark.anyio
async def test_provider_maps_rate_limit() -> None:
    provider = make_provider(lambda request: httpx.Response(429, json={"error": "secret body"}))
    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)
    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_RATE_LIMITED


@pytest.mark.anyio
async def test_provider_maps_server_error() -> None:
    provider = make_provider(lambda request: httpx.Response(503, json={"error": "secret body"}))
    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)
    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_UNAVAILABLE


@pytest.mark.anyio
async def test_provider_retries_only_transient_errors() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "transient"})
        return httpx.Response(200, json=ok_response())

    provider = make_provider(handler, max_retries=1)
    result = await call_provider(provider)

    assert result.content == "answer"
    assert calls == 2


@pytest.mark.anyio
async def test_provider_retries_are_bounded() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": "transient"})

    provider = make_provider(handler, max_retries=1)
    with pytest.raises(LLMError):
        await call_provider(provider)
    assert calls == 2


@pytest.mark.anyio
async def test_provider_does_not_log_prompt_response_or_api_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = make_provider(
        lambda request: httpx.Response(200, json=ok_response(CONFIDENTIAL_RESPONSE)),
        api_key=SecretStr(CONFIDENTIAL_KEY),
    )
    await call_provider(provider)

    logs = caplog.text
    assert CONFIDENTIAL_PROMPT not in logs
    assert CONFIDENTIAL_RESPONSE not in logs
    assert CONFIDENTIAL_KEY not in logs


@pytest.mark.anyio
async def test_openai_compatible_request_mapping() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(200, json=ok_response())

    await call_provider(make_provider(handler))

    assert '"model":"test-model"' in captured["body"]
    assert '"messages"' in captured["body"]
    assert '"stream":false' in captured["body"]


@pytest.mark.anyio
async def test_openai_compatible_response_mapping() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_response()))
    )

    assert result.provider == "openai_compatible"
    assert result.model == "test-model"
    assert result.finish_reason == "stop"


@pytest.mark.anyio
async def test_openai_compatible_usage_mapping() -> None:
    result = await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_response()))
    )

    assert result.usage.input_tokens == 7
    assert result.usage.output_tokens == 3
    assert result.usage.total_tokens is None


@pytest.mark.anyio
async def test_openai_compatible_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("SECRET timeout body")

    provider = make_provider(handler)
    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_TIMEOUT
    assert "SECRET" not in str(exc_info.value)


@pytest.mark.anyio
async def test_openai_compatible_safe_error() -> None:
    provider = make_provider(lambda request: httpx.Response(500, json={"error": "SECRET"}))

    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert exc_info.value.code == LLMFailureCode.LLM_PROVIDER_UNAVAILABLE
    assert "SECRET" not in str(exc_info.value)


@pytest.mark.anyio
async def test_prompt_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    await call_provider(make_provider(lambda request: httpx.Response(200, json=ok_response())))

    assert CONFIDENTIAL_PROMPT not in caplog.text


@pytest.mark.anyio
async def test_context_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    provider = make_provider(lambda request: httpx.Response(200, json=ok_response()))

    await provider.generate(
        messages=(LLMMessage(role="user", content="CONFIDENTIAL_CONTEXT_MARKER"),),
        temperature=0.0,
        max_output_tokens=32,
    )

    assert "CONFIDENTIAL_CONTEXT_MARKER" not in caplog.text


@pytest.mark.anyio
async def test_response_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    await call_provider(
        make_provider(lambda request: httpx.Response(200, json=ok_response(CONFIDENTIAL_RESPONSE)))
    )

    assert CONFIDENTIAL_RESPONSE not in caplog.text


@pytest.mark.anyio
async def test_provider_key_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    await call_provider(
        make_provider(
            lambda request: httpx.Response(200, json=ok_response()),
            api_key=SecretStr(CONFIDENTIAL_KEY),
        )
    )

    assert CONFIDENTIAL_KEY not in caplog.text


@pytest.mark.anyio
async def test_raw_provider_error_not_returned() -> None:
    provider = make_provider(
        lambda request: httpx.Response(500, json={"error": "CONFIDENTIAL_RAW_ERROR"})
    )

    with pytest.raises(LLMError) as exc_info:
        await call_provider(provider)

    assert "CONFIDENTIAL_RAW_ERROR" not in str(exc_info.value)


@pytest.mark.anyio
async def test_provider_health_without_connectivity_does_not_call_network() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=ok_response())

    provider = make_provider(handler)
    health = await provider.health_check()

    assert health.status == "configured"
    assert health.connectivity_checked is False
    assert calls == 0


@pytest.mark.anyio
async def test_provider_health_connectivity_reachable() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(404, headers={"x-request-id": "req-health-1"})

    provider = make_provider(handler)
    health = await provider.health_check(check_connectivity=True)

    assert captured == {"method": "GET", "url": "http://provider.test/v1"}
    assert health.status == "reachable"
    assert health.configured is True
    assert health.connectivity_checked is True
    assert health.request_id == "req-health-1"


@pytest.mark.anyio
async def test_provider_health_connectivity_unreachable() -> None:
    provider = make_provider(lambda request: httpx.Response(503, json={"error": "SECRET"}))

    health = await provider.health_check(check_connectivity=True)

    assert health.status == "unreachable"
    assert health.configured is True
    assert health.connectivity_checked is True
    assert "SECRET" not in (health.message or "")
