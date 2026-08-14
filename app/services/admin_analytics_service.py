from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessValidationError
from app.document_processing.document_types import JPEG_MIME_TYPE, PNG_MIME_TYPE
from app.llm.manager import LLMProviderManager
from app.models import (
    AuditLog,
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    CitationSourceType,
    Department,
    Document,
    DocumentStatus,
    Feedback,
    FeedbackRating,
    MessageCitation,
    User,
)
from app.schemas.admin_analytics import (
    AdminAnalyticsOverviewResponse,
    AdminAuditAnalyticsResponse,
    AdminChatAnalyticsResponse,
    AdminFeedbackAnalyticsResponse,
    AdminLLMAnalyticsResponse,
    AdminOCRAnalyticsResponse,
    AdminSearchAnalyticsResponse,
    AdminUserAnalyticsResponse,
    AnalyticsCountItem,
    AnalyticsMetric,
    AnalyticsPeriod,
    AnalyticsRatingTrendPoint,
    AnalyticsReportKind,
    AnalyticsTrendPoint,
    AnalyticsWindow,
    ModelUsageAnalyticsItem,
    ProviderUsageAnalyticsItem,
    TokenUsageAnalytics,
    TopDepartmentAnalyticsItem,
    TopDocumentAnalyticsItem,
    TopQueryAnalyticsItem,
    TopUserAnalyticsItem,
)

TOP_ANALYTICS_LIMIT = 10
TOP_AUDIT_ACTION_LIMIT = 20
IMAGE_OCR_MIME_TYPES = (PNG_MIME_TYPE, JPEG_MIME_TYPE)


@dataclass(frozen=True, slots=True)
class AnalyticsDateWindow:
    period: AnalyticsPeriod
    date_from: datetime
    date_to: datetime

    def to_schema(self) -> AnalyticsWindow:
        return AnalyticsWindow(
            period=self.period,
            date_from=self.date_from,
            date_to=self.date_to,
        )


