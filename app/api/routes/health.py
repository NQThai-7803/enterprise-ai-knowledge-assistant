from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis

from app.core.config import get_settings
from app.db.session import check_database_connection

router = APIRouter(prefix="/health", tags=["health"])


class HealthLiveResponse(BaseModel):
    status: str


class HealthReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/live", response_model=HealthLiveResponse)
async def live() -> HealthLiveResponse:
    return HealthLiveResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthReadyResponse}},
)
async def ready() -> HealthReadyResponse | JSONResponse:
    database_ready = await check_database_connection()
    redis_ready = await check_redis_connection()
    checks = {
        "database": "ok" if database_ready else "unavailable",
        "redis": "ok" if redis_ready else "unavailable",
    }

    if database_ready and redis_ready:
        return HealthReadyResponse(status="ready", checks=checks)

    response = HealthReadyResponse(
        status="not_ready",
        checks=checks,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )


async def check_redis_connection() -> bool:
    settings = get_settings()
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.redis_connect_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
        health_check_interval=settings.redis_health_check_interval_seconds,
    )
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()
