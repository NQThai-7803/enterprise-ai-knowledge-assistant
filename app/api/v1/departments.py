from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_context, require_admin
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    DataResponse,
    ListResponse,
)
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services.audit_service import AuditContext
from app.services.department_service import DepartmentService

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=ListResponse[DepartmentResponse])
async def list_departments(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    sort_by: str = "name",
    sort_order: Literal["asc", "desc"] = "asc",
) -> ListResponse[DepartmentResponse]:
    departments, meta = await DepartmentService(session).list_departments(
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ListResponse[DepartmentResponse](
        data=[DepartmentResponse.from_department(department) for department in departments],
        meta=meta,
    )


@router.post(
    "", response_model=DataResponse[DepartmentResponse], status_code=status.HTTP_201_CREATED
)
async def create_department(
    payload: DepartmentCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[DepartmentResponse]:
    department = await DepartmentService(session).create_department(
        payload=payload,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[DepartmentResponse](
        data=DepartmentResponse.from_department(department),
        meta=None,
    )


@router.get("/{department_id}", response_model=DataResponse[DepartmentResponse])
async def get_department(
    department_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[DepartmentResponse]:
    department = await DepartmentService(session).get_department(department_id)
    return DataResponse[DepartmentResponse](
        data=DepartmentResponse.from_department(department),
        meta=None,
    )


@router.patch("/{department_id}", response_model=DataResponse[DepartmentResponse])
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[DepartmentResponse]:
    department = await DepartmentService(session).update_department(
        department_id=department_id,
        payload=payload,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[DepartmentResponse](
        data=DepartmentResponse.from_department(department),
        meta=None,
    )


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> Response:
    await DepartmentService(session).delete_department(
        department_id=department_id,
        current_user=current_user,
        audit_context=audit_context,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
