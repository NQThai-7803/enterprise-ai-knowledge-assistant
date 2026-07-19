from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")


def run_async(coroutine: Coroutine[object, object, T]) -> T:  # noqa: UP047
    return asyncio.run(coroutine)
