from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

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
from app.llm.provider_names import GEMINI_PROVIDER, provider_display_name

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"
_SAFETY_FINISH_REASONS = {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "SPII"}


class GeminiLLMProvider(BaseHTTPProvider):
    def __init__(
        self,
        *,
        api_key: SecretStr | str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        base_url: str = DEFAULT_GEMINI_BASE_URL,
        app_env: str = "development",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not model.strip() or not secret_value(api_key):
            raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
        super().__init__(
            provider_name=GEMINI_PROVIDER,
            display_name=provider_display_name(GEMINI_PROVIDER),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            transport=transport,
        )
        self.base_url = validate_base_url(
            base_url,
            provider_name=GEMINI_PROVIDER,
            app_env=app_env,
            allow_http_local=False,
        )
        self._api_key = api_key
        self.model = model.strip()

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
            payload = _build_gemini_payload(llm_request)
        except ValueError as exc:
            raise LLMError(LLMFailureCode.LLM_REQUEST_REJECTED) from exc
        response, response_time_ms = await self._post_json(
            self._request_url(),
            payload=payload,
            headers={"x-goog-api-key": secret_value(self._api_key)},
        )
        return _parse_gemini_response(
            response,
            provider_name=self.provider_name,
            model=self.model,
            response_time_ms=response_time_ms,
        )

    async def health_check(self, *, check_connectivity: bool = False) -> ProviderHealth:
        if not check_connectivity:
            return self._configuration_health(model=self.model)
        return await self._connectivity_health(self.base_url, model=self.model)

    def _request_url(self) -> str:
        model = self.model.removeprefix("models/")
        return f"{self.base_url}/v1beta/models/{quote(model, safe='/')}:generateContent"


def _build_gemini_payload(request: LLMRequest) -> dict[str, object]:
    system_parts: list[dict[str, str]] = []
    contents: list[dict[str, object]] = []
    for message in request.messages:
        if message.role == "system":
            system_parts.append({"text": message.content})
        elif message.role == "user":
            contents.append({"role": "user", "parts": [{"text": message.content}]})
        elif message.role == "assistant":
            contents.append({"role": "model", "parts": [{"text": message.content}]})
    if not contents:
        msg = "Gemini requests require at least one user or assistant message."
        raise ValueError(msg)
    payload: dict[str, object] = {
        "contents": contents,
        "generationConfig": {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens,
        },
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": system_parts}
    return payload


def _parse_gemini_response(
    response: httpx.Response,
    *,
    provider_name: str,
    model: str,
    response_time_ms: int,
) -> LLMResponse:
    try:
        payload = response.json()
    except Exception as exc:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE) from exc
    if not isinstance(payload, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    finish_reason = candidate.get("finishReason")
    content = _candidate_text(candidate)
    if not content:
        if finish_reason in _SAFETY_FINISH_REASONS:
            raise LLMError(LLMFailureCode.LLM_REQUEST_REJECTED)
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    usage = _usage_from_gemini(payload.get("usageMetadata"))
    try:
        return LLMResponse(
            content=content,
            provider=provider_name,
            model=model,
            finish_reason=normalize_finish_reason(finish_reason),
            prompt_tokens=usage.input_tokens if usage is not None else None,
            completion_tokens=usage.output_tokens if usage is not None else None,
            usage=usage,
            response_time_ms=response_time_ms,
            request_id=safe_request_id(response),
        )
    except ValueError as exc:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE) from exc


def _candidate_text(candidate: dict[str, Any]) -> str:
    content = candidate.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            text = part["text"].strip()
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


def _usage_from_gemini(usage: Any) -> LLMUsage | None:
    if usage is None:
        return None
    if not isinstance(usage, dict):
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    return LLMUsage(
        input_tokens=_optional_non_negative_usage(usage, "promptTokenCount"),
        output_tokens=_optional_non_negative_usage(usage, "candidatesTokenCount"),
        total_tokens=_optional_non_negative_usage(usage, "totalTokenCount"),
    )


def _optional_non_negative_usage(usage: dict[str, Any], key: str) -> int | None:
    value = usage.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LLMError(LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE)
    return value
