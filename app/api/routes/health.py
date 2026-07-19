from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.session import check_database_connection

router = APIRouter(prefix="/health", tags=["health"])


class HealthLiveResponse(BaseModel):
    status: str
    app_name: str
    environment: str


class HealthReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/live", response_model=HealthLiveResponse)
async def live() -> HealthLiveResponse:
    settings = get_settings()
    return HealthLiveResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
    )


@router.get(
    "/ready",
    response_model=HealthReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthReadyResponse}},
)
async def ready() -> HealthReadyResponse | JSONResponse:
    if await check_database_connection():
        return HealthReadyResponse(status="ready", checks={"database": "ok"})

    response = HealthReadyResponse(
        status="not_ready",
        checks={"database": "unavailable"},
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )
