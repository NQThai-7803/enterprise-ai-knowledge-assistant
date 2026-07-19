from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.routes.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.departments import router as departments_router
from app.api.v1.documents import router as documents_router
from app.api.v1.users import router as users_router
from app.core.config import get_settings
from app.core.exceptions import (
    ApplicationError,
    application_error_handler,
    request_validation_error_handler,
)
from app.db.session import dispose_database_engine


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_database_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    application.add_exception_handler(ApplicationError, application_error_handler)
    application.add_exception_handler(RequestValidationError, request_validation_error_handler)
    application.include_router(health_router)
    application.include_router(auth_router, prefix=settings.api_v1_prefix)
    application.include_router(users_router, prefix=settings.api_v1_prefix)
    application.include_router(departments_router, prefix=settings.api_v1_prefix)
    application.include_router(documents_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
