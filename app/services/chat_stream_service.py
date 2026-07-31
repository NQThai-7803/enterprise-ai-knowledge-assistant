from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request

from app.chat.models import ChatAnswerResult
from app.chat.sse import SSEEventWriter
from app.core.config import Settings, get_settings
from app.core.exceptions import ApplicationError
from app.llm.provider_names import (
    ANTHROPIC_PROVIDER,
    AZURE_OPENAI_PROVIDER,
    GEMINI_PROVIDER,
    LM_STUDIO_PROVIDER,
    OLLAMA_PROVIDER,
    OPENAI_COMPATIBLE_PROVIDER,
    OPENROUTER_PROVIDER,
)
from app.models import User
from app.schemas.chat import ChatAnswerResponse
from app.services.audit_service import AuditContext
from app.services.grounded_answer_service import GroundedAnswerService

STREAM_INTERNAL_ERROR = "STREAM_INTERNAL_ERROR"
STREAM_TIMEOUT = "STREAM_TIMEOUT"
STREAM_CANCELLED = "STREAM_CANCELLED"

_RETRYABLE_ERROR_CODES = {
    "LLM_PROVIDER_RATE_LIMITED",
    "LLM_PROVIDER_TIMEOUT",
    "LLM_PROVIDER_UNAVAILABLE",
    "LLM_RATE_LIMITED",
    "LLM_TIMEOUT",
    STREAM_TIMEOUT,
}


class ChatStreamService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def stream_answer(
        self,
        *,
        request: Request,
        current_user: User,
        session_id: UUID,
        question: str,
        answer_service: GroundedAnswerService,
        audit_context: AuditContext | None = None,
    ) -> AsyncIterator[bytes]:
        request_id = uuid4().hex
        writer = SSEEventWriter(request_id=request_id)
        yield writer.started(
            {
                "request_id": request_id,
                "session_id": str(session_id),
                "provider": self.settings.llm_provider,
                "model": _selected_model(self.settings),
                "strategy": "buffer_after_validation",
            }
        )

        task = asyncio.create_task(
            answer_service.answer_question(
                current_user=current_user,
                session_id=session_id,
                question=question,
                audit_context=audit_context,
            )
        )
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + self.settings.llm_stream_max_duration_seconds
            heartbeat_interval = self.settings.llm_stream_heartbeat_seconds
            while not task.done():
                if await request.is_disconnected():
                    raise _ClientDisconnected
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise TimeoutError
                done, _ = await asyncio.wait(
                    {task},
                    timeout=min(heartbeat_interval, remaining),
                )
                if done:
                    break
                if await request.is_disconnected():
                    raise _ClientDisconnected
                if not writer.terminal_emitted:
                    yield writer.heartbeat()
            result = task.result()
        except _ClientDisconnected:
            await _cancel_task(task)
            return
        except TimeoutError:
            await _cancel_task(task)
            if not await request.is_disconnected():
                yield writer.error(
                    _safe_error_payload(
                        code=STREAM_TIMEOUT,
                        message="Streaming chat request timed out.",
                    )
                )
            return
        except ApplicationError as exc:
            if not await request.is_disconnected():
                yield writer.error(
                    _safe_error_payload(
                        code=exc.code,
                        message=exc.message,
                    )
                )
            return
        except asyncio.CancelledError:
            await _cancel_task(task)
            raise
        except Exception:
            if not await request.is_disconnected():
                yield writer.error(
                    _safe_error_payload(
                        code=STREAM_INTERNAL_ERROR,
                        message="Streaming chat request failed.",
                    )
                )
            return

        if await request.is_disconnected():
            return
        response = ChatAnswerResponse.from_result(result)
        response_data = response.model_dump(mode="json")
        assistant_message = response_data["assistant_message"]
        yield writer.delta(content=assistant_message["content"])
        citations = assistant_message.get("citations") or []
        if citations:
            yield writer.citations_ready({"citations": citations})
        yield writer.completed(_completed_payload(result, response_data, settings=self.settings))


async def _cancel_task(task: asyncio.Task[ChatAnswerResult]) -> None:
    if task.done():
        with suppress(asyncio.CancelledError, Exception):
            task.result()
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def _safe_error_payload(*, code: str, message: str) -> dict[str, object]:
    return {
        "code": code,
        "message": message,
        "retryable": code in _RETRYABLE_ERROR_CODES,
    }


def _completed_payload(
    result: ChatAnswerResult,
    response_data: dict[str, Any],
    *,
    settings: Settings,
) -> dict[str, object]:
    return {
        "message_id": str(result.assistant_message.id),
        "session_id": str(result.session_id),
        "content": result.assistant_message.content,
        "citations": response_data["assistant_message"].get("citations", []),
        "provider": settings.llm_provider,
        "model": _selected_model(settings),
        "usage": _usage_payload(result),
        "grounding_status": result.grounding_status.value,
        "retrieved_chunk_count": result.retrieved_chunk_count,
    }


def _usage_payload(result: ChatAnswerResult) -> dict[str, int | None] | None:
    prompt_tokens = result.assistant_message.prompt_tokens
    completion_tokens = result.assistant_message.completion_tokens
    if prompt_tokens is None and completion_tokens is None:
        return None
    total_tokens = (
        prompt_tokens + completion_tokens
        if prompt_tokens is not None and completion_tokens is not None
        else None
    )
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _selected_model(settings: Settings) -> str | None:
    provider = settings.llm_provider
    model = ""
    if provider == OPENAI_COMPATIBLE_PROVIDER:
        model = settings.llm_model
    elif provider == AZURE_OPENAI_PROVIDER:
        model = settings.llm_azure_deployment
    elif provider == GEMINI_PROVIDER:
        model = settings.llm_gemini_model or settings.llm_model
    elif provider == ANTHROPIC_PROVIDER:
        model = settings.llm_anthropic_model or settings.llm_model
    elif provider == OLLAMA_PROVIDER:
        model = settings.llm_ollama_model or settings.llm_model
    elif provider == LM_STUDIO_PROVIDER:
        model = settings.llm_lm_studio_model or settings.llm_model
    elif provider == OPENROUTER_PROVIDER:
        model = settings.llm_openrouter_model or settings.llm_model
    return model.strip() or None


class _ClientDisconnected(Exception):
    pass
