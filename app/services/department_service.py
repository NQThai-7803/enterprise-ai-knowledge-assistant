from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEventType, AuditTargetType
from app.core.exceptions import (
    BusinessValidationError,
    DepartmentCodeAlreadyExistsError,
    DepartmentHasDocumentsError,
    DepartmentInUseError,
    DepartmentNameAlreadyExistsError,
    ResourceNotFoundError,
)
from app.models import Department, User
from app.repositories import department_repository, document_repository, user_repository
from app.schemas.common import PaginationMeta, build_pagination_meta, calculate_offset
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.audit_service import AuditContext, AuditService

DEPARTMENT_SAFE_AUDIT_FIELDS = ("name", "code", "description")


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_departments(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Department], PaginationMeta]:
        _validate_department_sort(sort_by, sort_order)
        total = await department_repository.count_departments(self.session, search=search)
        departments = await department_repository.list_departments(
            self.session,
            limit=page_size,
            offset=calculate_offset(page, page_size),
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return departments, build_pagination_meta(page=page, page_size=page_size, total=total)

    async def get_department(self, department_id: UUID) -> Department:
        department = await department_repository.get_by_id(self.session, department_id)
        if department is None:
            raise ResourceNotFoundError()
        return department

    async def create_department(
        self,
        *,
        payload: DepartmentCreate,
        current_user: User,
        audit_context: AuditContext,
    ) -> Department:
        name = payload.name.strip()
        code = payload.code.strip().upper()
        description = payload.description.strip() if payload.description else None
        try:
            await self._ensure_name_available(name)
            await self._ensure_code_available(code)
            department = await department_repository.create(
                self.session,
                name=name,
                code=code,
                description=description,
            )
            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DEPARTMENT_CREATED,
                target_type=AuditTargetType.DEPARTMENT,
                target_id=department.id,
                context=audit_context,
                metadata={},
            )
            await self.session.commit()
            await self.session.refresh(department)
        except IntegrityError as exc:
            await self.session.rollback()
            await self._raise_department_duplicate(name=name, code=code, fallback=exc)
        except Exception:
            await self.session.rollback()
            raise

        return department

    async def update_department(
        self,
        *,
        department_id: UUID,
        payload: DepartmentUpdate,
        current_user: User,
        audit_context: AuditContext,
    ) -> Department:
        try:
            department = await department_repository.get_by_id(self.session, department_id)
            if department is None:
                raise ResourceNotFoundError()

            if "name" in payload.model_fields_set:
                if payload.name is None:
                    raise BusinessValidationError("Department name must not be null.")
                name = payload.name.strip()
                if name != department.name:
                    await self._ensure_name_available(name, excluded_department_id=department.id)
            if "code" in payload.model_fields_set:
                if payload.code is None:
                    raise BusinessValidationError("Department code must not be null.")
                code = payload.code.strip().upper()
                if code != department.code:
                    await self._ensure_code_available(code, excluded_department_id=department.id)

            before = _department_audit_snapshot(department)
            self._apply_department_update(department, payload)
            after = _department_audit_snapshot(department)
            changed_fields = [
                field for field in DEPARTMENT_SAFE_AUDIT_FIELDS if before[field] != after[field]
            ]
            if not changed_fields:
                await self.session.commit()
                return department

            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DEPARTMENT_UPDATED,
                target_type=AuditTargetType.DEPARTMENT,
                target_id=department.id,
                context=audit_context,
                metadata={},
            )
            await self.session.commit()
            await self.session.refresh(department)
        except IntegrityError as exc:
            await self.session.rollback()
            name = payload.name.strip() if payload.name is not None else None
            code = payload.code.strip().upper() if payload.code is not None else None
            await self._raise_department_duplicate(name=name, code=code, fallback=exc)
        except Exception:
            await self.session.rollback()
            raise

        return department

    async def delete_department(
        self,
        *,
        department_id: UUID,
        current_user: User,
        audit_context: AuditContext,
    ) -> None:
        try:
            department = await department_repository.get_by_id(self.session, department_id)
            if department is None:
                raise ResourceNotFoundError()
            active_user_count = await user_repository.count_active_users_by_department(
                self.session,
                department_id,
            )
            if active_user_count > 0:
                raise DepartmentInUseError()
            scoped_document_count = await document_repository.count_documents_by_department(
                self.session,
                department_id,
            )
            if scoped_document_count > 0:
                raise DepartmentHasDocumentsError()

            await department_repository.delete(self.session, department)
            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DEPARTMENT_DELETED,
                target_type=AuditTargetType.DEPARTMENT,
                target_id=department_id,
                context=audit_context,
                metadata={},
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def _ensure_name_available(
        self,
        name: str,
        excluded_department_id: UUID | None = None,
    ) -> None:
        if excluded_department_id is None:
            existing_department = await department_repository.get_by_name(self.session, name)
        else:
            existing_department = await department_repository.get_by_name_excluding_id(
                self.session,
                name=name,
                excluded_department_id=excluded_department_id,
            )
        if existing_department is not None:
            raise DepartmentNameAlreadyExistsError()

    async def _ensure_code_available(
        self,
        code: str,
        excluded_department_id: UUID | None = None,
    ) -> None:
        if excluded_department_id is None:
            existing_department = await department_repository.get_by_code(self.session, code)
        else:
            existing_department = await department_repository.get_by_code_excluding_id(
                self.session,
                code=code,
                excluded_department_id=excluded_department_id,
            )
        if existing_department is not None:
            raise DepartmentCodeAlreadyExistsError()

    async def _raise_department_duplicate(
        self,
        *,
        name: str | None,
        code: str | None,
        fallback: IntegrityError,
    ) -> None:
        if name is not None and await department_repository.get_by_name(self.session, name):
            raise DepartmentNameAlreadyExistsError() from fallback
        if code is not None and await department_repository.get_by_code(self.session, code):
            raise DepartmentCodeAlreadyExistsError() from fallback
        raise DepartmentCodeAlreadyExistsError() from fallback

    def _apply_department_update(
        self,
        department: Department,
        payload: DepartmentUpdate,
    ) -> None:
        if "name" in payload.model_fields_set:
            if payload.name is None:
                raise BusinessValidationError("Department name must not be null.")
            department.name = payload.name.strip()
        if "code" in payload.model_fields_set:
            if payload.code is None:
                raise BusinessValidationError("Department code must not be null.")
            department.code = payload.code.strip().upper()
        if "description" in payload.model_fields_set:
            department.description = payload.description.strip() if payload.description else None


def _validate_department_sort(sort_by: str, sort_order: str) -> None:
    if sort_by not in department_repository.DEPARTMENT_SORT_FIELDS:
        raise BusinessValidationError("Invalid sort field.")
    if sort_order not in {"asc", "desc"}:
        raise BusinessValidationError("Invalid sort order.")


def _department_audit_snapshot(department: Department) -> dict[str, Any]:
    return {
        "name": department.name,
        "code": department.code,
        "description": department.description,
    }