class AdminAnalyticsService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        application: Any | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.application = application
        self.settings = settings or _settings_from_application(application) or get_settings()

    async def get_overview(self, window: AnalyticsDateWindow) -> AdminAnalyticsOverviewResponse:
        chat = await self.get_chat(window)
        users = await self.get_users(window)
        search = await self.get_search(window)
        ocr = await self.get_ocr(window)
        llm = await self.get_llm(window)
        feedback = await self.get_feedback(window)
        audit = await self.get_audit(window)
        documents = await _count_where(
            self.session,
            Document,
            _between(Document.created_at, window),
            Document.is_deleted.is_(False),
        )
        return AdminAnalyticsOverviewResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            questions=chat.questions,
            sessions=chat.sessions,
            active_users=users.active_users,
            documents=documents,
            feedback=feedback.total_feedback,
            audit_events=audit.total_events,
            internal_searches=search.internal_searches,
            hybrid_searches=search.hybrid_searches,
            web_searches=search.web_searches,
            ocr_jobs=ocr.ocr_jobs,
            llm_messages=chat.assistant_messages,
            total_tokens=llm.token_usage.total_tokens,
        )

    async def get_chat(self, window: AnalyticsDateWindow) -> AdminChatAnalyticsResponse:
        questions = await _count_where(
            self.session,
            ChatMessage,
            ChatMessage.role == ChatMessageRole.USER,
            _between(ChatMessage.created_at, window),
        )
        sessions = await _count_where(
            self.session,
            ChatSession,
            _between(ChatSession.created_at, window),
        )
        assistant_messages = await _count_where(
            self.session,
            ChatMessage,
            ChatMessage.role == ChatMessageRole.ASSISTANT,
            _between(ChatMessage.created_at, window),
        )
        averages = await _chat_generation_averages(self.session, window)
        token_usage = await _token_usage(self.session, window)
        return AdminChatAnalyticsResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            questions=questions,
            sessions=sessions,
            assistant_messages=assistant_messages,
            average_response_time_ms=averages["average_response_time_ms"],
            average_retrieval_time_ms=_unavailable_metric(
                unit="ms",
                message="Retrieval duration is not persisted separately from answer generation.",
            ),
            average_streaming_usage=_unavailable_metric(
                unit="events",
                message="Streaming transport usage is not persisted per message.",
            ),
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
            total_tokens=token_usage.total_tokens,
            question_trends=await _message_trend(
                self.session,
                role=ChatMessageRole.USER,
                window=window,
            ),
        )

    async def get_users(self, window: AnalyticsDateWindow) -> AdminUserAnalyticsResponse:
        active_users = await _active_user_count(self.session, window)
        total_active_accounts = await _count_where(
            self.session,
            User,
            User.is_active.is_(True),
        )
        new_users = await _count_where(
            self.session,
            User,
            _between(User.created_at, window),
        )
        return AdminUserAnalyticsResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            active_users=active_users,
            total_active_accounts=total_active_accounts,
            new_users=new_users,
            top_users=await _top_users(self.session, window),
            top_departments=await _top_departments(self.session, window),
        )

    async def get_search(self, window: AnalyticsDateWindow) -> AdminSearchAnalyticsResponse:
        questions = await _count_where(
            self.session,
            ChatMessage,
            ChatMessage.role == ChatMessageRole.USER,
            _between(ChatMessage.created_at, window),
        )
        internal, hybrid, web = await _citation_search_counts(self.session, window)
        categorized = internal + hybrid + web
        return AdminSearchAnalyticsResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            internal_searches=internal,
            hybrid_searches=hybrid,
            web_searches=web,
            uncategorized_questions=max(0, questions - categorized),
            top_queries=await _top_query_hashes(self.session, window),
            top_documents=await _top_documents(self.session, window),
            classification_source="message_citations.source_type",
        )

    async def get_ocr(self, window: AnalyticsDateWindow) -> AdminOCRAnalyticsResponse:
        conditions = (
            Document.mime_type.in_(IMAGE_OCR_MIME_TYPES),
            _between(Document.created_at, window),
            Document.is_deleted.is_(False),
        )
        jobs = await _count_where(self.session, Document, *conditions)
        succeeded = await _count_where(
            self.session,
            Document,
            *conditions,
            Document.status == DocumentStatus.READY,
        )
        failed = await _count_where(
            self.session,
            Document,
            *conditions,
            Document.status == DocumentStatus.FAILED,
        )
        by_status = await _group_counts(
            self.session,
            Document.status,
            Document,
            *conditions,
        )
        return AdminOCRAnalyticsResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            ocr_jobs=jobs,
            succeeded=succeeded,
            failed=failed,
            success_rate_percent=_percent(succeeded, jobs),
            failure_rate_percent=_percent(failed, jobs),
            average_ocr_time_ms=_unavailable_metric(
                unit="ms",
                message="OCR duration is not persisted by the document processing pipeline.",
            ),
            pages_processed=jobs if jobs > 0 else 0,
            by_status=by_status,
            source="partial_inference_from_image_documents",
        )

    async def get_llm(self, window: AnalyticsDateWindow) -> AdminLLMAnalyticsResponse:
        assistant_messages = await _count_where(
            self.session,
            ChatMessage,
            ChatMessage.role == ChatMessageRole.ASSISTANT,
            _between(ChatMessage.created_at, window),
        )
        token_usage = await _token_usage(self.session, window)
        average_response_time = (await _chat_generation_averages(self.session, window))[
            "average_response_time_ms"
        ]
        failures = await _count_where(
            self.session,
            AuditLog,
            _between(AuditLog.created_at, window),
            AuditLog.outcome == "FAILURE",
            AuditLog.error_code.ilike("LLM%"),
        )
        health = self._llm_manager().configuration_health()
        provider_usage = [
            ProviderUsageAnalyticsItem(
                provider=health.provider,
                model=health.model,
                message_count=assistant_messages,
                historical_attribution=False,
            )
        ]
        model_usage = (
            [
                ModelUsageAnalyticsItem(
                    model=health.model,
                    message_count=assistant_messages,
                    historical_attribution=False,
                )
            ]
            if health.model
            else []
        )
        return AdminLLMAnalyticsResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            provider_usage=provider_usage,
            model_usage=model_usage,
            latency=AnalyticsMetric(
                value=average_response_time,
                available=average_response_time is not None,
                unit="ms",
                message=None
                if average_response_time is not None
                else "No assistant response latency data is available in this window.",
            ),
            failures=failures,
            token_usage=token_usage,
            usage_source=(
                "chat_messages_current_configuration; per-message provider/model is not persisted"
            ),
        )

    async def get_feedback(self, window: AnalyticsDateWindow) -> AdminFeedbackAnalyticsResponse:
        helpful = await _count_where(
            self.session,
            Feedback,
            Feedback.rating == FeedbackRating.HELPFUL,
            _between(Feedback.updated_at, window),
        )
        not_helpful = await _count_where(
            self.session,
            Feedback,
            Feedback.rating == FeedbackRating.NOT_HELPFUL,
            _between(Feedback.updated_at, window),
        )
        total = helpful + not_helpful
        return AdminFeedbackAnalyticsResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            total_feedback=total,
            helpful=helpful,
            not_helpful=not_helpful,
            helpful_percent=_percent(helpful, total),
            not_helpful_percent=_percent(not_helpful, total),
            feedback_trend=await _feedback_trend(self.session, window),
        )

    async def get_audit(self, window: AnalyticsDateWindow) -> AdminAuditAnalyticsResponse:
        action_counts = await _audit_action_counts(self.session, window)
        by_outcome = await _group_counts(
            self.session,
            AuditLog.outcome,
            AuditLog,
            _between(AuditLog.created_at, window),
        )
        total = sum(action_counts.values())
        successes = by_outcome.get("SUCCESS", 0)
        failures = by_outcome.get("FAILURE", 0)
        return AdminAuditAnalyticsResponse(
            generated_at=_utc_now(),
            window=window.to_schema(),
            total_events=total,
            successes=successes,
            failures=failures,
            login=_sum_actions(action_counts, lambda action: action.startswith("AUTH_LOGIN_")),
            upload=action_counts.get("DOCUMENT_UPLOADED", 0),
            download=action_counts.get("DOCUMENT_DOWNLOADED", 0),
            delete=action_counts.get("DOCUMENT_DELETED", 0),
            permission=_sum_actions(
                action_counts,
                lambda action: action.startswith("DOCUMENT_PERMISSION_"),
            ),
            admin_actions=_sum_actions(
                action_counts,
                lambda action: action.startswith(("USER_", "DEPARTMENT_", "DOCUMENT_PERMISSION_")),
            ),
            by_action=[
                AnalyticsCountItem(key=action, count=count)
                for action, count in sorted(
                    action_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )[:TOP_AUDIT_ACTION_LIMIT]
            ],
            by_outcome=by_outcome,
        )

    async def get_report(
        self,
        *,
        report: AnalyticsReportKind,
        window: AnalyticsDateWindow,
    ) -> Any:
        if report == "overview":
            return await self.get_overview(window)
        if report == "chat":
            return await self.get_chat(window)
        if report == "users":
            return await self.get_users(window)
        if report == "search":
            return await self.get_search(window)
        if report == "ocr":
            return await self.get_ocr(window)
        if report == "llm":
            return await self.get_llm(window)
        if report == "feedback":
            return await self.get_feedback(window)
        if report == "audit":
            return await self.get_audit(window)
        raise BusinessValidationError("Analytics report is not supported.")

    def _llm_manager(self) -> LLMProviderManager:
        manager = getattr(getattr(self.application, "state", None), "llm_provider_manager", None)
        if isinstance(manager, LLMProviderManager):
            return manager
        return LLMProviderManager(self.settings)


