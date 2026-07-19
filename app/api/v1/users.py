from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_context, get_current_user, require_admin
from app.db.session import get_db_session
from app.models import User, UserRole
from app.schemas.common import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    DataResponse,
    ListResponse,
)
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.audit_service import AuditContext
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=ListResponse[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    role: UserRole | None = None,
    department_id: UUID | None = None,
    is_active: bool | None = None,
    sort_by: str = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> ListResponse[UserResponse]:
    users, meta = await UserService(session).list_users(
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        department_id=department_id,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ListResponse[UserResponse](
        data=[UserResponse.from_user(user) for user in users],
        meta=meta,
    )


@router.post("", response_model=DataResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[UserResponse]:
    user = await UserService(session).create_user(
        payload=payload,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[UserResponse](data=UserResponse.from_user(user), meta=None)


@router.get("/{user_id}", response_model=DataResponse[UserResponse])
async def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[UserResponse]:
    user = await UserService(session).get_user_for_view(
        user_id=user_id,
        current_user=current_user,
    )
    return DataResponse[UserResponse](data=UserResponse.from_user(user), meta=None)


@router.patch("/{user_id}", response_model=DataResponse[UserResponse])
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[UserResponse]:
    user = await UserService(session).update_user(
        user_id=user_id,
        payload=payload,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[UserResponse](data=UserResponse.from_user(user), meta=None)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> Response:
    await UserService(session).deactivate_user(
        user_id=user_id,
        current_user=current_user,
        audit_context=audit_context,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
