from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ComponentStatus = Literal[
    "ok",
    "degraded",
    "unavailable",
    "disabled",
    "misconfigured",
    "not_configured",
]
OverallStatus = Literal["healthy", "degraded", "unhealthy"]
ProviderStatus = Literal["healthy", "disabled", "misconfigured", "unhealthy"]
QueueKind = Literal["document", "ocr", "embedding", "retry", "dead_letter"]
SafeDetailValue = str | int | float | bool | None | list[str]


class AdminComponentCheck(BaseModel):
    name: str
    status: ComponentStatus
    enabled: bool | None = None
    message: str | None = None
    details: dict[str, SafeDetailValue] = Field(default_factory=dict)


class AdminHealthResponse(BaseModel):
    status: OverallStatus
    generated_at: datetime
    checks: list[AdminComponentCheck]


class AdminProviderStatus(BaseModel):
    provider_type: Literal["llm", "web_search"]
    provider: str
    status: ProviderStatus
    enabled: bool
    configured: bool
    display_name: str | None = None
    model: str | None = None
    external_allowed: bool | None = None
    connectivity_checked: bool = False
    message: str | None = None


class AdminProvidersResponse(BaseModel):
    llm: AdminProviderStatus
    web_search: AdminProviderStatus


class AdminWorkerInfo(BaseModel):
    name: str
    status: ComponentStatus
    queues: list[str] = Field(default_factory=list)
    pool: str | None = None


class AdminWorkersResponse(BaseModel):
    status: OverallStatus
    active_worker_count: int = Field(ge=0)
    workers: list[AdminWorkerInfo]
    registered_tasks: list[str] = Field(default_factory=list)
    message: str | None = None


class AdminQueueStatus(BaseModel):
    kind: QueueKind
    name: str
    status: ComponentStatus
    configured: bool
    pending: int | None = Field(default=None, ge=0)
    consumer: str | None = None
    message: str | None = None


class AdminQueuesResponse(BaseModel):
    status: OverallStatus
    queues: list[AdminQueueStatus]


class AdminDocumentStatistics(BaseModel):
    total: int = Field(ge=0)
    deleted: int = Field(ge=0)
    by_status: dict[str, int] = Field(default_factory=dict)


class AdminUserStatistics(BaseModel):
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    inactive: int = Field(ge=0)
    by_role: dict[str, int] = Field(default_factory=dict)


class AdminSessionStatistics(BaseModel):
    total: int = Field(ge=0)
    archived: int = Field(ge=0)


class AdminMessageStatistics(BaseModel):
    total: int = Field(ge=0)
    by_role: dict[str, int] = Field(default_factory=dict)


class AdminFeedbackStatistics(BaseModel):
    total: int = Field(ge=0)
    by_rating: dict[str, int] = Field(default_factory=dict)


class AdminCountStatistic(BaseModel):
    total: int = Field(ge=0)


class AdminStatisticsResponse(BaseModel):
    documents: AdminDocumentStatistics
    chunks: AdminCountStatistic
    embeddings: AdminCountStatistic
    users: AdminUserStatistics
    departments: AdminCountStatistic
    chat_sessions: AdminSessionStatistics
    messages: AdminMessageStatistics
    feedback: AdminFeedbackStatistics
    audit_logs: AdminCountStatistic


class AdminVersionResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    python_version: str
    api_prefix: str
    migration_head: str | None = None
    database_revision: str | None = None
    started_at: datetime | None = None
    uptime_seconds: int = Field(ge=0)


class AdminSystemResponse(BaseModel):
    generated_at: datetime
    version: AdminVersionResponse
    uptime_seconds: int = Field(ge=0)
    health: AdminHealthResponse
    providers: AdminProvidersResponse
    workers: AdminWorkersResponse
    queues: AdminQueuesResponse
    statistics: AdminStatisticsResponse
