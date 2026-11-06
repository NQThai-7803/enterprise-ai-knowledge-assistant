"""Read the answer-branch counters from GET /metrics, for the metadata of an eval run.

The counters live in the API process, so a run records the change between its start and its end.
`None` means not measured: the stack does not report them, or the API restarted during the run.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.error import URLError
from urllib.request import urlopen

_SAMPLE = re.compile(r'^enterprise_ai_rag_answer_branch_total\{branch="([^"]+)"\} (\d+)$', re.M)


def parse(text: str) -> dict[str, int] | None:
    counts = {branch: int(value) for branch, value in _SAMPLE.findall(text)}
    return counts or None


def read(base_url: str, timeout: float = 30.0) -> dict[str, int] | None:
    try:
        with urlopen(f"{base_url.rstrip('/')}/metrics", timeout=timeout) as response:
            return parse(response.read().decode("utf-8"))
    except (URLError, OSError):
        return None


# shortcut: a restart before the first count reads as 0; eval metadata records resumed runs.
def delta(start: Mapping[str, int] | None, end: Mapping[str, int] | None) -> dict[str, int] | None:
    if start is None or end is None or any(end.get(key, 0) < start[key] for key in start):
        return None
    return {key: value - start.get(key, 0) for key, value in end.items()}
