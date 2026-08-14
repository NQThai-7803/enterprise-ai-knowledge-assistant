from __future__ import annotations

import asyncio
import platform
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.document_processing.ocr.tesseract_provider import create_tesseract_ocr_provider
from app.llm.manager import LLMProviderManager
from app.llm.models import ProviderHealth
from app.models import (
    AuditLog,
    ChatMessage,
    ChatSession,
    Department,
    Document,
    DocumentChunk,
    Feedback,
    User,
)
from app.schemas.admin_monitoring import (
    AdminComponentCheck,
    AdminCountStatistic,
    AdminDocumentStatistics,
    AdminFeedbackStatistics,
    AdminHealthResponse,
    AdminMessageStatistics,
    AdminProvidersResponse,
    AdminProviderStatus,
    AdminQueuesResponse,
    AdminQueueStatus,
    AdminSessionStatistics,
    AdminStatisticsResponse,
    AdminSystemResponse,
    AdminUserStatistics,
    AdminVersionResponse,
    AdminWorkerInfo,
    AdminWorkersResponse,
    ComponentStatus,
    OverallStatus,
    ProviderStatus,
)
from app.web_search.manager import WebSearchProviderManager
from app.web_search.models import WebSearchProviderHealth
from app.workers.celery_app import celery_app

CELERY_INSPECT_TIMEOUT_SECONDS = 1.0
CELERY_INSPECT_OUTER_TIMEOUT_SECONDS = 3.0
APPLICATION_VERSION_FALLBACK = "0.1.0"


