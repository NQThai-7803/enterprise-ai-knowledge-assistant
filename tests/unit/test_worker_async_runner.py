from __future__ import annotations

import asyncio

import pytest

from app.workers.async_runner import run_async


def test_run_async_returns_coroutine_result() -> None:
    async def returns_value() -> str:
        return "ok"

    assert run_async(returns_value()) == "ok"


def test_run_async_propagates_exception() -> None:
    async def raises_error() -> None:
        raise RuntimeError("runner failed")

    with pytest.raises(RuntimeError, match="runner failed"):
        run_async(raises_error())


def test_run_async_does_not_swallow_cancellation() -> None:
    async def raises_cancelled() -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        run_async(raises_cancelled())
