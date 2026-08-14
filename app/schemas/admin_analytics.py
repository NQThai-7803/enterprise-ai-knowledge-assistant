from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AnalyticsPeriod = Literal["today", "7d", "30d", "90d", "custom"]
AnalyticsReportKind = Literal[
    "overview",
    "chat",
    "users",
    "search",
    "ocr",
    "llm",
    "feedback",
    "audit",
]
AnalyticsExportFormat = Literal["json", "csv", "pdf"]


class AnalyticsWindow(BaseModel):
    period: AnalyticsPeriod
    date_from: datetime
    date_to: datetime
    timezone: Literal["UTC"] = "UTC"


class AnalyticsMetric(BaseModel):
    value: float | None = None
    available: bool
    unit: str | None = None
    message: str | None = None


class AnalyticsTrendPoint(BaseModel):
    date: str
    count: int = Field(ge=0)


class AnalyticsRatingTrendPoint(BaseModel):
    date: str
    helpful: int = Field(ge=0)
    not_helpful: int = Field(ge=0)


class AnalyticsCountItem(BaseModel):
    key: str
    count: int = Field(ge=0)


class AdminAnalyticsOverviewResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    questions: int = Field(ge=0)
    sessions: int = Field(ge=0)
    active_users: int = Field(ge=0)
    documents: int = Field(ge=0)
    feedback: int = Field(ge=0)
    audit_events: int = Field(ge=0)
    internal_searches: int = Field(ge=0)
    hybrid_searches: int = Field(ge=0)
    web_searches: int = Field(ge=0)
    ocr_jobs: int = Field(ge=0)
    llm_messages: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class AdminChatAnalyticsResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    questions: int = Field(ge=0)
    sessions: int = Field(ge=0)
    assistant_messages: int = Field(ge=0)
    average_response_time_ms: float | None = None
    average_retrieval_time_ms: AnalyticsMetric
    average_streaming_usage: AnalyticsMetric
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    question_trends: list[AnalyticsTrendPoint] = Field(default_factory=list)


class TopUserAnalyticsItem(BaseModel):
    user_id: UUID
    department_id: UUID | None = None
    question_count: int = Field(ge=0)
    session_count: int = Field(ge=0)


class TopDepartmentAnalyticsItem(BaseModel):
    department_id: UUID | None = None
    department_code: str | None = None
    department_name: str | None = None
    question_count: int = Field(ge=0)
    active_user_count: int = Field(ge=0)


class AdminUserAnalyticsResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    active_users: int = Field(ge=0)
    total_active_accounts: int = Field(ge=0)
    new_users: int = Field(ge=0)
    top_users: list[TopUserAnalyticsItem] = Field(default_factory=list)
    top_departments: list[TopDepartmentAnalyticsItem] = Field(default_factory=list)


class TopQueryAnalyticsItem(BaseModel):
    query_hash: str
    count: int = Field(ge=0)
    raw_query_available: Literal[False] = False


class TopDocumentAnalyticsItem(BaseModel):
    document_id: UUID
    title: str
    citation_count: int = Field(ge=0)


class AdminSearchAnalyticsResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    internal_searches: int = Field(ge=0)
    hybrid_searches: int = Field(ge=0)
    web_searches: int = Field(ge=0)
    uncategorized_questions: int = Field(ge=0)
    top_queries: list[TopQueryAnalyticsItem] = Field(default_factory=list)
    top_documents: list[TopDocumentAnalyticsItem] = Field(default_factory=list)
    classification_source: str


class AdminOCRAnalyticsResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    ocr_jobs: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    success_rate_percent: float | None = None
    failure_rate_percent: float | None = None
    average_ocr_time_ms: AnalyticsMetric
    pages_processed: int | None = Field(default=None, ge=0)
    by_status: dict[str, int] = Field(default_factory=dict)
    source: str


class ProviderUsageAnalyticsItem(BaseModel):
    provider: str
    model: str | None = None
    message_count: int = Field(ge=0)
    historical_attribution: bool


class ModelUsageAnalyticsItem(BaseModel):
    model: str
    message_count: int = Field(ge=0)
    historical_attribution: bool


class TokenUsageAnalytics(BaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class AdminLLMAnalyticsResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    provider_usage: list[ProviderUsageAnalyticsItem] = Field(default_factory=list)
    model_usage: list[ModelUsageAnalyticsItem] = Field(default_factory=list)
    latency: AnalyticsMetric
    failures: int = Field(ge=0)
    token_usage: TokenUsageAnalytics
    usage_source: str


class AdminFeedbackAnalyticsResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    total_feedback: int = Field(ge=0)
    helpful: int = Field(ge=0)
    not_helpful: int = Field(ge=0)
    helpful_percent: float | None = None
    not_helpful_percent: float | None = None
    feedback_trend: list[AnalyticsRatingTrendPoint] = Field(default_factory=list)


class AdminAuditAnalyticsResponse(BaseModel):
    generated_at: datetime
    window: AnalyticsWindow
    total_events: int = Field(ge=0)
    successes: int = Field(ge=0)
    failures: int = Field(ge=0)
    login: int = Field(ge=0)
    upload: int = Field(ge=0)
    download: int = Field(ge=0)
    delete: int = Field(ge=0)
    permission: int = Field(ge=0)
    admin_actions: int = Field(ge=0)
    by_action: list[AnalyticsCountItem] = Field(default_factory=list)
    by_outcome: dict[str, int] = Field(default_factory=dict)
