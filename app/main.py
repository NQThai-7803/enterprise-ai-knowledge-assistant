from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes.health import router as health_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.departments import router as departments_router
from app.api.v1.documents import router as documents_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.users import router as users_router
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ApplicationError,
    application_error_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)
from app.core.logging import configure_logging_redaction
from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.db.session import dispose_database_engine
from app.llm.manager import LLMProviderManager


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        llm_provider_manager = getattr(application.state, "llm_provider_manager", None)
        if llm_provider_manager is not None:
            await llm_provider_manager.aclose()
        await dispose_database_engine()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging_redaction()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    )
    application.state.llm_provider_manager = LLMProviderManager(settings)
    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_bytes=settings.max_request_body_bytes,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allowed_methods,
        allow_headers=settings.cors_allowed_headers,
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    application.add_middleware(SecurityHeadersMiddleware, settings=settings)
    application.add_exception_handler(ApplicationError, application_error_handler)
    application.add_exception_handler(RequestValidationError, request_validation_error_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
    application.include_router(health_router)
    application.include_router(auth_router, prefix=settings.api_v1_prefix)
    application.include_router(audit_logs_router, prefix=settings.api_v1_prefix)
    application.include_router(chat_router, prefix=settings.api_v1_prefix)
    application.include_router(users_router, prefix=settings.api_v1_prefix)
    application.include_router(departments_router, prefix=settings.api_v1_prefix)
    application.include_router(documents_router, prefix=settings.api_v1_prefix)
    application.include_router(feedback_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
