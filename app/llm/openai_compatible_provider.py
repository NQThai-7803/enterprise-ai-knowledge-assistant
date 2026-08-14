from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

import httpx
from pydantic import SecretStr

from app.llm.errors import LLMError, LLMFailureCode
from app.llm.http import BaseHTTPProvider, bearer_headers, safe_request_id, validate_base_url
from app.llm.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ProviderHealth,
    build_llm_request,
    normalize_finish_reason,
)
from app.llm.provider_names import OPENAI_COMPATIBLE_PROVIDER, provider_display_name


class OpenAICompatibleLLMProvider(BaseHTTPProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: SecretStr | str | None,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        provider_name: str = OPENAI_COMPATIBLE_PROVIDER,
        display_name: str | None = None,
        reasoning_effort: str | None = None,
        app_env: str = "development",
        extra_headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        ollama_num_ctx: int | None = None,
        ollama_keep_alive: str | None = None,
    ) -> None:
        if not model.strip():
            raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
        super().__init__(
            provider_name=provider_name,
            display_name=display_name or provider_display_name(provider_name),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            transport=transport,
        )
        self.base_url = validate_base_url(
            base_url,
            provider_name=provider_name,
            app_env=app_env,
            allow_http_local=True,
        )
        self.model = model.strip()
        self._api_key = api_key
        self._extra_headers = dict(extra_headers or {})
        self._reasoning_effort = (reasoning_effort or "").strip() or None
        self._ollama_num_ctx = ollama_num_ctx
        self._ollama_keep_alive = (ollama_keep_alive or "").strip() or None

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
        except ValueError as exc:
            raise LLMError(LLMFailureCode.LLM_REQUEST_REJECTED) from exc
        payload = self._build_payload(llm_request)
        response, response_time_ms = await self._post_json(
            f"{self.base_url}/chat/completions",
            payload=payload,
            headers=self._headers(),
        )
        return _parse_generation_response(
            response,
            provider_name=self.provider_name,
            default_model=self.model,
            response_time_ms=response_time_ms,
        )

    async def health_check(self, *, check_connectivity: bool = False) -> ProviderHealth:
        if not check_connectivity:
            return self._configuration_health(model=self.model)
        return await self._connectivity_health(self.base_url, model=self.model)

    def _build_payload(self, request: LLMRequest) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": self._payload_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
        if self._reasoning_effort:
            payload["reasoning_effort"] = self._reasoning_effort
            payload["reasoning"] = {"effort": self._reasoning_effort}
        if self.provider_name == "ollama":
            if self._ollama_num_ctx is not None:
                payload["options"] = {
                    "num_ctx": self._ollama_num_ctx,
                }

            if self._ollama_keep_alive:
                payload["keep_alive"] = self._ollama_keep_alive
        return payload

    def _payload_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        messages = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        if self.provider_name == "ollama" and self._reasoning_effort == "none":
            first = messages[0]
            if "/no_think" not in first["content"]:
                first["content"] = f"/no_think\n{first['content']}"
        return messages

    def _headers(self) -> dict[str, str]:
        headers = bearer_headers(self._api_key)
        headers.update(self._extra_headers)
        return headers


def _parse_generation_response(
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
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    content = _strip_visible_reasoning(content)
    if not content:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    model = payload.get("model") or default_model
    if not isinstance(model, str) or not model.strip():
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    usage = _usage_from_openai(payload.get("usage"))
    try:
        return LLMResponse(
            content=content.strip(),
            provider=provider_name,
            model=model.strip(),
            finish_reason=normalize_finish_reason(first_choice.get("finish_reason")),
            prompt_tokens=usage.input_tokens if usage is not None else None,
            completion_tokens=usage.output_tokens if usage is not None else None,
            usage=usage,
            response_time_ms=response_time_ms,
            request_id=safe_request_id(response),
        )
    except ValueError as exc:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE) from exc


_VISIBLE_THINKING_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINKING_CLOSE_TAG = "</think>"


def _strip_visible_reasoning(content: str) -> str:
    stripped = content.strip()
    lower = stripped.lower()
    close_index = lower.rfind(_THINKING_CLOSE_TAG)
    if close_index >= 0:
        return stripped[close_index + len(_THINKING_CLOSE_TAG) :].strip()
    return _VISIBLE_THINKING_BLOCK.sub("", stripped).strip()


def _usage_from_openai(usage: Any) -> LLMUsage | None:
    if usage is None:
        return None
    if not isinstance(usage, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    return LLMUsage(
        input_tokens=_optional_non_negative_usage(usage, "prompt_tokens"),
        output_tokens=_optional_non_negative_usage(usage, "completion_tokens"),
        total_tokens=_optional_non_negative_usage(usage, "total_tokens"),
    )


def _optional_non_negative_usage(usage: dict[str, Any], key: str) -> int | None:
    value = usage.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    return value
