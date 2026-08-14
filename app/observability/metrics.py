from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock

from starlette.types import Scope

METRIC_PREFIX = "enterprise_ai"
MAX_ROUTE_LABEL_LENGTH = 160
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