class AdminMonitoringService:
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

    async def get_system(self) -> AdminSystemResponse:
        version = await self.get_version()
        return AdminSystemResponse(
            generated_at=_utc_now(),
            version=version,
            uptime_seconds=version.uptime_seconds,
            health=await self.get_health(),
            providers=self.get_providers(),
            workers=await self.get_workers(),
            queues=await self.get_queues(),
            statistics=await self.get_statistics(),
        )

    async def get_health(self) -> AdminHealthResponse:
        checks = [
            self._api_health(),
            await self._postgres_health(),
            await self._redis_health(),
            await self._worker_health(),
            await self._ocr_health(),
            self._embedding_health(),
            self._llm_health(),
            self._web_search_health(),
            self._streaming_health(),
            self._conversation_health(),
        ]
        return AdminHealthResponse(
            status=_overall_health_status(checks),
            generated_at=_utc_now(),
            checks=checks,
        )

    def get_providers(self) -> AdminProvidersResponse:
        llm_health = self._llm_manager().configuration_health()
        web_search_health = self._web_search_manager().configuration_health()
        return AdminProvidersResponse(
            llm=_llm_provider_status(llm_health, enabled=self.settings.llm_enabled),
            web_search=_web_search_provider_status(
                web_search_health,
                enabled=self.settings.web_search_enabled,
            ),
        )

    async def get_workers(self) -> AdminWorkersResponse:
        try:
            snapshot = await _call_celery_inspect(_inspect_worker_snapshot)
        except Exception:
            return AdminWorkersResponse(
                status="unhealthy",
                active_worker_count=0,
                workers=[],
                registered_tasks=[],
                message="Worker inspection is unavailable.",
            )

        ping = _safe_mapping(snapshot.get("ping"))
        stats = _safe_mapping(snapshot.get("stats"))
        registered = _safe_mapping(snapshot.get("registered"))
        active_queues = _safe_mapping(snapshot.get("active_queues"))
        worker_names = sorted(set(ping) | set(stats) | set(registered) | set(active_queues))
        workers = [
            AdminWorkerInfo(
                name=name,
                status="ok" if name in ping else "unavailable",
                queues=_queue_names(active_queues.get(name)),
                pool=_pool_name(stats.get(name)),
            )
            for name in worker_names
        ]
        registered_tasks = sorted(
            {
                task
                for task_list in registered.values()
                if isinstance(task_list, list)
                for task in task_list
                if isinstance(task, str)
            }
        )
        active_count = sum(1 for worker in workers if worker.status == "ok")
        return AdminWorkersResponse(
            status="healthy" if active_count > 0 else "unhealthy",
            active_worker_count=active_count,
            workers=workers,
            registered_tasks=registered_tasks,
            message=None if active_count > 0 else "No active Celery workers responded.",
        )

    async def get_queues(self) -> AdminQueuesResponse:
        document_queue = await self._document_queue_status()
        queues = [
            document_queue,
            AdminQueueStatus(
                kind="ocr",
                name="ocr",
                status="not_configured",
                configured=False,
                pending=None,
                consumer="documents.process_document",
                message="OCR is executed inside the document processing task.",
            ),
            AdminQueueStatus(
                kind="embedding",
                name="embedding",
                status="not_configured",
                configured=False,
                pending=None,
                consumer="documents.process_document",
                message="Embedding is executed inside the document processing task.",
            ),
            AdminQueueStatus(
                kind="retry",
                name="retry",
                status="not_configured",
                configured=False,
                pending=None,
                consumer="celery",
                message="No dedicated retry queue is configured.",
            ),
            AdminQueueStatus(
                kind="dead_letter",
                name="dead_letter",
                status="not_configured",
                configured=False,
                pending=None,
                consumer=None,
                message="No dead-letter queue is configured.",
            ),
        ]
        return AdminQueuesResponse(
            status="healthy" if document_queue.status == "ok" else "unhealthy",
            queues=queues,
        )

    async def get_statistics(self) -> AdminStatisticsResponse:
        document_by_status = await _group_counts(self.session, Document.status)
        user_by_role = await _group_counts(self.session, User.role)
        message_by_role = await _group_counts(self.session, ChatMessage.role)
        feedback_by_rating = await _group_counts(self.session, Feedback.rating)
        return AdminStatisticsResponse(
            documents=AdminDocumentStatistics(
                total=await _count_where(self.session, Document, Document.is_deleted.is_(False)),
                deleted=await _count_where(self.session, Document, Document.is_deleted.is_(True)),
                by_status=document_by_status,
            ),
            chunks=AdminCountStatistic(total=await _count_table(self.session, DocumentChunk)),
            embeddings=AdminCountStatistic(
                total=await _count_where(
                    self.session,
                    DocumentChunk,
                    DocumentChunk.embedding.is_not(None),
                )
            ),
            users=AdminUserStatistics(
                total=await _count_table(self.session, User),
                active=await _count_where(self.session, User, User.is_active.is_(True)),
                inactive=await _count_where(self.session, User, User.is_active.is_(False)),
                by_role=user_by_role,
            ),
            departments=AdminCountStatistic(total=await _count_table(self.session, Department)),
            chat_sessions=AdminSessionStatistics(
                total=await _count_table(self.session, ChatSession),
                archived=await _count_where(
                    self.session,
                    ChatSession,
                    ChatSession.is_archived.is_(True),
                ),
            ),
            messages=AdminMessageStatistics(
                total=await _count_table(self.session, ChatMessage),
                by_role=message_by_role,
            ),
            feedback=AdminFeedbackStatistics(
                total=await _count_table(self.session, Feedback),
                by_rating=feedback_by_rating,
            ),
            audit_logs=AdminCountStatistic(total=await _count_table(self.session, AuditLog)),
        )

    async def get_version(self) -> AdminVersionResponse:
        started_at = _application_started_at(self.application)
        return AdminVersionResponse(
            app_name=self.settings.app_name,
            version=_application_version(),
            environment=self.settings.app_env,
            python_version=platform.python_version(),
            api_prefix=self.settings.api_v1_prefix,
            migration_head=_migration_source_head(),
            database_revision=await self._database_revision(),
            started_at=started_at,
            uptime_seconds=_uptime_seconds(started_at),
        )

    def _api_health(self) -> AdminComponentCheck:
        started_at = _application_started_at(self.application)
        return AdminComponentCheck(
            name="api",
            status="ok",
            enabled=True,
            message="API process is running.",
            details={"uptime_seconds": _uptime_seconds(started_at)},
        )

    async def _postgres_health(self) -> AdminComponentCheck:
        try:
            result = await self.session.execute(text("SELECT 1"))
            ready = result.scalar_one() == 1
        except Exception:
            ready = False
        return AdminComponentCheck(
            name="postgres",
            status="ok" if ready else "unavailable",
            enabled=True,
            message="PostgreSQL is reachable." if ready else "PostgreSQL is unavailable.",
        )

    async def _redis_health(self) -> AdminComponentCheck:
        ready = await _redis_ping(
            self.settings.redis_url,
            settings=self.settings,
        )
        return AdminComponentCheck(
            name="redis",
            status="ok" if ready else "unavailable",
            enabled=True,
            message="Redis is reachable." if ready else "Redis is unavailable.",
        )

    async def _worker_health(self) -> AdminComponentCheck:
        try:
            ping = await _call_celery_inspect(_inspect_worker_ping)
        except Exception:
            ping = None
        active_count = len(_safe_mapping(ping))
        return AdminComponentCheck(
            name="worker",
            status="ok" if active_count > 0 else "unavailable",
            enabled=True,
            message=(
                "At least one Celery worker responded."
                if active_count > 0
                else "No Celery worker responded."
            ),
            details={"active_worker_count": active_count},
        )

    async def _ocr_health(self) -> AdminComponentCheck:
        if not self.settings.ocr_enabled:
            return AdminComponentCheck(
                name="ocr",
                status="disabled",
                enabled=False,
                message="OCR is disabled.",
            )
        try:
            result = await create_tesseract_ocr_provider(self.settings).health_check()
        except Exception:
            result = None
        available = bool(result and result.available)
        details: dict[str, str | int | float | bool | None | list[str]] = {
            "engine": result.engine if result is not None else "tesseract",
            "requested_languages": list(self.settings.ocr_languages),
        }
        if result is not None:
            details["version"] = result.version
            details["available_languages"] = list(result.languages)
        return AdminComponentCheck(
            name="ocr",
            status="ok" if available else "unavailable",
            enabled=True,
            message="OCR engine is available." if available else "OCR engine is unavailable.",
            details=details,
        )

    def _embedding_health(self) -> AdminComponentCheck:
        configured = (
            bool(self.settings.embedding_provider)
            and bool(self.settings.embedding_model_name)
            and self.settings.embedding_dimensions > 0
        )
        return AdminComponentCheck(
            name="embedding",
            status="ok" if configured else "misconfigured",
            enabled=True,
            message=(
                "Embedding provider configuration is valid."
                if configured
                else "Embedding provider configuration is invalid."
            ),
            details={
                "provider": self.settings.embedding_provider,
                "model": self.settings.embedding_model_name,
                "dimensions": self.settings.embedding_dimensions,
                "model_loading_checked": False,
            },
        )

    def _llm_health(self) -> AdminComponentCheck:
        health = self._llm_manager().configuration_health()
        return AdminComponentCheck(
            name="llm",
            status=_component_status_from_provider_health(health.status),
            enabled=self.settings.llm_enabled,
            message=health.message,
            details={
                "provider": health.provider,
                "display_name": health.display_name,
                "model": health.model,
                "connectivity_checked": health.connectivity_checked,
            },
        )

    def _web_search_health(self) -> AdminComponentCheck:
        health = self._web_search_manager().configuration_health()
        return AdminComponentCheck(
            name="web_search",
            status=_component_status_from_provider_health(health.status),
            enabled=self.settings.web_search_enabled,
            message=health.message,
            details={
                "provider": health.provider,
                "display_name": health.display_name,
                "external_allowed": health.external_allowed,
                "connectivity_checked": health.connectivity_checked,
            },
        )

    def _streaming_health(self) -> AdminComponentCheck:
        route_registered = _route_registered(
            self.application,
            f"{self.settings.api_v1_prefix}/chat/sessions/{{session_id}}/messages/stream",
        )
        status: ComponentStatus = "ok" if route_registered else "misconfigured"
        return AdminComponentCheck(
            name="streaming",
            status=status,
            enabled=True,
            message=(
                "Streaming subsystem is registered."
                if route_registered
                else "Streaming route is not registered."
            ),
            details={
                "strategy": "buffer_after_validation",
                "heartbeat_seconds": self.settings.llm_stream_heartbeat_seconds,
                "max_duration_seconds": self.settings.llm_stream_max_duration_seconds,
            },
        )

    def _conversation_health(self) -> AdminComponentCheck:
        enabled = (
            self.settings.chat_history_max_messages > 0
            and self.settings.chat_history_max_tokens > 0
        )
        return AdminComponentCheck(
            name="conversation",
            status="ok" if enabled else "disabled",
            enabled=enabled,
            message=(
                "Conversation memory is enabled."
                if enabled
                else "Conversation memory is disabled by configuration."
            ),
            details={
                "max_messages": self.settings.chat_history_max_messages,
                "max_tokens": self.settings.chat_history_max_tokens,
            },
        )

    async def _document_queue_status(self) -> AdminQueueStatus:
        queue_name = self.settings.celery_document_queue
        pending = await _redis_llen(
            self.settings.celery_broker_url,
            queue_name,
            settings=self.settings,
        )
        return AdminQueueStatus(
            kind="document",
            name=queue_name,
            status="ok" if pending is not None else "unavailable",
            configured=True,
            pending=pending,
            consumer="documents.process_document",
            message=(
                "Document queue is reachable."
                if pending is not None
                else "Document queue is unavailable."
            ),
        )

    async def _database_revision(self) -> str | None:
        try:
            value = await self.session.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception:
            return None
        return str(value) if value else None

    def _llm_manager(self) -> LLMProviderManager:
        manager = getattr(getattr(self.application, "state", None), "llm_provider_manager", None)
        if isinstance(manager, LLMProviderManager):
            return manager
        return LLMProviderManager(self.settings)

    def _web_search_manager(self) -> WebSearchProviderManager:
        manager = getattr(
            getattr(self.application, "state", None),
            "web_search_provider_manager",
            None,
        )
        if isinstance(manager, WebSearchProviderManager):
            return manager
        return WebSearchProviderManager(self.settings)


