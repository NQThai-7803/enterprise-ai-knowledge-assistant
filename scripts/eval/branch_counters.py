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
# Question/evidence cosines, one counter per 0.01 bucket, read as "similarity_<bucket>".
_SIMILARITY = re.compile(
    r'^enterprise_ai_rag_question_evidence_similarity_total\{bucket="([^"]+)"\} (\d+)$', re.M
)


def parse(text: str) -> dict[str, int] | None:
    counts = {branch: int(value) for branch, value in _SAMPLE.findall(text)}
    if not counts:
        return None
    counts.update({f"similarity_{b}": int(value) for b, value in _SIMILARITY.findall(text)})
    return counts


def similarity(delta: Mapping[str, int] | None) -> float | None:
    """The bucket of the one cosine computed in a delta; None when none or several."""
    moved = [key for key, value in (delta or {}).items() if key.startswith("similarity_") and value]
    if len(moved) != 1 or delta[moved[0]] != 1:
        return None
    return float(moved[0].removeprefix("similarity_"))


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
