from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEventType, AuditTargetType
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ApplicationError,
    BusinessValidationError,
    ChatSessionNotFoundError,
    ChatSessionTitleTooLongError,
    InternalServerError,
)
from app.models import User
from app.repositories import (
    chat_message_repository,
    chat_session_repository,
    message_citation_repository,
)
from app.repositories.chat_message_repository import VisibleChatMessageRow
from app.repositories.chat_session_repository import ChatSessionListRow
from app.schemas.chat import ChatSessionCreate
from app.schemas.common import PaginationMeta, build_pagination_meta, calculate_offset
from app.services.audit_service import AuditContext, AuditService


@dataclass(frozen=True, slots=True)
class ChatSessionDetailData:
    chat_session: object
    messages: tuple[VisibleChatMessageRow, ...]
    citations_by_message_id: dict[UUID, tuple[object, ...]]
    message_pagination: PaginationMeta


class ChatSessionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        session_repository=chat_session_repository,
        message_repository=chat_message_repository,
        citation_repository=message_citation_repository,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.session_repository = session_repository
        self.message_repository = message_repository
        self.citation_repository = citation_repository

    async def create_session(
        self,
        *,
        payload: ChatSessionCreate,
        current_user: User,
        audit_context: AuditContext | None = None,
    ):
        normalized_title = normalize_chat_session_title(
            payload.title,
            max_characters=self.settings.chat_session_title_max_characters,
        )
        try:
            chat_session = await self.session_repository.create(
                self.session,
                user_id=current_user.id,
                title=normalized_title,
            )
            await self.session.flush()
            await AuditService(self.session, settings=self.settings).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.CHAT_SESSION_CREATED,
                target_type=AuditTargetType.CHAT_SESSION,
                target_id=chat_session.id,
                context=audit_context,
                metadata={},
            )
            await self.session.commit()
            await self.session.refresh(chat_session)
        except ApplicationError:
            await self.session.rollback()
            raise
        except IntegrityError as exc:
            await self.session.rollback()
            raise InternalServerError() from exc
        except Exception as exc:
            await self.session.rollback()
            raise InternalServerError() from exc
        return chat_session

    async def list_sessions(
        self,
        *,
        current_user: User,
        page: int,
        page_size: int | None = None,
        include_archived: bool = False,
    ) -> tuple[tuple[ChatSessionListRow, ...], PaginationMeta]:
        resolved_page = validate_page(page)
        resolved_page_size = resolve_page_size(
            page_size,
            default=self.settings.chat_session_list_page_size,
            maximum=self.settings.chat_session_list_max_page_size,
        )
        total = await self.session_repository.count_owned(
            self.session,
            owner_user_id=current_user.id,
            include_archived=include_archived,
        )
        rows = await self.session_repository.list_owned(
            self.session,
            owner_user_id=current_user.id,
            limit=resolved_page_size,
            offset=calculate_offset(resolved_page, resolved_page_size),
            include_archived=include_archived,
        )
        return rows, build_pagination_meta(
            page=resolved_page,
            page_size=resolved_page_size,
            total=total,
        )

    async def get_session_detail(
        self,
        *,
        session_id: UUID,
        current_user: User,
        message_page: int,
        message_page_size: int | None = None,
    ) -> ChatSessionDetailData:
        resolved_message_page = validate_page(message_page)
        resolved_message_page_size = resolve_page_size(
            message_page_size,
            default=self.settings.chat_history_page_size,
            maximum=self.settings.chat_history_max_page_size,
        )
        chat_session = await self.session_repository.get_owned_by_id(
            self.session,
            session_id=session_id,
            owner_user_id=current_user.id,
        )
        if chat_session is None:
            raise ChatSessionNotFoundError()

        total = await self.message_repository.count_visible_by_session(
            self.session,
            session_id=chat_session.id,
        )
        messages = await self.message_repository.list_visible_by_session(
            self.session,
            session_id=chat_session.id,
            limit=resolved_message_page_size,
            offset=calculate_offset(resolved_message_page, resolved_message_page_size),
        )
        citation_rows = await self.citation_repository.list_by_message_ids(
            self.session,
            message_ids=tuple(message.id for message in messages),
            current_user=current_user,
        )
        citations_by_message_id: dict[UUID, list[object]] = {}
        for citation in citation_rows:
            citations_by_message_id.setdefault(citation.message_id, []).append(citation)
        return ChatSessionDetailData(
            chat_session=chat_session,
            messages=messages,
            citations_by_message_id={
                message_id: tuple(citations)
                for message_id, citations in citations_by_message_id.items()
            },
            message_pagination=build_pagination_meta(
                page=resolved_message_page,
                page_size=resolved_message_page_size,
                total=total,
            ),
        )

    async def delete_session(
        self,
        *,
        session_id: UUID,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> None:
        try:
            chat_session = await self.session_repository.get_owned_by_id_for_update(
                self.session,
                session_id=session_id,
                owner_user_id=current_user.id,
            )

            if chat_session is None:
                raise ChatSessionNotFoundError()

            deleted_session_id = chat_session.id

            await self.session_repository.delete(
                self.session,
                chat_session=chat_session,
            )

            await self.session.flush()

            await AuditService(
                self.session,
                settings=self.settings,
            ).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.CHAT_SESSION_DELETED,
                target_type=AuditTargetType.CHAT_SESSION,
                target_id=deleted_session_id,
                context=audit_context,
                metadata={},
            )

            await self.session.commit()

        except ApplicationError:
            await self.session.rollback()
            raise
        except IntegrityError as exc:
            await self.session.rollback()
            raise InternalServerError() from exc
        except Exception as exc:
            await self.session.rollback()
            raise InternalServerError() from exc


def normalize_chat_session_title(title: str | None, *, max_characters: int) -> str | None:
    if title is None:
        return None
    normalized = title.strip()
    if not normalized:
        return None
    if len(normalized) > max_characters:
        raise ChatSessionTitleTooLongError()
    return normalized


def validate_page(page: int) -> int:
    if isinstance(page, bool) or not isinstance(page, Integral):
        raise BusinessValidationError("Pagination parameters are invalid.")
    resolved_page = int(page)
    if resolved_page < 1:
        raise BusinessValidationError("Pagination parameters are invalid.")
    return resolved_page


def resolve_page_size(value: int | None, *, default: int, maximum: int) -> int:
    page_size = default if value is None else value
    if isinstance(page_size, bool) or not isinstance(page_size, Integral):
        raise BusinessValidationError("Pagination parameters are invalid.")
    resolved_page_size = int(page_size)
    if resolved_page_size < 1 or resolved_page_size > maximum:
        raise BusinessValidationError("Pagination parameters are invalid.")
    return resolved_page_size
