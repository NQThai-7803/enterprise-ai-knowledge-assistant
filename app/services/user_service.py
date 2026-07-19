from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import (
    BusinessValidationError,
    LastActiveAdminError,
    ResourceNotFoundError,
    SelfModificationNotAllowedError,
    UserEmailAlreadyExistsError,
)
from app.core.security import hash_password, utc_now
from app.models import User, UserRole
from app.repositories import department_repository, refresh_token_repository, user_repository
from app.schemas.common import PaginationMeta, build_pagination_meta, calculate_offset
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditAction, AuditContext, AuditService

USER_SAFE_AUDIT_FIELDS = ("email", "full_name", "role", "department_id", "is_active")


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_users(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: UserRole | None,
        department_id: UUID | None,
        is_active: bool | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[User], PaginationMeta]:
        _validate_user_sort(sort_by, sort_order)
        total = await user_repository.count_users(
            self.session,
            search=search,
            role=role,
            department_id=department_id,
            is_active=is_active,
        )
        users = await user_repository.list_users(
            self.session,
            limit=page_size,
            offset=calculate_offset(page, page_size),
            search=search,
            role=role,
            department_id=department_id,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return users, build_pagination_meta(page=page, page_size=page_size, total=total)

    async def get_user_for_view(self, *, user_id: UUID, current_user: User) -> User:
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            raise ResourceNotFoundError()
        user = await user_repository.get_by_id(self.session, user_id)
        if user is None:
            raise ResourceNotFoundError()
        return user

    async def create_user(
        self,
        *,
        payload: UserCreate,
        current_user: User,
        audit_context: AuditContext,
    ) -> User:
        email = str(payload.email).strip().lower()
        full_name = payload.full_name.strip()
        role = payload.role
        department_id = payload.department_id
        actor_user_id = current_user.id

        try:
            await self._validate_role_department(role=role, department_id=department_id)
            await self._ensure_email_available(email)
            if self.session.in_transaction():
                await self.session.rollback()
        except Exception:
            await self.session.rollback()
            raise

        hashed_password = await run_in_threadpool(
            hash_password,
            payload.password.get_secret_value(),
        )

        try:
            user = await user_repository.create(
                self.session,
                email=email,
                full_name=full_name,
                hashed_password=hashed_password,
                role=role,
                department_id=department_id,
            )
            await self.session.flush()
            await AuditService(self.session).create_audit_log(
                actor_user_id=actor_user_id,
                action=AuditAction.USER_CREATED.value,
                entity_type="User",
                entity_id=user.id,
                context=audit_context,
                metadata={
                    "email": user.email,
                    "role": user.role,
                    "department_id": user.department_id,
                },
            )
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            raise UserEmailAlreadyExistsError() from exc
        except Exception:
            await self.session.rollback()
            raise

        return user

    async def update_user(
        self,
        *,
        user_id: UUID,
        payload: UserUpdate,
        current_user: User,
        audit_context: AuditContext,
    ) -> User:
        try:
            user = await user_repository.get_by_id(self.session, user_id)
            if user is None:
                raise ResourceNotFoundError()

            self._ensure_self_update_allowed(user, payload, current_user)
            final_role = payload.role if "role" in payload.model_fields_set else user.role
            final_department_id = (
                payload.department_id
                if "department_id" in payload.model_fields_set
                else user.department_id
            )
            final_is_active = (
                payload.is_active if "is_active" in payload.model_fields_set else user.is_active
            )
            await self._validate_role_department(
                role=final_role,
                department_id=final_department_id,
            )
            if "email" in payload.model_fields_set:
                email = str(payload.email).strip().lower() if payload.email is not None else None
                if email is None:
                    raise BusinessValidationError("Email must not be null.")
                if email != user.email:
                    await self._ensure_email_available(email, excluded_user_id=user.id)
            await self._ensure_last_active_admin_not_removed(
                user,
                final_role=final_role,
                final_is_active=final_is_active,
            )

            before = _user_audit_snapshot(user)
            self._apply_user_update(user, payload)
            after = _user_audit_snapshot(user)
            changed_fields = [
                field for field in USER_SAFE_AUDIT_FIELDS if before[field] != after[field]
            ]
            if not changed_fields:
                await self.session.commit()
                return user

            action = AuditAction.USER_UPDATED.value
            if before["is_active"] is True and after["is_active"] is False:
                await refresh_token_repository.revoke_all_active_for_user(
                    self.session,
                    user_id=user.id,
                    revoked_at=utc_now(),
                )
                action = AuditAction.USER_DEACTIVATED.value
            elif before["is_active"] is False and after["is_active"] is True:
                action = AuditAction.USER_REACTIVATED.value

            await self.session.flush()
            await AuditService(self.session).create_audit_log(
                actor_user_id=current_user.id,
                action=action,
                entity_type="User",
                entity_id=user.id,
                context=audit_context,
                metadata={
                    "changed_fields": changed_fields,
                    "before": {field: before[field] for field in changed_fields},
                    "after": {field: after[field] for field in changed_fields},
                    "role": user.role,
                    "department_id": user.department_id,
                },
            )
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            raise UserEmailAlreadyExistsError() from exc
        except Exception:
            await self.session.rollback()
            raise

        return user

    async def deactivate_user(
        self,
        *,
        user_id: UUID,
        current_user: User,
        audit_context: AuditContext,
    ) -> None:
        try:
            if current_user.id == user_id:
                raise SelfModificationNotAllowedError()
            user = await user_repository.get_by_id(self.session, user_id)
            if user is None:
                raise ResourceNotFoundError()
            await self._ensure_last_active_admin_not_removed(
                user,
                final_role=user.role,
                final_is_active=False,
            )
            if not user.is_active:
                await self.session.commit()
                return

            before = _user_audit_snapshot(user)
            user.is_active = False
            after = _user_audit_snapshot(user)
            await refresh_token_repository.revoke_all_active_for_user(
                self.session,
                user_id=user.id,
                revoked_at=utc_now(),
            )
            await self.session.flush()
            await AuditService(self.session).create_audit_log(
                actor_user_id=current_user.id,
                action=AuditAction.USER_DEACTIVATED.value,
                entity_type="User",
                entity_id=user.id,
                context=audit_context,
                metadata={
                    "changed_fields": ["is_active"],
                    "before": {"is_active": before["is_active"]},
                    "after": {"is_active": after["is_active"]},
                    "role": user.role,
                    "department_id": user.department_id,
                },
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def _validate_role_department(
        self,
        *,
        role: UserRole,
        department_id: UUID | None,
    ) -> None:
        if role in {UserRole.MANAGER, UserRole.STAFF} and department_id is None:
            raise BusinessValidationError("Manager and Staff users must belong to a Department.")
        if department_id is None:
            return
        department = await department_repository.get_by_id(self.session, department_id)
        if department is None:
            raise ResourceNotFoundError()

    async def _ensure_email_available(
        self,
        email: str,
        excluded_user_id: UUID | None = None,
    ) -> None:
        if excluded_user_id is None:
            existing_user = await user_repository.get_by_email(self.session, email)
        else:
            existing_user = await user_repository.get_by_email_excluding_id(
                self.session,
                email=email,
                excluded_user_id=excluded_user_id,
            )
        if existing_user is not None:
            raise UserEmailAlreadyExistsError()

    def _ensure_self_update_allowed(
        self,
        user: User,
        payload: UserUpdate,
        current_user: User,
    ) -> None:
        if current_user.id != user.id:
            return
        if "is_active" in payload.model_fields_set and payload.is_active is False:
            raise SelfModificationNotAllowedError()
        if "role" in payload.model_fields_set and payload.role != user.role:
            raise SelfModificationNotAllowedError()

    async def _ensure_last_active_admin_not_removed(
        self,
        user: User,
        *,
        final_role: UserRole,
        final_is_active: bool,
    ) -> None:
        removes_active_admin = (
            user.role == UserRole.ADMIN
            and user.is_active
            and (final_role != UserRole.ADMIN or not final_is_active)
        )
        if not removes_active_admin:
            return
        active_admin_count = await user_repository.count_active_admins(self.session)
        if active_admin_count <= 1:
            raise LastActiveAdminError()

    def _apply_user_update(self, user: User, payload: UserUpdate) -> None:
        if "email" in payload.model_fields_set:
            if payload.email is None:
                raise BusinessValidationError("Email must not be null.")
            user.email = str(payload.email).strip().lower()
        if "full_name" in payload.model_fields_set:
            if payload.full_name is None:
                raise BusinessValidationError("Full name must not be null.")
            user.full_name = payload.full_name.strip()
        if "role" in payload.model_fields_set:
            if payload.role is None:
                raise BusinessValidationError("Role must not be null.")
            user.role = payload.role
        if "department_id" in payload.model_fields_set:
            user.department_id = payload.department_id
        if "is_active" in payload.model_fields_set:
            if payload.is_active is None:
                raise BusinessValidationError("Active status must not be null.")
            user.is_active = payload.is_active


def _validate_user_sort(sort_by: str, sort_order: str) -> None:
    if sort_by not in user_repository.USER_SORT_FIELDS:
        raise BusinessValidationError("Invalid sort field.")
    if sort_order not in {"asc", "desc"}:
        raise BusinessValidationError("Invalid sort order.")


def _user_audit_snapshot(user: User) -> dict[str, Any]:
    return {
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "department_id": user.department_id,
        "is_active": user.is_active,
    }
