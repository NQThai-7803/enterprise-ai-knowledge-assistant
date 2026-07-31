from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import quote

import httpx
from pydantic import SecretStr

from app.llm.errors import LLMError, LLMFailureCode
from app.llm.http import BaseHTTPProvider, secret_value, validate_base_url
from app.llm.models import LLMMessage, LLMRequest, LLMResponse, ProviderHealth, build_llm_request
from app.llm.openai_compatible_provider import _parse_generation_response
from app.llm.provider_names import AZURE_OPENAI_PROVIDER, provider_display_name


class AzureOpenAILLMProvider(BaseHTTPProvider):
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: SecretStr | str,
        deployment: str,
        api_version: str,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        app_env: str = "development",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not deployment.strip() or not api_version.strip() or not secret_value(api_key):
            raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
        super().__init__(
            provider_name=AZURE_OPENAI_PROVIDER,
            display_name=provider_display_name(AZURE_OPENAI_PROVIDER),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            transport=transport,
        )
        self.endpoint = validate_base_url(
            endpoint,
            provider_name=AZURE_OPENAI_PROVIDER,
            app_env=app_env,
            allow_http_local=False,
        )
        self._api_key = api_key
        self.deployment = deployment.strip()
        self.model = self.deployment
        self.api_version = api_version.strip()

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
        response, response_time_ms = await self._post_json(
            self._request_url(),
            payload=self._build_payload(llm_request),
            headers={"api-key": secret_value(self._api_key)},
        )
        return _parse_generation_response(
            response,
            provider_name=self.provider_name,
            default_model=self.deployment,
            response_time_ms=response_time_ms,
        )

    async def health_check(self, *, check_connectivity: bool = False) -> ProviderHealth:
        if not check_connectivity:
            return self._configuration_health(model=self.deployment)
        return await self._connectivity_health(self.endpoint, model=self.deployment)

    def _request_url(self) -> str:
        deployment = quote(self.deployment, safe="")
        api_version = quote(self.api_version, safe="")
        return (
            f"{self.endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={api_version}"
        )

    def _build_payload(self, request: LLMRequest) -> dict[str, object]:
        return {
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
