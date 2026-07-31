from __future__ import annotations

from collections.abc import Callable
from ipaddress import ip_address
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AccessTokenInvalidError, PermissionDeniedError
from app.core.rate_limit import (
    anonymous_identity,
    chat_rule,
    enforce_rate_limit,
    feedback_rule,
    login_rule,
    refresh_rule,
    upload_rule,
    user_identity,
)
from app.core.security import decode_access_token
from app.db.session import async_session_factory, get_db_session
from app.document_processing.tokenization import TiktokenTokenCounter
from app.models import User, UserRole
from app.retrieval.factory import create_hybrid_retrieval_service
from app.services.audit_service import MAX_USER_AGENT_LENGTH, AuditContext
from app.services.auth_service import AuthService
from app.services.document_service import DocumentUploadLimits, EnqueueDocumentProcessing
from app.services.grounded_answer_service import GroundedAnswerService
from app.workers.document_tasks import try_enqueue_document_processing

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AccessTokenInvalidError()

    payload = decode_access_token(credentials.credentials)
    auth_service = AuthService(session)
    return await auth_service.get_active_user(payload.user_id)


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    if not allowed_roles:
        msg = "At least one role must be allowed."
        raise ValueError(msg)

    allowed_role_set = frozenset(allowed_roles)

    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_role_set:
            raise PermissionDeniedError()
        return current_user

    return role_dependency


async def enforce_login_rate_limit(request: Request) -> None:
    await enforce_rate_limit(
        request,
        rule=login_rule(),
        identity=anonymous_identity(request),
    )


async def enforce_refresh_rate_limit(request: Request) -> None:
    await enforce_rate_limit(
        request,
        rule=refresh_rule(),
        identity=anonymous_identity(request),
    )


async def enforce_upload_rate_limit(request: Request, current_user: User) -> None:
    await enforce_rate_limit(
        request,
        rule=upload_rule(),
        identity=user_identity(current_user.id),
    )


async def enforce_chat_rate_limit(request: Request, current_user: User) -> None:
    await enforce_rate_limit(
        request,
        rule=chat_rule(),
        identity=user_identity(current_user.id),
    )


async def enforce_feedback_rate_limit(request: Request, current_user: User) -> None:
    await enforce_rate_limit(
        request,
        rule=feedback_rule(),
        identity=user_identity(current_user.id),
    )


def get_audit_context(request: Request) -> AuditContext:
    user_agent = request.headers.get("user-agent")
    if user_agent is not None:
        user_agent = user_agent[:MAX_USER_AGENT_LENGTH]
    client_host = request.client.host if request.client is not None else None
    if client_host is not None:
        try:
            ip_address(client_host)
        except ValueError:
            client_host = None
    return AuditContext(ip_address=client_host, user_agent=user_agent)


def get_document_upload_limits() -> DocumentUploadLimits:
    settings = get_settings()
    return DocumentUploadLimits(
        max_upload_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        upload_chunk_size_bytes=settings.upload_chunk_size_bytes,
    )


def get_document_processing_enqueue() -> EnqueueDocumentProcessing:
    return try_enqueue_document_processing


def get_grounded_answer_service(request: Request) -> GroundedAnswerService:
    settings = get_settings()
    llm_provider_manager = request.app.state.llm_provider_manager
    return GroundedAnswerService(
        settings=settings,
        session_provider=async_session_factory,
        hybrid_retrieval_service=create_hybrid_retrieval_service(settings),
        llm_provider_factory=llm_provider_manager.get_provider,
        close_llm_provider_after_generate=False,
        token_counter=TiktokenTokenCounter(settings.tokenizer_encoding_name),
    )


require_admin = require_roles(UserRole.ADMIN)
require_manager_or_admin = require_roles(UserRole.ADMIN, UserRole.MANAGER)
require_authenticated_user = get_current_user
