from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from numbers import Integral, Real
from typing import Literal

LLMRole = Literal["system", "user", "assistant"]
_ALLOWED_ROLES = {"system", "user", "assistant"}
ProviderHealthStatus = Literal[
    "configured",
    "disabled",
    "reachable",
    "unreachable",
    "misconfigured",
]


class LLMFinishReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    SAFETY = "safety"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: LLMRole
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        if self.role not in _ALLOWED_ROLES:
            msg = "LLM message role is invalid."
            raise ValueError(msg)
        if not isinstance(self.content, str) or not self.content.strip():
            msg = "LLM message content must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_tokens",
            _coerce_optional_non_negative_int(self.input_tokens),
        )
        object.__setattr__(
            self,
            "output_tokens",
            _coerce_optional_non_negative_int(self.output_tokens),
        )
        object.__setattr__(
            self,
            "total_tokens",
            _coerce_optional_non_negative_int(self.total_tokens),
        )


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    temperature: float
    max_output_tokens: int

    def __post_init__(self) -> None:
        messages = tuple(self.messages)
        if not messages:
            msg = "LLM request messages must not be empty."
            raise ValueError(msg)
        object.__setattr__(self, "messages", messages)
        object.__setattr__(self, "temperature", _coerce_temperature(self.temperature))
        object.__setattr__(
            self,
            "max_output_tokens",
            _coerce_positive_int(self.max_output_tokens),
        )


@dataclass(frozen=True, slots=True)
class LLMProviderCapabilities:
    supports_streaming: bool = True
    supports_usage_streaming: bool = False
    supports_native_streaming: bool = False


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider: str
    status: ProviderHealthStatus
    configured: bool
    display_name: str | None = None
    model: str | None = None
    message: str | None = None
    connectivity_checked: bool = False
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider.strip():
            msg = "provider must not be empty."
            raise ValueError(msg)
        if self.display_name is not None and not self.display_name.strip():
            msg = "display_name must not be empty when present."
            raise ValueError(msg)
        if self.model is not None and not self.model.strip():
            msg = "model must not be empty when present."
            raise ValueError(msg)
        if self.request_id is not None and not self.request_id.strip():
            msg = "request_id must not be empty when present."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class LLMGenerationResult:
    content: str = field(repr=False)
    model: str
    finish_reason: str | LLMFinishReason | None
    prompt_tokens: int | None
    completion_tokens: int | None
    response_time_ms: int
    provider: str = "unknown"
    request_id: str | None = None
    usage: LLMUsage | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str) or not self.content.strip():
            msg = "LLM generation content must not be empty."
            raise ValueError(msg)
        if not isinstance(self.model, str) or not self.model.strip():
            msg = "LLM generation model must not be empty."
            raise ValueError(msg)
        if not isinstance(self.provider, str) or not self.provider.strip():
            msg = "LLM generation provider must not be empty."
            raise ValueError(msg)
        object.__setattr__(
            self,
            "response_time_ms",
            _coerce_non_negative_int(self.response_time_ms),
        )
        prompt_tokens = _coerce_optional_non_negative_int(self.prompt_tokens)
        completion_tokens = _coerce_optional_non_negative_int(self.completion_tokens)
        usage = self.usage
        if usage is None:
            if prompt_tokens is not None or completion_tokens is not None:
                total_tokens = (
                    prompt_tokens + completion_tokens
                    if prompt_tokens is not None and completion_tokens is not None
                    else None
                )
                usage = LLMUsage(
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )
        else:
            if prompt_tokens is None:
                prompt_tokens = usage.input_tokens
            if completion_tokens is None:
                completion_tokens = usage.output_tokens
        object.__setattr__(self, "prompt_tokens", prompt_tokens)
        object.__setattr__(self, "completion_tokens", completion_tokens)
        object.__setattr__(self, "usage", usage)
        if self.request_id is not None and not self.request_id.strip():
            msg = "request_id must not be empty when present."
            raise ValueError(msg)


LLMResponse = LLMGenerationResult


def build_llm_request(
    *,
    request: LLMRequest | None = None,
    messages: tuple[LLMMessage, ...] | list[LLMMessage] | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> LLMRequest:
    if request is not None:
        return request
    if messages is None or temperature is None or max_output_tokens is None:
        msg = "messages, temperature, and max_output_tokens are required."
        raise ValueError(msg)
    return LLMRequest(
        messages=tuple(messages),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def normalize_finish_reason(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, LLMFinishReason):
        return value.value
    if not isinstance(value, str):
        return LLMFinishReason.UNKNOWN.value
    normalized = value.strip().lower()
    if not normalized:
        return None
    aliases = {
        "max_tokens": LLMFinishReason.LENGTH.value,
        "max_output_tokens": LLMFinishReason.LENGTH.value,
        "end_turn": LLMFinishReason.STOP.value,
        "stop_sequence": LLMFinishReason.STOP.value,
        "safety": LLMFinishReason.SAFETY.value,
        "content_filter": LLMFinishReason.CONTENT_FILTER.value,
    }
    return aliases.get(normalized, normalized)


def _coerce_non_negative_int(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        msg = "Metric must be a non-negative integer."
        raise ValueError(msg)
    metric = int(value)
    if metric < 0 or not isfinite(metric):
        msg = "Metric must be a non-negative integer."
        raise ValueError(msg)
    return metric


def _coerce_optional_non_negative_int(value: int | None) -> int | None:
    if value is None:
        return None
    return _coerce_non_negative_int(value)


def _coerce_positive_int(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        msg = "Metric must be a positive integer."
        raise ValueError(msg)
    metric = int(value)
    if metric <= 0 or not isfinite(metric):
        msg = "Metric must be a positive integer."
        raise ValueError(msg)
    return metric


def _coerce_temperature(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        msg = "Temperature must be a finite number."
        raise ValueError(msg)
    temperature = float(value)
    if not isfinite(temperature) or temperature < 0.0 or temperature > 2.0:
        msg = "Temperature must be between 0 and 2."
        raise ValueError(msg)
    return temperature
