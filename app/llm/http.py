from __future__ import annotations

import asyncio
from time import perf_counter
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMProviderCapabilities, ProviderHealth
from app.llm.provider_names import provider_display_name

_SAFE_REQUEST_ID_HEADERS = (
    "x-request-id",
    "request-id",
    "x-ms-request-id",
    "x-ratelimit-request-id",
    "cf-ray",
)
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class BaseHTTPProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        display_name: str | None = None,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0 or max_retries < 0 or retry_backoff_seconds < 0:
            raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
        self.provider_name = provider_name
        self.display_name = display_name or provider_display_name(provider_name)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._transport = transport
        self.capabilities = LLMProviderCapabilities(
            supports_streaming=True,
            supports_usage_streaming=False,
            supports_native_streaming=False,
        )
        self._client: httpx.AsyncClient | None = None

    async def health_check(self, *, check_connectivity: bool = False) -> ProviderHealth:
        if not check_connectivity:
            return self._configuration_health()
        endpoint = getattr(self, "base_url", "")
        return await self._connectivity_health(str(endpoint))

    def _configuration_health(self, *, model: str | None = None) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            display_name=self.display_name,
            status="configured",
            configured=True,
            model=model or getattr(self, "model", None),
            connectivity_checked=False,
            message="Provider configuration is valid.",
        )

    async def _connectivity_health(
        self,
        endpoint: str,
        *,
        model: str | None = None,
    ) -> ProviderHealth:
        safe_endpoint = endpoint.strip()
        if not safe_endpoint:
            return ProviderHealth(
                provider=self.provider_name,
                display_name=self.display_name,
                status="misconfigured",
                configured=False,
                model=model or getattr(self, "model", None),
                connectivity_checked=False,
                message="Provider configuration is invalid.",
            )
        try:
            response = await self._get_client().get(safe_endpoint)
        except httpx.TimeoutException:
            return self._unreachable_health(
                model=model,
                message="Provider connectivity check timed out.",
            )
        except (httpx.ConnectError, httpx.NetworkError, httpx.RemoteProtocolError, httpx.HTTPError):
            return self._unreachable_health(
                model=model,
                message="Provider endpoint is unreachable.",
            )
        status = "reachable" if response.status_code < 500 else "unreachable"
        message = (
            "Provider endpoint is reachable."
            if status == "reachable"
            else "Provider endpoint is unreachable."
        )
        return ProviderHealth(
            provider=self.provider_name,
            display_name=self.display_name,
            status=status,
            configured=True,
            model=model or getattr(self, "model", None),
            connectivity_checked=True,
            request_id=safe_request_id(response),
            message=message,
        )

    def _unreachable_health(
        self,
        *,
        model: str | None,
        message: str,
    ) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            display_name=self.display_name,
            status="unreachable",
            configured=True,
            model=model or getattr(self, "model", None),
            connectivity_checked=True,
            message=message,
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _post_json(
        self,
        endpoint: str,
        *,
        payload: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> tuple[httpx.Response, int]:
        attempts = self.max_retries + 1
        started_at = perf_counter()
        last_error: LLMError | None = None
        for attempt in range(attempts):
            try:
                response = await self._get_client().post(endpoint, json=payload, headers=headers)
                response_time_ms = max(0, int((perf_counter() - started_at) * 1000))
                error_code = _provider_error_code(response.status_code)
                if error_code is None:
                    return response, response_time_ms
                error = LLMError(error_code)
                if not _is_retryable_status(response.status_code) or attempt >= self.max_retries:
                    raise error
                last_error = error
            except httpx.TimeoutException as exc:
                last_error = LLMError(LLMFailureCode.LLM_PROVIDER_TIMEOUT)
                if attempt >= self.max_retries:
                    raise last_error from exc
            except (httpx.ConnectError, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = LLMError(LLMFailureCode.LLM_PROVIDER_UNAVAILABLE)
                if attempt >= self.max_retries:
                    raise last_error from exc
            except LLMError:
                raise
            if self.retry_backoff_seconds > 0:
                await asyncio.sleep(self.retry_backoff_seconds)
        raise last_error or LLMError(LLMFailureCode.LLM_PROVIDER_UNAVAILABLE)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(
                self.timeout_seconds,
                connect=self.timeout_seconds,
                read=self.timeout_seconds,
                write=self.timeout_seconds,
                pool=self.timeout_seconds,
            )
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=False,
                transport=self._transport,
            )
        return self._client


def secret_value(value: SecretStr | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return value.get_secret_value().strip()
    return str(value).strip()


def bearer_headers(api_key: SecretStr | str | None) -> dict[str, str]:
    value = secret_value(api_key)
    if not value:
        return {}
    return {"Authorization": f"Bearer {value}"}


def safe_request_id(response: httpx.Response) -> str | None:
    for header_name in _SAFE_REQUEST_ID_HEADERS:
        value = response.headers.get(header_name)
        if value and _is_safe_request_id(value):
            return value.strip()
    return None


def validate_base_url(
    base_url: str,
    *,
    provider_name: str,
    app_env: str = "development",
    allow_http_local: bool = True,
) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
    try:
        _ = parsed.port
    except ValueError as exc:
        raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED) from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
    if (
        parsed.scheme == "http"
        and app_env == "production"
        and not (allow_http_local and _is_local_host(parsed.hostname))
    ):
        raise LLMError(LLMFailureCode.LLM_NOT_CONFIGURED)
    return normalized


def append_v1_if_missing(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def _provider_error_code(status_code: int) -> LLMFailureCode | None:
    if status_code < 400:
        return None
    if status_code in {401, 403}:
        return LLMFailureCode.LLM_PROVIDER_AUTHENTICATION_FAILED
    if status_code == 408:
        return LLMFailureCode.LLM_PROVIDER_TIMEOUT
    if status_code == 429:
        return LLMFailureCode.LLM_PROVIDER_RATE_LIMITED
    if 500 <= status_code <= 599:
        return LLMFailureCode.LLM_PROVIDER_UNAVAILABLE
    if status_code in {400, 422}:
        return LLMFailureCode.LLM_REQUEST_REJECTED
    return LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE


def _is_retryable_status(status_code: int) -> bool:
    return status_code in _RETRYABLE_STATUS_CODES


def _is_safe_request_id(value: str) -> bool:
    stripped = value.strip()
    if not stripped or len(stripped) > 128:
        return False
    return all(char.isalnum() or char in {"-", "_", ".", ":"} for char in stripped)


def _is_local_host(hostname: str) -> bool:
    normalized = hostname.strip().lower().strip("[]")
    return normalized in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
