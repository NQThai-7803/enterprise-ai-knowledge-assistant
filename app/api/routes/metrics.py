from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.services.metrics_service import PROMETHEUS_CONTENT_TYPE, PrometheusMetricsService

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def metrics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    settings = _settings_from_application(request) or get_settings()
    if not settings.metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    body = await PrometheusMetricsService(
        session=session,
        application=request.app,
        settings=settings,
    ).render()
    return Response(content=body, media_type=PROMETHEUS_CONTENT_TYPE)


def _settings_from_application(request: Request) -> Settings | None:
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else None
