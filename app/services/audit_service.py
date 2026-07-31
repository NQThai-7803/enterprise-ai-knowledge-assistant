from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from numbers import Integral
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEvent, AuditEventType, AuditOutcome, AuditTargetType
from app.audit.metadata import AuditMetadataError, AuditScalar, sanitize_audit_metadata
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuditDateRangeInvalidError,
    AuditEventInvalidError,
    AuditFilterInvalidError,
    AuditMetadataInvalidError,
    AuditReportForbiddenError,
)
from app.models import AuditLog, User, UserRole
from app.repositories import audit_log_repository
from app.repositories.audit_log_repository import AuditReportFilters
from app.schemas.common import calculate_offset, calculate_total_pages

MAX_USER_AGENT_LENGTH = 512
MAX_REQUEST_ID_LENGTH = 128
_ERROR_CODE_PATTERN = re.compile(r"^[A-Z0-9_]+$")

AuditAction = AuditEventType

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuditContext:
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class AuditPaginationMeta:
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class AuditReportData:
    rows: tuple[AuditLog, ...]
    pagination: AuditPaginationMeta


class AuditService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        repository=audit_log_repository,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository

    async def record_success(
        self,
        *,
        event_type: AuditEventType | str,
        actor_user_id: UUID | None,
        target_type: AuditTargetType | str | None = None,
        target_id: UUID | str | None = None,
        context: AuditContext | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AuditLog:
        event = self._build_event(
            event_type=event_type,
            outcome=AuditOutcome.SUCCESS,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            context=context,
            error_code=None,
            metadata=metadata,
        )
        return await self.repository.create(
            self.session,
            event=event,
            ip_address=context.ip_address if context is not None else None,
            user_agent=_limit_user_agent(context.user_agent) if context is not None else None,
        )

    async def record_failure(
        self,
        *,
        event_type: AuditEventType | str,
        actor_user_id: UUID | None,
        error_code: str | None,
        target_type: AuditTargetType | str | None = None,
        target_id: UUID | str | None = None,
        context: AuditContext | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AuditLog:
        event = self._build_event(
            event_type=event_type,
            outcome=AuditOutcome.FAILURE,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            context=context,
            error_code=_sanitize_error_code(
                error_code,
                max_length=self.settings.audit_error_code_max_length,
            ),
            metadata=metadata,
        )
        return await self.repository.create(
            self.session,
            event=event,
            ip_address=context.ip_address if context is not None else None,
            user_agent=_limit_user_agent(context.user_agent) if context is not None else None,
        )

    async def record_failure_best_effort(
        self,
        *,
        event_type: AuditEventType | str,
        actor_user_id: UUID | None,
        error_code: str | None,
        target_type: AuditTargetType | str | None = None,
        target_id: UUID | str | None = None,
        context: AuditContext | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        try:
            if self.session.in_transaction():
                await self.session.rollback()
            await self.record_failure(
                event_type=event_type,
                actor_user_id=actor_user_id,
                error_code=error_code,
                target_type=target_type,
                target_id=target_id,
                context=context,
                metadata=metadata,
            )
            await self.session.commit()
        except Exception:  # noqa: BLE001 - best-effort audit must preserve the original error.
            await self.session.rollback()
            logger.warning("Audit failure event could not be persisted")

    async def list_audit_report(
        self,
        *,
        current_user: User,
        page: int,
        page_size: int | None,
        event_type: AuditEventType | None = None,
        outcome: AuditOutcome | None = None,
        actor_user_id: UUID | None = None,
        target_type: AuditTargetType | None = None,
        target_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        request_id: str | None = None,
        error_code: str | None = None,
    ) -> AuditReportData:
        if current_user.role != UserRole.ADMIN:
            raise AuditReportForbiddenError()
        resolved_page = _validate_page(page)
        resolved_page_size = _resolve_page_size(
            page_size,
            default=self.settings.audit_report_page_size,
            maximum=self.settings.audit_report_max_page_size,
        )
        validate_audit_date_range(date_from=date_from, date_to=date_to)
        filters = AuditReportFilters(
            event_type=event_type,
            outcome=outcome,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            date_from=date_from,
            date_to=date_to,
            request_id=_validate_filter_string(request_id, max_length=MAX_REQUEST_ID_LENGTH),
            error_code=_validate_filter_string(
                error_code,
                max_length=self.settings.audit_error_code_max_length,
            ),
        )
        total = await self.repository.count_report(self.session, filters=filters)
        rows = await self.repository.list_report(
            self.session,
            filters=filters,
            limit=resolved_page_size,
            offset=calculate_offset(resolved_page, resolved_page_size),
        )
        return AuditReportData(
            rows=rows,
            pagination=AuditPaginationMeta(
                page=resolved_page,
                page_size=resolved_page_size,
                total=total,
                total_pages=calculate_total_pages(total, resolved_page_size),
            ),
        )

    async def create_audit_log(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str | None,
        entity_id: UUID | None,
        context: AuditContext | None,
        metadata: dict[str, object] | None,
    ) -> AuditLog:
        return await self.record_success(
            event_type=action,
            actor_user_id=actor_user_id,
            target_type=entity_type,
            target_id=entity_id,
            context=context,
            metadata=metadata,
        )

    def _build_event(
        self,
        *,
        event_type: AuditEventType | str,
        outcome: AuditOutcome,
        actor_user_id: UUID | None,
        target_type: AuditTargetType | str | None,
        target_id: UUID | str | None,
        context: AuditContext | None,
        error_code: str | None,
        metadata: dict[str, object] | None,
    ) -> AuditEvent:
        return AuditEvent(
            event_type=_coerce_event_type(event_type),
            outcome=outcome,
            actor_user_id=actor_user_id,
            target_type=_coerce_target_type(
                target_type,
                max_length=self.settings.audit_target_type_max_length,
            ),
            target_id=_coerce_target_id(target_id),
            request_id=_coerce_request_id(context.request_id if context is not None else None),
            error_code=error_code,
            metadata=_sanitize_metadata(
                metadata,
                max_length=self.settings.audit_metadata_max_length,
            ),
        )


def validate_audit_date_range(
    *,
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    for value in (date_from, date_to):
        if value is not None and (value.tzinfo is None or value.tzinfo.utcoffset(value) is None):
            raise AuditDateRangeInvalidError()
    if date_from is not None and date_to is not None and date_from > date_to:
        raise AuditDateRangeInvalidError()


def _coerce_event_type(event_type: AuditEventType | str) -> AuditEventType:
    try:
        return event_type if isinstance(event_type, AuditEventType) else AuditEventType(event_type)
    except ValueError as exc:
        raise AuditEventInvalidError() from exc


def _coerce_target_type(
    target_type: AuditTargetType | str | None,
    *,
    max_length: int,
) -> AuditTargetType | None:
    if target_type is None:
        return None
    try:
        if isinstance(target_type, AuditTargetType):
            coerced = target_type
        else:
            normalized = target_type.strip().upper()
            legacy_target_types = {
                "CHATMESSAGE": AuditTargetType.CHAT_MESSAGE,
                "CHATSESSION": AuditTargetType.CHAT_SESSION,
                "DEPARTMENT": AuditTargetType.DEPARTMENT,
                "DOCUMENT": AuditTargetType.DOCUMENT,
                "DOCUMENTPERMISSION": AuditTargetType.DOCUMENT_PERMISSION,
                "FEEDBACK": AuditTargetType.FEEDBACK,
                "USER": AuditTargetType.USER,
            }
            coerced = legacy_target_types.get(normalized.replace("_", ""))
            if coerced is None:
                coerced = AuditTargetType(normalized)
    except ValueError as exc:
        raise AuditEventInvalidError() from exc
    if len(coerced.value) > max_length:
        raise AuditEventInvalidError()
    return coerced


def _coerce_target_id(target_id: UUID | str | None) -> str | None:
    if target_id is None:
        return None
    try:
        return str(target_id if isinstance(target_id, UUID) else UUID(str(target_id)))
    except ValueError as exc:
        raise AuditEventInvalidError() from exc


def _coerce_request_id(request_id: str | None) -> str | None:
    if request_id is None:
        return None
    normalized = request_id.strip()
    if not normalized:
        return None
    return normalized[:MAX_REQUEST_ID_LENGTH]


def _sanitize_metadata(
    metadata: dict[str, object] | None,
    *,
    max_length: int,
) -> dict[str, AuditScalar]:
    try:
        return dict(sanitize_audit_metadata(metadata, max_length=max_length))
    except AuditMetadataError as exc:
        raise AuditMetadataInvalidError() from exc


def _sanitize_error_code(error_code: str | None, *, max_length: int) -> str:
    if error_code is None:
        return "INTERNAL_ERROR"
    normalized = error_code.strip().upper()
    if not normalized or len(normalized) > max_length:
        return "INTERNAL_ERROR"
    if _ERROR_CODE_PATTERN.fullmatch(normalized) is None:
        return "INTERNAL_ERROR"
    return normalized


def _limit_user_agent(user_agent: str | None) -> str | None:
    if user_agent is None:
        return None
    return user_agent[:MAX_USER_AGENT_LENGTH]


def _validate_page(page: int) -> int:
    if isinstance(page, bool) or not isinstance(page, Integral):
        raise AuditFilterInvalidError()
    resolved_page = int(page)
    if resolved_page < 1:
        raise AuditFilterInvalidError()
    return resolved_page


def _resolve_page_size(value: int | None, *, default: int, maximum: int) -> int:
    page_size = default if value is None else value
    if isinstance(page_size, bool) or not isinstance(page_size, Integral):
        raise AuditFilterInvalidError()
    resolved_page_size = int(page_size)
    if resolved_page_size < 1 or resolved_page_size > maximum:
        raise AuditFilterInvalidError()
    return resolved_page_size


def _validate_filter_string(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise AuditFilterInvalidError()
    return normalized