async def _count_table(session: AsyncSession, model: type) -> int:
    statement = select(func.count()).select_from(model)
    return int(await session.scalar(statement) or 0)


async def _count_where(session: AsyncSession, model: type, condition: Any) -> int:
    statement = select(func.count()).select_from(model).where(condition)
    return int(await session.scalar(statement) or 0)


async def _group_counts(session: AsyncSession, column: Any) -> dict[str, int]:
    statement = select(column, func.count()).group_by(column)
    rows = await session.execute(statement)
    return {_safe_key(key): int(count or 0) for key, count in rows}


def _safe_key(value: Any) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


async def _redis_ping(url: str, *, settings: Settings) -> bool:
    client = _redis_client(url, settings=settings)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


async def _redis_llen(url: str, queue_name: str, *, settings: Settings) -> int | None:
    client = _redis_client(url, settings=settings)
    try:
        return int(await client.llen(queue_name))
    except Exception:
        return None
    finally:
        await client.aclose()


def _redis_client(url: str, *, settings: Settings) -> Redis:
    return Redis.from_url(
        url,
        socket_connect_timeout=settings.redis_connect_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
        health_check_interval=settings.redis_health_check_interval_seconds,
    )


async def _call_celery_inspect(function: Any) -> Any:
    return await asyncio.wait_for(
        asyncio.to_thread(function),
        timeout=CELERY_INSPECT_OUTER_TIMEOUT_SECONDS,
    )