def resolve_analytics_window(
    *,
    period: AnalyticsPeriod,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    now: datetime | None = None,
) -> AnalyticsDateWindow:
    current = now or _utc_now()
    if current.tzinfo is None or current.tzinfo.utcoffset(current) is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)

    if period == "custom":
        if date_from is None or date_to is None:
            raise BusinessValidationError("Custom analytics range requires date_from and date_to.")
        start = _require_aware_utc(date_from)
        end = _require_aware_utc(date_to)
        if start > end:
            raise BusinessValidationError("Analytics date range is invalid.")
        return AnalyticsDateWindow(period=period, date_from=start, date_to=end)

    if date_from is not None or date_to is not None:
        raise BusinessValidationError("date_from and date_to are only supported with custom range.")
    if period == "today":
        start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "7d":
        start = current - timedelta(days=7)
    elif period == "30d":
        start = current - timedelta(days=30)
    elif period == "90d":
        start = current - timedelta(days=90)
    else:
        raise BusinessValidationError("Analytics period is not supported.")
    return AnalyticsDateWindow(period=period, date_from=start, date_to=current)


def build_export_payload(
    *,
    report: AnalyticsReportKind,
    data: Any,
) -> dict[str, Any]:
    return {
        "report": report,
        "generated_at": _utc_now().isoformat(),
        "data": data.model_dump(mode="json"),
    }


