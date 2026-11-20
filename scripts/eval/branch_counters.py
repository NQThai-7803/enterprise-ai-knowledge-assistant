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
# Question/evidence cosines, one counter per route and 0.01 bucket,
# read as "similarity_<route>_<bucket>" (route: llm or local).
_SIMILARITY = re.compile(
    r"^enterprise_ai_rag_question_evidence_similarity_total"
    r'\{bucket="([^"]+)",route="([^"]+)"\} (\d+)$',
    re.M,
)


def parse(text: str) -> dict[str, int] | None:
    counts = {branch: int(value) for branch, value in _SAMPLE.findall(text)}
    if not counts:
        return None
    counts.update(
        {f"similarity_{route}_{b}": int(value) for b, route, value in _SIMILARITY.findall(text)}
    )
    return counts


def similarities(delta: Mapping[str, int] | None, route: str = "llm") -> list[float] | None:
    """Every cosine one route computed in a delta, lowest first, with repeats; None when the
    delta is unknown."""
    if delta is None:
        return None
    prefix = f"similarity_{route}_"
    return sorted(
        float(key.removeprefix(prefix))
        for key, count in delta.items()
        if key.startswith(prefix)
        for _ in range(count)
    )


def read(base_url: str, timeout: float = 30.0) -> dict[str, int] | None:
    try:
        with urlopen(f"{base_url.rstrip('/')}/metrics", timeout=timeout) as response:
            return parse(response.read().decode("utf-8"))
    except (URLError, OSError):
        return None


# The per-question fields a runner records and a grader copies (DEC-041).
ROUTE_FIELDS = ("answer_route", "retrieved", "no_answer_reasons")
_ROUTE = "answer_route_"
_NO_ANSWER = "no_answer_"


def answer_route(change: Mapping[str, int] | None) -> str | None:
    """The route of one answer from the counter change around it: the API's own label
    (det_<route>, repair_<route>, llm_legacy, llm_simple, refusal_gate), or on an older API
    deterministic / llm; None when unknown or when more than one answer moved the counters."""
    if change is None:
        return None
    routes = {k.removeprefix(_ROUTE): v for k, v in change.items() if k.startswith(_ROUTE) and v}
    if routes:
        return next(iter(routes)) if list(routes.values()) == [1] else None
    pair = (change.get("route_deterministic", 0), change.get("route_llm", 0))
    return {(1, 0): "deterministic", (0, 1): "llm"}.get(pair)


def coarse_route(route: str | None) -> str | None:
    """deterministic (a server-built answer) or llm (anything else) for a route label."""
    if route is None:
        return None
    return "deterministic" if route.startswith(("deterministic", "det_", "repair_")) else "llm"


def route_fields(
    before: Mapping[str, int] | None, after: Mapping[str, int] | None
) -> dict[str, object]:
    """answer_route and every no-answer reason the API counted while answering one question
    (intermediate attempts included); None when the counters are unknown."""
    change = delta(before, after)
    reasons = None
    if change is not None:
        reasons = sorted(
            k.removeprefix(_NO_ANSWER) for k, v in change.items() if v and k.startswith(_NO_ANSWER)
        )
    return {"answer_route": answer_route(change), "no_answer_reasons": reasons}


# shortcut: a restart before the first count reads as 0; eval metadata records resumed runs.
def delta(start: Mapping[str, int] | None, end: Mapping[str, int] | None) -> dict[str, int] | None:
    if start is None or end is None or any(end.get(key, 0) < start[key] for key in start):
        return None
    return {key: value - start.get(key, 0) for key, value in end.items()}
