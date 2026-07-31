from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
from pydantic import SecretStr

from app.llm.errors import LLMError, LLMFailureCode
from app.llm.http import BaseHTTPProvider, safe_request_id, secret_value, validate_base_url
from app.llm.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ProviderHealth,
    build_llm_request,
    normalize_finish_reason,
)
from app.llm.provider_names import ANTHROPIC_PROVIDER, provider_display_name

DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicLLMProvider(BaseHTTPProvider):
    def __init__(
        self,
        *,
        api_key: SecretStr | str,
        model: str,
        anthropic_version: str,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        base_url: str = DEFAULT_ANTHROPIC_BASE_URL,
        app_env: str = "development",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not model.strip() or not anthropic_version.strip() or not secret_value(api_key):
            raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
        super().__init__(
            provider_name=ANTHROPIC_PROVIDER,
            display_name=provider_display_name(ANTHROPIC_PROVIDER),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            transport=transport,
        )
        self.base_url = validate_base_url(
            base_url,
            provider_name=ANTHROPIC_PROVIDER,
            app_env=app_env,
            allow_http_local=False,
        )
        self._api_key = api_key
        self.model = model.strip()
        self.anthropic_version = anthropic_version.strip()

    async def generate(
        self,
        *,
        messages: Sequence[LLMMessage] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        request: LLMRequest | None = None,
    ) -> LLMResponse:
        try:
            llm_request = build_llm_request(
                request=request,
                messages=tuple(messages or ()),
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            payload = self._build_payload(llm_request)
        except ValueError as exc:
            raise LLMError(LLMFailureCode.LLM_REQUEST_REJECTED) from exc
        response, response_time_ms = await self._post_json(
            f"{self.base_url}/v1/messages",
            payload=payload,
            headers=self._headers(),
        )
        return _parse_anthropic_response(
            response,
            provider_name=self.provider_name,
            default_model=self.model,
            response_time_ms=response_time_ms,
        )

    async def health_check(self, *, check_connectivity: bool = False) -> ProviderHealth:
        if not check_connectivity:
            return self._configuration_health(model=self.model)
        return await self._connectivity_health(self.base_url, model=self.model)

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": secret_value(self._api_key),
            "anthropic-version": self.anthropic_version,
        }

    def _build_payload(self, request: LLMRequest) -> dict[str, object]:
        system_parts: list[str] = []
        messages: list[dict[str, object]] = []
        for message in request.messages:
            if message.role == "system":
                system_parts.append(message.content)
            elif message.role in {"user", "assistant"}:
                messages.append(
                    {
                        "role": message.role,
                        "content": [{"type": "text", "text": message.content}],
                    }
                )
        if not messages:
            msg = "Anthropic requests require at least one user or assistant message."
            raise ValueError(msg)
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        return payload


def _parse_anthropic_response(
    response: httpx.Response,
    *,
    provider_name: str,
    default_model: str,
    response_time_ms: int,
) -> LLMResponse:
    try:
        payload = response.json()
    except Exception as exc:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE) from exc
    if not isinstance(payload, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    content = _content_text(payload.get("content"))
    if not content:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    model = payload.get("model") or default_model
    if not isinstance(model, str) or not model.strip():
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    usage = _usage_from_anthropic(payload.get("usage"))
    try:
        return LLMResponse(
            content=content,
            provider=provider_name,
            model=model.strip(),
            finish_reason=normalize_finish_reason(payload.get("stop_reason")),
            prompt_tokens=usage.input_tokens if usage is not None else None,
            completion_tokens=usage.output_tokens if usage is not None else None,
            usage=usage,
            response_time_ms=response_time_ms,
            request_id=safe_request_id(response),
        )
    except ValueError as exc:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE) from exc


def _content_text(content: Any) -> str:
    if not isinstance(content, list):
        return ""
    texts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            text = block["text"].strip()
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


def _usage_from_anthropic(usage: Any) -> LLMUsage | None:
    if usage is None:
        return None
    if not isinstance(usage, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    input_tokens = _optional_non_negative_usage(usage, "input_tokens")
    output_tokens = _optional_non_negative_usage(usage, "output_tokens")
    return LLMUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=None,
    )


def _optional_non_negative_usage(usage: dict[str, Any], key: str) -> int | None:
    value = usage.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    return value