def analytics_payload_to_csv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(("field", "value"))
    for key, value in _flatten_export_payload(payload):
        writer.writerow((key, value))
    return output.getvalue()


async def _chat_generation_averages(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> dict[str, float | None]:
    statement = select(func.avg(ChatMessage.response_time_ms)).where(
        ChatMessage.role == ChatMessageRole.ASSISTANT,
        ChatMessage.response_time_ms.is_not(None),
        _between(ChatMessage.created_at, window),
    )
    return {"average_response_time_ms": _optional_float(await session.scalar(statement))}


async def _token_usage(session: AsyncSession, window: AnalyticsDateWindow) -> TokenUsageAnalytics:
    statement = select(
        func.coalesce(func.sum(ChatMessage.prompt_tokens), 0),
        func.coalesce(func.sum(ChatMessage.completion_tokens), 0),
    ).where(
        ChatMessage.role == ChatMessageRole.ASSISTANT,
        _between(ChatMessage.created_at, window),
    )
    input_tokens, output_tokens = (await session.execute(statement)).one()
    input_total = int(input_tokens or 0)
    output_total = int(output_tokens or 0)
    return TokenUsageAnalytics(
        input_tokens=input_total,
        output_tokens=output_total,
        total_tokens=input_total + output_total,
    )


async def _message_trend(
    session: AsyncSession,
    *,
    role: ChatMessageRole,
    window: AnalyticsDateWindow,
) -> list[AnalyticsTrendPoint]:
    bucket = func.date_trunc("day", ChatMessage.created_at)
    statement = (
        select(bucket, func.count())
        .where(ChatMessage.role == role, _between(ChatMessage.created_at, window))
        .group_by(bucket)
        .order_by(bucket)
    )
    rows = await session.execute(statement)
    return [
        AnalyticsTrendPoint(date=_date_bucket_to_iso(bucket_value), count=int(count or 0))
        for bucket_value, count in rows
    ]


async def _feedback_trend(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> list[AnalyticsRatingTrendPoint]:
    bucket = func.date_trunc("day", Feedback.updated_at)
    statement = (
        select(bucket, Feedback.rating, func.count())
        .where(_between(Feedback.updated_at, window))
        .group_by(bucket, Feedback.rating)
        .order_by(bucket)
    )
    grouped: dict[str, dict[str, int]] = {}
    rows = await session.execute(statement)
    for bucket_value, rating, count in rows:
        date_key = _date_bucket_to_iso(bucket_value)
        grouped.setdefault(date_key, {"helpful": 0, "not_helpful": 0})
        if rating == FeedbackRating.HELPFUL:
            grouped[date_key]["helpful"] = int(count or 0)
        elif rating == FeedbackRating.NOT_HELPFUL:
            grouped[date_key]["not_helpful"] = int(count or 0)
    return [
        AnalyticsRatingTrendPoint(
            date=date_key,
            helpful=counts["helpful"],
            not_helpful=counts["not_helpful"],
        )
        for date_key, counts in sorted(grouped.items())
    ]


async def _active_user_count(session: AsyncSession, window: AnalyticsDateWindow) -> int:
    user_ids: set[str] = set()
    chat_statement = (
        select(distinct(ChatSession.user_id))
        .join(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .where(_between(ChatMessage.created_at, window))
    )
    feedback_statement = select(distinct(Feedback.user_id)).where(
        _between(Feedback.updated_at, window)
    )
    audit_statement = select(distinct(AuditLog.user_id)).where(
        AuditLog.user_id.is_not(None),
        _between(AuditLog.created_at, window),
    )
    for statement in (chat_statement, feedback_statement, audit_statement):
        rows = await session.execute(statement)
        user_ids.update(str(user_id) for user_id in rows.scalars() if user_id is not None)
    return len(user_ids)


async def _top_users(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> list[TopUserAnalyticsItem]:
    question_count = func.count(ChatMessage.id)
    session_count = func.count(distinct(ChatSession.id))
    statement = (
        select(ChatSession.user_id, User.department_id, question_count, session_count)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .join(User, ChatSession.user_id == User.id)
        .where(ChatMessage.role == ChatMessageRole.USER, _between(ChatMessage.created_at, window))
        .group_by(ChatSession.user_id, User.department_id)
        .order_by(question_count.desc(), ChatSession.user_id)
        .limit(TOP_ANALYTICS_LIMIT)
    )
    rows = await session.execute(statement)
    return [
        TopUserAnalyticsItem(
            user_id=user_id,
            department_id=department_id,
            question_count=int(questions or 0),
            session_count=int(sessions or 0),
        )
        for user_id, department_id, questions, sessions in rows
    ]


async def _top_departments(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> list[TopDepartmentAnalyticsItem]:
    question_count = func.count(ChatMessage.id)
    user_count = func.count(distinct(ChatSession.user_id))
    statement = (
        select(
            User.department_id,
            Department.code,
            Department.name,
            question_count,
            user_count,
        )
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .join(User, ChatSession.user_id == User.id)
        .outerjoin(Department, User.department_id == Department.id)
        .where(ChatMessage.role == ChatMessageRole.USER, _between(ChatMessage.created_at, window))
        .group_by(User.department_id, Department.code, Department.name)
        .order_by(question_count.desc(), User.department_id)
        .limit(TOP_ANALYTICS_LIMIT)
    )
    rows = await session.execute(statement)
    return [
        TopDepartmentAnalyticsItem(
            department_id=department_id,
            department_code=department_code,
            department_name=department_name,
            question_count=int(questions or 0),
            active_user_count=int(users or 0),
        )
        for department_id, department_code, department_name, questions, users in rows
    ]


async def _citation_search_counts(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> tuple[int, int, int]:
    statement = (
        select(MessageCitation.message_id, MessageCitation.source_type)
        .join(ChatMessage, MessageCitation.message_id == ChatMessage.id)
        .where(_between(ChatMessage.created_at, window))
    )
    rows = await session.execute(statement)
    by_message: dict[str, set[str]] = {}
    for message_id, source_type in rows:
        by_message.setdefault(str(message_id), set()).add(str(source_type))
    internal = 0
    hybrid = 0
    web = 0
    for source_types in by_message.values():
        has_internal = CitationSourceType.INTERNAL.value in source_types
        has_web = CitationSourceType.WEB.value in source_types
        if has_internal and has_web:
            hybrid += 1
        elif has_web:
            web += 1
        elif has_internal:
            internal += 1
    return internal, hybrid, web


async def _top_query_hashes(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> list[TopQueryAnalyticsItem]:
    normalized_query = func.lower(func.btrim(ChatMessage.content))
    query_count = func.count(ChatMessage.id)
    statement = (
        select(normalized_query, query_count)
        .where(ChatMessage.role == ChatMessageRole.USER, _between(ChatMessage.created_at, window))
        .group_by(normalized_query)
        .order_by(query_count.desc())
        .limit(TOP_ANALYTICS_LIMIT * 5)
    )
    rows = await session.execute(statement)
    counts: dict[str, int] = {}
    for query, count in rows:
        query_hash = _hash_query(str(query))
        counts[query_hash] = counts.get(query_hash, 0) + int(count or 0)
    return [
        TopQueryAnalyticsItem(query_hash=query_hash, count=count)
        for query_hash, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[
            :TOP_ANALYTICS_LIMIT
        ]
    ]


async def _top_documents(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> list[TopDocumentAnalyticsItem]:
    citation_count = func.count(MessageCitation.id)
    statement = (
        select(Document.id, Document.title, citation_count)
        .join(MessageCitation, MessageCitation.document_id == Document.id)
        .join(ChatMessage, MessageCitation.message_id == ChatMessage.id)
        .where(
            MessageCitation.source_type == CitationSourceType.INTERNAL.value,
            _between(ChatMessage.created_at, window),
            Document.is_deleted.is_(False),
        )
        .group_by(Document.id, Document.title)
        .order_by(citation_count.desc(), Document.id)
        .limit(TOP_ANALYTICS_LIMIT)
    )
    rows = await session.execute(statement)
    return [
        TopDocumentAnalyticsItem(
            document_id=document_id,
            title=title,
            citation_count=int(count or 0),
        )
        for document_id, title, count in rows
    ]


async def _audit_action_counts(
    session: AsyncSession,
    window: AnalyticsDateWindow,
) -> dict[str, int]:
    statement = (
        select(AuditLog.action, func.count())
        .where(_between(AuditLog.created_at, window))
        .group_by(AuditLog.action)
    )
    rows = await session.execute(statement)
    return {str(action): int(count or 0) for action, count in rows}


async def _count_where(
    session: AsyncSession,
    model: type,
    *conditions: Any,
) -> int:
    statement = select(func.count()).select_from(model)
    if conditions:
        statement = statement.where(*conditions)
    return int(await session.scalar(statement) or 0)


async def _group_counts(
    session: AsyncSession,
    column: Any,
    model: type,
    *conditions: Any,
) -> dict[str, int]:
    statement = select(column, func.count()).select_from(model)
    if conditions:
        statement = statement.where(*conditions)
    statement = statement.group_by(column)
    rows = await session.execute(statement)
    return {_safe_key(key): int(count or 0) for key, count in rows}


def _between(column: Any, window: AnalyticsDateWindow) -> Any:
    return and_(column >= window.date_from, column <= window.date_to)


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise BusinessValidationError("Analytics date range must include timezone offsets.")
    return value.astimezone(UTC)


def _unavailable_metric(*, unit: str, message: str) -> AnalyticsMetric:
    return AnalyticsMetric(value=None, available=False, unit=unit, message=message)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 2)


def _safe_key(value: Any) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def _date_bucket_to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)


def _hash_query(value: str) -> str:
    normalized = " ".join(value.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _sum_actions(action_counts: dict[str, int], predicate: Any) -> int:
    return sum(count for action, count in action_counts.items() if predicate(action))


def _settings_from_application(application: Any | None) -> Settings | None:
    manager = getattr(getattr(application, "state", None), "llm_provider_manager", None)
    settings = getattr(manager, "settings", None)
    return settings if isinstance(settings, Settings) else None


def _flatten_export_payload(payload: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def visit(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(f"{prefix}.{key}" if prefix else str(key), child)
            return
        if isinstance(value, list):
            rows.append((prefix, json.dumps(value, sort_keys=True, separators=(",", ":"))))
            return
        rows.append((prefix, "" if value is None else str(value)))

    visit("", payload)
    return rows


def _utc_now() -> datetime:
    return datetime.now(UTC)