def _inspect_worker_ping() -> dict[str, object] | None:
    inspector = celery_app.control.inspect(timeout=CELERY_INSPECT_TIMEOUT_SECONDS)
    return inspector.ping()


def _inspect_worker_snapshot() -> dict[str, object | None]:
    inspector = celery_app.control.inspect(timeout=CELERY_INSPECT_TIMEOUT_SECONDS)
    return {
        "ping": inspector.ping(),
        "stats": inspector.stats(),
        "registered": inspector.registered(),
        "active_queues": inspector.active_queues(),
    }


def _safe_mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _queue_names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name:
                names.append(name)
    return sorted(dict.fromkeys(names))


def _pool_name(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    pool = value.get("pool")
    if not isinstance(pool, dict):
        return None
    implementation = pool.get("implementation")
    return implementation if isinstance(implementation, str) and implementation else None


def _overall_health_status(checks: list[AdminComponentCheck]) -> OverallStatus:
    critical = {"api", "postgres", "redis", "worker"}
    critical_failure = any(
        check.name in critical and check.status in {"unavailable", "misconfigured"}
        for check in checks
    )
    if critical_failure:
        return "unhealthy"
    optional_failure = any(
        check.status in {"degraded", "unavailable", "misconfigured"} for check in checks
    )
    return "degraded" if optional_failure else "healthy"


def _component_status_from_provider_health(status: str) -> ComponentStatus:
    if status == "disabled":
        return "disabled"
    if status in {"configured", "reachable"}:
        return "ok"
    if status == "misconfigured":
        return "misconfigured"
    if status in {"unreachable", "blocked"}:
        return "unavailable"
    return "degraded"


def _provider_status_from_health(status: str) -> ProviderStatus:
    if status == "disabled":
        return "disabled"
    if status in {"configured", "reachable"}:
        return "healthy"
    if status == "misconfigured":
        return "misconfigured"
    return "unhealthy"


def _llm_provider_status(health: ProviderHealth, *, enabled: bool) -> AdminProviderStatus:
    return AdminProviderStatus(
        provider_type="llm",
        provider=health.provider,
        status=_provider_status_from_health(health.status),
        enabled=enabled,
        configured=health.configured,
        display_name=health.display_name,
        model=health.model,
        external_allowed=None,
        connectivity_checked=health.connectivity_checked,
        message=health.message,
    )


def _web_search_provider_status(
    health: WebSearchProviderHealth,
    *,
    enabled: bool,
) -> AdminProviderStatus:
    return AdminProviderStatus(
        provider_type="web_search",
        provider=health.provider,
        status=_provider_status_from_health(health.status),
        enabled=enabled,
        configured=health.configured,
        display_name=health.display_name,
        model=None,
        external_allowed=health.external_allowed,
        connectivity_checked=health.connectivity_checked,
        message=health.message,
    )


def _application_version() -> str:
    try:
        return package_version("enterprise-ai-knowledge-assistant")
    except PackageNotFoundError:
        return APPLICATION_VERSION_FALLBACK


def _migration_source_head() -> str | None:
    try:
        repo_root = Path(__file__).resolve().parents[2]
        config = Config(str(repo_root / "alembic.ini"))
        config.set_main_option("script_location", str(repo_root / "app" / "db" / "migrations"))
        return ScriptDirectory.from_config(config).get_current_head()
    except Exception:
        return None


def _settings_from_application(application: Any | None) -> Settings | None:
    manager = getattr(getattr(application, "state", None), "llm_provider_manager", None)
    settings = getattr(manager, "settings", None)
    return settings if isinstance(settings, Settings) else None


def _application_started_at(application: Any | None) -> datetime | None:
    started_at = getattr(getattr(application, "state", None), "started_at", None)
    return started_at if isinstance(started_at, datetime) else None


def _uptime_seconds(started_at: datetime | None) -> int:
    if started_at is None:
        return 0
    return max(0, int((_utc_now() - started_at).total_seconds()))


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _route_registered(application: Any | None, path: str) -> bool:
    routes = getattr(getattr(application, "router", None), "routes", ())
    return path in set(_iter_route_paths(routes))


def _iter_route_paths(routes: object, *, prefix: str = "") -> list[str]:
    paths: list[str] = []
    for route in routes or ():
        route_path = getattr(route, "path", None)
        if isinstance(route_path, str) and route_path:
            paths.append(f"{prefix}{route_path}")
        original_router = getattr(route, "original_router", None)
        include_context = getattr(route, "include_context", None)
        included_routes = getattr(original_router, "routes", None)
        included_prefix = getattr(include_context, "prefix", "")
        if included_routes is not None:
            paths.extend(_iter_route_paths(included_routes, prefix=f"{prefix}{included_prefix}"))
    return paths
