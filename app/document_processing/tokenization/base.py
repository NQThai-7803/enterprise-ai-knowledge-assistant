from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class TokenCounter(Protocol):
    def count(self, text: str) -> int:
        """Return the number of tokens in text."""

    def encode(self, text: str) -> tuple[int, ...]:
        """Encode text into an immutable token id sequence."""

    def decode(self, tokens: Sequence[int]) -> str:
        """Decode token ids back to text."""
