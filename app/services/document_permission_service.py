from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEventType, AuditTargetType
from app.core.exceptions import (
    DocumentPermissionAlreadyExistsError,
    ResourceNotFoundError,
)
from app.models import DocumentPermission, User
from app.repositories import (
    department_repository,
    document_permission_repository,
    document_repository,
    user_repository,
)
from app.schemas.document import DocumentPermissionCreate, DocumentPermissionUpdate
from app.services.audit_service import AuditContext, AuditService


class DocumentPermissionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_permissions(self, *, document_id: UUID) -> list[DocumentPermission]:
        await self._get_active_document_or_404(document_id)
        return await document_permission_repository.list_for_document(self.session, document_id)

    async def create_permission(
        self,
        *,
        document_id: UUID,
        payload: DocumentPermissionCreate,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> DocumentPermission:
        try:
            await self._get_active_document_or_404(document_id)
            await self._validate_grantee(payload)
            await self._ensure_permission_available(document_id=document_id, payload=payload)
            document_permission = await document_permission_repository.create(
                self.session,
                document_id=document_id,
                user_id=payload.user_id,
                department_id=payload.department_id,
                permission=payload.permission,
                created_by=current_user.id,
            )
            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DOCUMENT_PERMISSION_GRANTED,
                target_type=AuditTargetType.DOCUMENT_PERMISSION,
                target_id=document_permission.id,
                context=audit_context,
                metadata=_permission_audit_metadata(document_permission),
            )
            await self.session.commit()
            await self.session.refresh(document_permission)
        except IntegrityError as exc:
            await self.session.rollback()
            raise DocumentPermissionAlreadyExistsError() from exc
        except Exception:
            await self.session.rollback()
            raise
        return document_permission

    async def update_permission(
        self,
        *,
        document_id: UUID,
        permission_id: UUID,
        payload: DocumentPermissionUpdate,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> DocumentPermission:
        try:
            await self._get_active_document_or_404(document_id)
            document_permission = await document_permission_repository.get_by_document_and_id(
                self.session,
                document_id=document_id,
                permission_id=permission_id,
            )
            if document_permission is None:
                raise ResourceNotFoundError()
            document_permission.permission = payload.permission
            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DOCUMENT_PERMISSION_UPDATED,
                target_type=AuditTargetType.DOCUMENT_PERMISSION,
                target_id=document_permission.id,
                context=audit_context,
                metadata=_permission_audit_metadata(document_permission),
            )
            await self.session.commit()
            await self.session.refresh(document_permission)
        except Exception:
            await self.session.rollback()
            raise
        return document_permission

    async def delete_permission(
        self,
        *,
        document_id: UUID,
        permission_id: UUID,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> None:
        try:
            await self._get_active_document_or_404(document_id)
            document_permission = await document_permission_repository.get_by_document_and_id(
                self.session,
                document_id=document_id,
                permission_id=permission_id,
            )
            if document_permission is None:
                raise ResourceNotFoundError()
            metadata = _permission_audit_metadata(document_permission)
            await document_permission_repository.delete(self.session, document_permission)
            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DOCUMENT_PERMISSION_REVOKED,
                target_type=AuditTargetType.DOCUMENT_PERMISSION,
                target_id=permission_id,
                context=audit_context,
                metadata=metadata,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def _get_active_document_or_404(self, document_id: UUID):
        document = await document_repository.get_active_by_id(self.session, document_id)
        if document is None:
            raise ResourceNotFoundError()
        return document

    async def _validate_grantee(self, payload: DocumentPermissionCreate) -> None:
        if payload.user_id is not None:
            user = await user_repository.get_by_id(self.session, payload.user_id)
            if user is None or not user.is_active:
                raise ResourceNotFoundError()
            return
        if payload.department_id is None:
            raise ResourceNotFoundError()
        department = await department_repository.get_by_id(self.session, payload.department_id)
        if department is None:
            raise ResourceNotFoundError()

    async def _ensure_permission_available(
        self,
        *,
        document_id: UUID,
        payload: DocumentPermissionCreate,
    ) -> None:
        if payload.user_id is not None:
            existing_permission = await document_permission_repository.get_by_document_and_user(
                self.session,
                document_id=document_id,
                user_id=payload.user_id,
            )
        elif payload.department_id is not None:
            existing_permission = (
                await document_permission_repository.get_by_document_and_department(
                    self.session,
                    document_id=document_id,
                    department_id=payload.department_id,
                )
            )
        else:
            existing_permission = None
        if existing_permission is not None:
            raise DocumentPermissionAlreadyExistsError()


def _permission_audit_metadata(permission: DocumentPermission) -> dict[str, object]:
    principal_id = permission.user_id or permission.department_id
    principal_type = "USER" if permission.user_id is not None else "DEPARTMENT"
    return {
        "document_id": permission.document_id,
        "permission": permission.permission,
        "principal_type": principal_type,
        "principal_id": principal_id,
    }
