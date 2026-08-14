from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.db.session import get_db_session
from app.models import User
from app.schemas.admin_monitoring import (
    AdminHealthResponse,
    AdminProvidersResponse,
    AdminQueuesResponse,
    AdminStatisticsResponse,
    AdminSystemResponse,
    AdminVersionResponse,
    AdminWorkersResponse,
)
from app.schemas.common import DataResponse
from app.services.admin_monitoring_service import AdminMonitoringService

router = APIRouter(prefix="/admin", tags=["Admin Monitoring"])


@router.get("/system", response_model=DataResponse[AdminSystemResponse])
async def get_admin_system(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[AdminSystemResponse]:
    _ = current_user
    return DataResponse[AdminSystemResponse](
        data=await AdminMonitoringService(session=session, application=request.app).get_system(),
        meta=None,
    )


@router.get("/health", response_model=DataResponse[AdminHealthResponse])
async def get_admin_health(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[AdminHealthResponse]:
    _ = current_user
    return DataResponse[AdminHealthResponse](
        data=await AdminMonitoringService(session=session, application=request.app).get_health(),
        meta=None,
    )


@router.get("/providers", response_model=DataResponse[AdminProvidersResponse])
async def get_admin_providers(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[AdminProvidersResponse]:
    _ = current_user
    return DataResponse[AdminProvidersResponse](
        data=AdminMonitoringService(session=session, application=request.app).get_providers(),
        meta=None,
    )


@router.get("/workers", response_model=DataResponse[AdminWorkersResponse])
async def get_admin_workers(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[AdminWorkersResponse]:
    _ = current_user
    return DataResponse[AdminWorkersResponse](
        data=await AdminMonitoringService(session=session, application=request.app).get_workers(),
        meta=None,
    )


@router.get("/statistics", response_model=DataResponse[AdminStatisticsResponse])
async def get_admin_statistics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[AdminStatisticsResponse]:
    _ = current_user
    return DataResponse[AdminStatisticsResponse](
        data=await AdminMonitoringService(
            session=session,
            application=request.app,
        ).get_statistics(),
        meta=None,
    )


@router.get("/queues", response_model=DataResponse[AdminQueuesResponse])
async def get_admin_queues(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[AdminQueuesResponse]:
    _ = current_user
    return DataResponse[AdminQueuesResponse](
        data=await AdminMonitoringService(session=session, application=request.app).get_queues(),
        meta=None,
    )


@router.get("/version", response_model=DataResponse[AdminVersionResponse])
async def get_admin_version(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[AdminVersionResponse]:
    _ = current_user
    return DataResponse[AdminVersionResponse](
        data=await AdminMonitoringService(session=session, application=request.app).get_version(),
        meta=None,
    )
