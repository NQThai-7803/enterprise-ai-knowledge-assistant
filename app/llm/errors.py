from __future__ import annotations

from enum import StrEnum


class LLMFailureCode(StrEnum):
    LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"
    LLM_PROVIDER_UNSUPPORTED = "LLM_PROVIDER_UNSUPPORTED"
    LLM_PROVIDER_AUTHENTICATION_FAILED = "LLM_PROVIDER_AUTHENTICATION_FAILED"
    LLM_PROVIDER_RATE_LIMITED = "LLM_PROVIDER_RATE_LIMITED"
    LLM_PROVIDER_TIMEOUT = "LLM_PROVIDER_TIMEOUT"
    LLM_PROVIDER_UNAVAILABLE = "LLM_PROVIDER_UNAVAILABLE"
    LLM_PROVIDER_BAD_RESPONSE = "LLM_PROVIDER_BAD_RESPONSE"
    LLM_REQUEST_REJECTED = "LLM_REQUEST_REJECTED"

    # Backward-compatible TASK-019/TASK-020 aliases accepted by older tests/fakes.
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_AUTHENTICATION_FAILED = "LLM_AUTHENTICATION_FAILED"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_RESPONSE_INVALID = "LLM_RESPONSE_INVALID"
    LLM_GENERATION_FAILED = "LLM_GENERATION_FAILED"


_SAFE_MESSAGES = {
    LLMFailureCode.LLM_NOT_CONFIGURED: "The LLM provider is not configured.",
    LLMFailureCode.LLM_PROVIDER_UNSUPPORTED: "The LLM provider is not supported.",
    LLMFailureCode.LLM_PROVIDER_AUTHENTICATION_FAILED: ("The LLM provider authentication failed."),
    LLMFailureCode.LLM_PROVIDER_RATE_LIMITED: "The LLM provider is rate limited.",
    LLMFailureCode.LLM_PROVIDER_TIMEOUT: "The LLM provider timed out.",
    LLMFailureCode.LLM_PROVIDER_UNAVAILABLE: "The LLM provider is unavailable.",
    LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE: ("The LLM provider returned an invalid response."),
    LLMFailureCode.LLM_REQUEST_REJECTED: "The LLM request was rejected by the provider.",
    LLMFailureCode.LLM_TIMEOUT: "The LLM provider timed out.",
    LLMFailureCode.LLM_AUTHENTICATION_FAILED: "The LLM provider authentication failed.",
    LLMFailureCode.LLM_RATE_LIMITED: "The LLM provider is rate limited.",
    LLMFailureCode.LLM_RESPONSE_INVALID: "The LLM provider returned an invalid response.",
    LLMFailureCode.LLM_GENERATION_FAILED: "The LLM generation operation failed.",
}


class LLMError(Exception):
    code: LLMFailureCode
    safe_message: str

    def __init__(self, code: LLMFailureCode, safe_message: str | None = None) -> None:
        self.code = code
        self.safe_message = safe_message or _SAFE_MESSAGES[code]
        super().__init__(self.safe_message)
