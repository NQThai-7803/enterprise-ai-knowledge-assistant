from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.core.exceptions import BusinessValidationError
from app.db.session import get_db_session
from app.models import User
from app.schemas.admin_analytics import (
    AdminAnalyticsOverviewResponse,
    AdminAuditAnalyticsResponse,
    AdminChatAnalyticsResponse,
    AdminFeedbackAnalyticsResponse,
    AdminLLMAnalyticsResponse,
    AdminOCRAnalyticsResponse,
    AdminSearchAnalyticsResponse,
    AdminUserAnalyticsResponse,
    AnalyticsExportFormat,
    AnalyticsPeriod,
    AnalyticsReportKind,
)
from app.schemas.common import DataResponse
from app.services.admin_analytics_service import (
    AdminAnalyticsService,
    analytics_payload_to_csv,
    build_export_payload,
    resolve_analytics_window,
)

router = APIRouter(prefix="/admin", tags=["Admin Analytics"])


@router.get("/analytics/overview", response_model=DataResponse[AdminAnalyticsOverviewResponse])
async def get_admin_analytics_overview(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminAnalyticsOverviewResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminAnalyticsOverviewResponse](
        data=await AdminAnalyticsService(
            session=session,
            application=request.app,
        ).get_overview(window),
        meta=None,
    )


@router.get("/analytics/chat", response_model=DataResponse[AdminChatAnalyticsResponse])
async def get_admin_chat_analytics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminChatAnalyticsResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminChatAnalyticsResponse](
        data=await AdminAnalyticsService(session=session, application=request.app).get_chat(window),
        meta=None,
    )


@router.get("/analytics/users", response_model=DataResponse[AdminUserAnalyticsResponse])
async def get_admin_user_analytics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminUserAnalyticsResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminUserAnalyticsResponse](
        data=await AdminAnalyticsService(session=session, application=request.app).get_users(
            window
        ),
        meta=None,
    )


@router.get("/analytics/search", response_model=DataResponse[AdminSearchAnalyticsResponse])
async def get_admin_search_analytics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminSearchAnalyticsResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminSearchAnalyticsResponse](
        data=await AdminAnalyticsService(
            session=session,
            application=request.app,
        ).get_search(window),
        meta=None,
    )


@router.get("/analytics/ocr", response_model=DataResponse[AdminOCRAnalyticsResponse])
async def get_admin_ocr_analytics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminOCRAnalyticsResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminOCRAnalyticsResponse](
        data=await AdminAnalyticsService(session=session, application=request.app).get_ocr(window),
        meta=None,
    )


@router.get("/analytics/llm", response_model=DataResponse[AdminLLMAnalyticsResponse])
async def get_admin_llm_analytics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminLLMAnalyticsResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminLLMAnalyticsResponse](
        data=await AdminAnalyticsService(session=session, application=request.app).get_llm(window),
        meta=None,
    )


@router.get("/analytics/feedback", response_model=DataResponse[AdminFeedbackAnalyticsResponse])
async def get_admin_feedback_analytics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminFeedbackAnalyticsResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminFeedbackAnalyticsResponse](
        data=await AdminAnalyticsService(
            session=session,
            application=request.app,
        ).get_feedback(window),
        meta=None,
    )


@router.get("/analytics/audit", response_model=DataResponse[AdminAuditAnalyticsResponse])
async def get_admin_audit_analytics(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DataResponse[AdminAuditAnalyticsResponse]:
    _ = current_user
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    return DataResponse[AdminAuditAnalyticsResponse](
        data=await AdminAnalyticsService(session=session, application=request.app).get_audit(
            window
        ),
        meta=None,
    )


@router.get("/reports/export", response_model=None)
async def export_admin_report(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    report: Annotated[AnalyticsReportKind, Query()],
    format: Annotated[AnalyticsExportFormat, Query()] = "json",  # noqa: A002
    period: Annotated[AnalyticsPeriod, Query()] = "30d",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    _ = current_user
    if format == "pdf":
        raise BusinessValidationError(
            "PDF export is not available because no backend PDF export infrastructure "
            "is configured."
        )
    window = resolve_analytics_window(period=period, date_from=date_from, date_to=date_to)
    service = AdminAnalyticsService(session=session, application=request.app)
    payload = build_export_payload(
        report=report,
        data=await service.get_report(report=report, window=window),
    )
    filename = f"admin-{report}-analytics.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if format == "csv":
        return Response(
            content=analytics_payload_to_csv(payload),
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )
    return JSONResponse(
        content=jsonable_encoder({"data": payload, "meta": None}),
        headers=headers,
    )
