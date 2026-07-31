from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    enforce_upload_rate_limit,
    get_audit_context,
    get_current_user,
    get_document_processing_enqueue,
    get_document_upload_limits,
    require_admin,
    require_manager_or_admin,
)
from app.db.session import get_db_session
from app.models import DocumentAccessScope, DocumentStatus, User
from app.schemas.common import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    DataResponse,
    ListResponse,
)
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListItem,
    DocumentPermissionCreate,
    DocumentPermissionResponse,
    DocumentPermissionUpdate,
    DocumentStatusResponse,
    DocumentUpdate,
    DocumentUploadResponse,
)
from app.services.audit_service import AuditContext
from app.services.document_permission_service import DocumentPermissionService
from app.services.document_service import (
    DocumentService,
    DocumentUploadLimits,
    EnqueueDocumentProcessing,
)
from app.storage.base import FileStorage
from app.storage.factory import get_file_storage

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DataResponse[DocumentUploadResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(max_length=255)],
    access_scope: Annotated[DocumentAccessScope, Form()],
    current_user: Annotated[User, Depends(require_manager_or_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[FileStorage, Depends(get_file_storage)],
    upload_limits: Annotated[DocumentUploadLimits, Depends(get_document_upload_limits)],
    enqueue_processing: Annotated[
        EnqueueDocumentProcessing, Depends(get_document_processing_enqueue)
    ],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
    description: Annotated[str | None, Form()] = None,
    department_id: Annotated[UUID | None, Form()] = None,
) -> DataResponse[DocumentUploadResponse]:
    await enforce_upload_rate_limit(request, current_user)
    document = await DocumentService(
        session,
        storage=storage,
        upload_limits=upload_limits,
        enqueue_processing=enqueue_processing,
    ).upload_document(
        file=file,
        title=title,
        description=description,
        access_scope=access_scope,
        department_id=department_id,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[DocumentUploadResponse](
        data=DocumentUploadResponse.from_document(document),
        meta=None,
    )


@router.get("", response_model=ListResponse[DocumentListItem])
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    search: Annotated[str | None, Query(max_length=200)] = None,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    access_scope: DocumentAccessScope | None = None,
    department_id: UUID | None = None,
    sort_by: str = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> ListResponse[DocumentListItem]:
    documents, meta = await DocumentService(session).list_documents(
        current_user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        status=status_filter,
        access_scope=access_scope,
        department_id=department_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ListResponse[DocumentListItem](
        data=[DocumentListItem.from_document(document) for document in documents],
        meta=meta,
    )


@router.get("/{document_id}/status", response_model=DataResponse[DocumentStatusResponse])
async def get_document_status(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[DocumentStatusResponse]:
    document = await DocumentService(session).get_document_status(
        document_id=document_id,
        current_user=current_user,
    )
    return DataResponse[DocumentStatusResponse](
        data=DocumentStatusResponse.from_document(document),
        meta=None,
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[FileStorage, Depends(get_file_storage)],
    upload_limits: Annotated[DocumentUploadLimits, Depends(get_document_upload_limits)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> StreamingResponse:
    download = await DocumentService(
        session,
        storage=storage,
        upload_limits=upload_limits,
    ).get_document_download(
        document_id=document_id,
        current_user=current_user,
        audit_context=audit_context,
    )
    return StreamingResponse(
        download.chunks,
        media_type=download.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download.filename}"',
            "Content-Length": str(download.file_size),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get(
    "/{document_id}/permissions",
    response_model=DataResponse[list[DocumentPermissionResponse]],
)
async def list_document_permissions(
    document_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[list[DocumentPermissionResponse]]:
    permissions = await DocumentPermissionService(session).list_permissions(document_id=document_id)
    return DataResponse[list[DocumentPermissionResponse]](
        data=[DocumentPermissionResponse.from_permission(permission) for permission in permissions],
        meta=None,
    )


@router.post(
    "/{document_id}/permissions",
    response_model=DataResponse[DocumentPermissionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_document_permission(
    document_id: UUID,
    payload: DocumentPermissionCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[DocumentPermissionResponse]:
    permission = await DocumentPermissionService(session).create_permission(
        document_id=document_id,
        payload=payload,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[DocumentPermissionResponse](
        data=DocumentPermissionResponse.from_permission(permission),
        meta=None,
    )


@router.patch(
    "/{document_id}/permissions/{permission_id}",
    response_model=DataResponse[DocumentPermissionResponse],
)
async def update_document_permission(
    document_id: UUID,
    permission_id: UUID,
    payload: DocumentPermissionUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[DocumentPermissionResponse]:
    permission = await DocumentPermissionService(session).update_permission(
        document_id=document_id,
        permission_id=permission_id,
        payload=payload,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[DocumentPermissionResponse](
        data=DocumentPermissionResponse.from_permission(permission),
        meta=None,
    )


@router.delete(
    "/{document_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document_permission(
    document_id: UUID,
    permission_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> Response:
    await DocumentPermissionService(session).delete_permission(
        document_id=document_id,
        permission_id=permission_id,
        current_user=current_user,
        audit_context=audit_context,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}", response_model=DataResponse[DocumentDetailResponse])
async def get_document_detail(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DataResponse[DocumentDetailResponse]:
    document = await DocumentService(session).get_document_detail(
        document_id=document_id,
        current_user=current_user,
    )
    return DataResponse[DocumentDetailResponse](
        data=DocumentDetailResponse.from_document(document),
        meta=None,
    )


@router.patch("/{document_id}", response_model=DataResponse[DocumentDetailResponse])
async def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> DataResponse[DocumentDetailResponse]:
    document = await DocumentService(session).update_document(
        document_id=document_id,
        payload=payload,
        current_user=current_user,
        audit_context=audit_context,
    )
    return DataResponse[DocumentDetailResponse](
        data=DocumentDetailResponse.from_document(document),
        meta=None,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
) -> Response:
    await DocumentService(session).soft_delete_document(
        document_id=document_id,
        current_user=current_user,
        audit_context=audit_context,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
