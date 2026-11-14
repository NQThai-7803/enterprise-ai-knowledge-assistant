from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock

from starlette.types import Scope

METRIC_PREFIX = "enterprise_ai"
MAX_ROUTE_LABEL_LENGTH = 160
# FIX 2 group 4a: a rejected answer entered reselection, and the strong-support flag would
# change the sources it can move to. Counted with the flag on or off.
BRANCH_RESELECT_AFTER_REJECTION = "reselect_after_rejection"
BRANCH_RESELECT_GUARD_WOULD_CHANGE = "reselect_guard_would_change"
# FIX 3a: an answer turned into NO_ANSWER by M2, M1a or M1b; counted only with its flag on.
BRANCH_REFUSAL_PHRASE_EXTENDED = "refusal_phrase_extended"
BRANCH_QUESTION_HEAD_MISSING = "question_head_missing"
BRANCH_QUESTION_EVIDENCE_DISSIMILAR = "question_evidence_dissimilar"
# FIX 4 (i): a validated first answer kept after a failed retry, or over a retry that left it.
BRANCH_FIRST_ANSWER_KEPT = "first_answer_kept"
BRANCH_RETRY_ABANDONED_FIRST = "retry_abandoned_first"
# Every persisted answer, by who wrote it: a server-built answer or the LLM path.
BRANCH_ROUTE_DETERMINISTIC = "route_deterministic"
BRANCH_ROUTE_LLM = "route_llm"
ANSWER_BRANCHES = (
    BRANCH_RESELECT_AFTER_REJECTION,
    BRANCH_RESELECT_GUARD_WOULD_CHANGE,
    BRANCH_REFUSAL_PHRASE_EXTENDED,
    BRANCH_QUESTION_HEAD_MISSING,
    BRANCH_QUESTION_EVIDENCE_DISSIMILAR,
    BRANCH_FIRST_ANSWER_KEPT,
    BRANCH_RETRY_ABANDONED_FIRST,
    BRANCH_ROUTE_DETERMINISTIC,
    BRANCH_ROUTE_LLM,
)
_UUID_SEGMENT_PATTERN = re.compile(
    r"(?<=/)[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)"
)
_LONG_SEGMENT_PATTERN = re.compile(r"(?<=/)[A-Za-z0-9_-]{24,}(?=/|$)")
_NUMERIC_SEGMENT_PATTERN = re.compile(r"(?<=/)\d+(?=/|$)")
_UNSAFE_ROUTE_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9_./{}:-]")


@dataclass(frozen=True, slots=True)
class HTTPMetricKey:
    method: str
    route: str
    status_code: int


@dataclass(frozen=True, slots=True)
class HTTPMetricSnapshot:
    method: str
    route: str
    status_code: int
    count: int
    latency_sum_seconds: float
    latency_max_seconds: float


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._http_counts: defaultdict[HTTPMetricKey, int] = defaultdict(int)
        self._http_latency_sum: defaultdict[HTTPMetricKey, float] = defaultdict(float)
        self._http_latency_max: defaultdict[HTTPMetricKey, float] = defaultdict(float)
        self._answer_branch_counts: defaultdict[str, int] = defaultdict(int)
        self._similarity_counts: defaultdict[str, int] = defaultdict(int)

    def record_http_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        latency_seconds: float,
    ) -> None:
        key = HTTPMetricKey(
            method=_safe_method(method),
            route=normalize_route_path(route),
            status_code=int(status_code),
        )
        latency = max(0.0, float(latency_seconds))
        with self._lock:
            self._http_counts[key] += 1
            self._http_latency_sum[key] += latency
            self._http_latency_max[key] = max(self._http_latency_max[key], latency)

    def record_answer_branch(self, branch: str) -> None:
        with self._lock:
            self._answer_branch_counts[branch] += 1

    def record_question_evidence_similarity(self, similarity: float) -> None:
        """Count one computed question/evidence cosine in its 0.01 bucket (floored)."""
        bucket = f"{math.floor(min(max(similarity, 0.0), 1.0) * 100) / 100:.2f}"
        with self._lock:
            self._similarity_counts[bucket] += 1

    def question_evidence_similarity_counts(self) -> dict[str, int]:
        with self._lock:
            return dict(sorted(self._similarity_counts.items()))

    def answer_branch_counts(self) -> dict[str, int]:
        """Every known branch, at 0 when unused, so a missing line means an older stack."""
        with self._lock:
            return {branch: self._answer_branch_counts[branch] for branch in ANSWER_BRANCHES}

    def http_snapshots(self) -> list[HTTPMetricSnapshot]:
        with self._lock:
            return [
                HTTPMetricSnapshot(
                    method=key.method,
                    route=key.route,
                    status_code=key.status_code,
                    count=count,
                    latency_sum_seconds=self._http_latency_sum[key],
                    latency_max_seconds=self._http_latency_max[key],
                )
                for key, count in sorted(
                    self._http_counts.items(),
                    key=lambda item: (item[0].route, item[0].method, item[0].status_code),
                )
            ]

    def reset(self) -> None:
        with self._lock:
            self._http_counts.clear()
            self._http_latency_sum.clear()
            self._http_latency_max.clear()
            self._answer_branch_counts.clear()
            self._similarity_counts.clear()


GLOBAL_METRICS = MetricsRegistry()


def route_template_from_scope(scope: Scope, *, status_code: int | None = None) -> str:
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return normalize_route_path(route_path)
    if status_code == 404:
        return "/unmatched"
    path = scope.get("path")
    return normalize_route_path(path if isinstance(path, str) else "/")


def normalize_route_path(path: str) -> str:
    value = (path or "/").split("?", 1)[0].strip() or "/"
    if not value.startswith("/"):
        value = f"/{value}"
    value = _UUID_SEGMENT_PATTERN.sub("{id}", value)
    value = _LONG_SEGMENT_PATTERN.sub("{id}", value)
    value = _NUMERIC_SEGMENT_PATTERN.sub("{id}", value)
    value = _UNSAFE_ROUTE_CHAR_PATTERN.sub("_", value)
    if len(value) > MAX_ROUTE_LABEL_LENGTH:
        return f"{value[:MAX_ROUTE_LABEL_LENGTH].rstrip('/')}/..."
    return value


def prometheus_labels(labels: Mapping[str, object]) -> str:
    if not labels:
        return ""
    parts = [
        f'{_safe_label_name(str(key))}="{_escape_label_value(str(value))}"'
        for key, value in sorted(labels.items())
    ]
    return "{" + ",".join(parts) + "}"


def prometheus_sample(
    name: str, value: int | float, labels: Mapping[str, object] | None = None
) -> str:
    return f"{name}{prometheus_labels(labels or {})} {_format_number(value)}"


def _safe_method(method: str) -> str:
    normalized = method.upper().strip()
    if not normalized or any(not ("A" <= char <= "Z") for char in normalized):
        return "OTHER"
    return normalized[:16]


def _safe_label_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not safe or safe[0].isdigit():
        return f"label_{safe}"
    return safe


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.6f}"
